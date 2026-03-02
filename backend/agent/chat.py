import uuid
import json
import logging
import re
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import ChatSession, ChatMessage, Brand
from ingestion.embedder import search_brand, _extract_search_keywords
from ingestion.gemini_vision import rerank_chunks
from agent.clarifier import (
    MAX_CLARIFICATION_ROUNDS,
    needs_clarification,
    should_require_model_clarification,
    get_clarification_question,
    generate_answer,
    analyze_search_confidence,
    generate_smart_clarification,
    build_enriched_query_from_history,
    count_clarification_rounds,
    extract_known_context,
    determine_missing_info,
    generate_progressive_question,
    generate_disambiguation_question,
    get_alternative_docs_for_context,
)

logger = logging.getLogger(__name__)


def _is_greeting_only(query: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return False
    compact = re.sub(r"[!?.\s]+", " ", q).strip()
    greetings = {
        "oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "e ai", "e aí", "opa"
    }
    return compact in greetings


def _is_door_cycle_no_start_symptom(query: str) -> bool:
    q = (query or "").lower()
    has_door = bool(re.search(r"\b(porta|dw|dfc)\b", q, re.IGNORECASE))
    has_cycle = bool(re.search(r"abr(e|indo).*(fech|fecha)|fech(a|ando).*(abr|abre)", q, re.IGNORECASE))
    has_no_start = bool(re.search(r"n[aã]o\s+parte|n[aã]o\s+sobe|n[aã]o\s+arranca|n[aã]o\s+anda", q, re.IGNORECASE))
    return has_door and (has_cycle or has_no_start)


def _has_explicit_model_identifier(text: str) -> bool:
    """Return True if the text mentions any specific Otis equipment/model/document.
    
    This is the main gatekeeper that prevents over-disambiguation.
    If True, Phase 6a will NOT ask 'qual equipamento?'
    """
    q = (text or "").strip()
    if not q:
        return False
    # Normalize "+" separators (e.g. "GEN2+LVA+BAA21000S") → treat as spaces
    q = q.replace("+", " ")
    patterns = [
        # ── Alphanumeric codes ──
        r"\b[a-z]{1,5}\s?-?\s?\d{1,5}[a-z]?\b",  # OVF10, XO 508, LCB1, LCB2, RCB2, ADV-210, D0510
        r"\b\d{3,5}[a-z]{0,3}\b",                  # 2000, 508, 311335
        # ── Boards & controllers ──
        r"\b(gen\s?\d[a-z]*|g\d)\b",                # gen2, gen2c, g3
        r"\b(lcbi?i|lcb[12]|rcb\d|tcbc|gscb|gecb|gdcb|mcp\d{2,4}|atc)\b",
        # ── Model names (no numbers) ──
        r"\b(otismatic|miconic|mag|selectron)\b",
        r"\b(mrl|do\s?2000|mrds|ledo)\b",
        # ── Drives ──
        r"\b(ovf\s?\d{1,2}|cvf|lvf|cfw\s?\d{0,2})\b",
        r"\b(lva|ultra\s*drive)\b",
        # ── ADV family ──
        r"\b(advz[aã]o|adv)\b",
        # ── VW, Miconic variants ──
        r"\b(vw\s?\d?)\b",
        r"\b(bx|lx)\b",
        # ── MCS, URM ──
        r"\b(mcs\s?\d{3}|urm)\b",
        # ── Escalator ──
        r"\b(nce|xizi)\b",
        # ── Part numbers ──
        r"\b[a-z]{3}\d{4,}[a-z]*\b",                # JAA30171AAA, BAA21000S, BOS9693
        # ── Specific doc/equipment names ──
        r"\b(wittur|midi\s*supra)\b",
        r"\b(arobox|ac[- ]?156)\b",
        r"\b(ifl|jr)[- ]?vvvf\b",
        r"\b(vvvf)\b",
        r"\b(lgtech|lg\s*tech|melco)\b",
        r"\b(modelim)\b",
        r"\b(cme\s*\d{3})\b",                        # CME 101
        r"\b(d05\d{2})\b",                           # D0510, D0506, D0509
        # ── General doc topics that are specific enough ──
        r"\b(livro\s*de\s*pe[cç]as)\b",
        r"\b(no[cç][oõ]es\s*gerais)\b",
        r"\b(m[aá]quinas\s*otis)\b",
        r"\b(manual\s*de\s*seguran[cç]a)\b",
        r"\b(manual\s*geral\s*otis)\b",
        r"\b(ajuste\s*de\s*freio|regular\s*freio)\b",
        r"\b(access?e?\s*code)\b",
        r"\b(diagn[oó]stico\s*de\s*falhas)\b",
        r"\b(311335)\b",                              # 311335MW
    ]
    return any(re.search(p, q, re.IGNORECASE) for p in patterns)


def _is_meta_docs_question(query: str) -> bool:
    return bool(re.search(
        r"(quais\s+(modelos?|documentos?|manuais)|que\s+(modelos?|documentos?|manuais)|"
        r"quais\s+equipamentos|lista\s+de\s+(modelos?|documentos?)|"
        r"vocês?\s+tem\s+documenta[cç]|"
        r"me\s+(lista|mostra|diz)\s+(os|quais))",
        query or "", re.IGNORECASE
    ))


def _is_general_manual_query(query: str) -> bool:
    q = query or ""
    return bool(re.search(
        r"\b(manual\s*(geral\s*otis|otis\s*geral)|no[cç][oõ]es\s*gerais|falhas\s*comuns)\b",
        q,
        re.IGNORECASE,
    ))


def _is_cross_brand_query(query: str, current_brand: str) -> bool:
    q = (query or "").lower()
    brand = (current_brand or "").lower()
    known_brands = [
        "otis", "thyssen", "thyssenkrupp", "tk", "schindler", "atlas",
        "atlas schindler", "hyundai", "mitsubishi", "orona", "kone",
    ]
    matched = [b for b in known_brands if re.search(rf"\b{re.escape(b)}\b", q)]
    if not matched:
        return False
    return all((brand not in m) and (m not in brand) for m in matched)


def _expand_brand_query_terms(query: str, brand_name: str) -> str:
    """Add high-value brand-specific aliases to improve retrieval precision."""
    base_query = (query or "").strip()
    if not base_query:
        return base_query

    brand = (brand_name or "").strip().lower()
    additions: list[str] = []
    q_low = base_query.lower()

    if "otis" in brand:
        has_porta_theme = bool(re.search(r"\b(porta|dw|dfc|door)\b", q_low, re.IGNORECASE))
        has_safety_theme = bool(re.search(r"\b(seguran[cç]a|es|safety)\b", q_low, re.IGNORECASE))
        has_door_cycle_no_start = _is_door_cycle_no_start_symptom(base_query)

        if has_porta_theme:
            additions.extend(["DW", "DFC", "porta cabine", "porta pavimento"])
        if has_safety_theme:
            additions.extend(["ES", "segurança"])
        if has_door_cycle_no_start:
            additions.extend([
                "contato de porta",
                "intertravamento",
                "trinco de porta",
                "cadeia de segurança",
                "não parte após fechamento da porta",
            ])

    if not additions:
        return base_query

    existing_compact = re.sub(r"[^a-z0-9]", "", q_low)
    filtered_additions: list[str] = []
    for item in additions:
        compact = re.sub(r"[^a-z0-9]", "", item.lower())
        if compact and compact not in existing_compact:
            filtered_additions.append(item)

    if not filtered_additions:
        return base_query

    return f"{base_query} {' '.join(filtered_additions)}"


def _prioritize_symptom_chunks(chunks: list[dict], query: str, brand_name: str) -> list[dict]:
    if not chunks:
        return chunks

    brand = (brand_name or "").lower()
    if "otis" not in brand or not _is_door_cycle_no_start_symptom(query):
        return chunks

    door_patterns = [
        r"\bporta\b", r"\bdw\b", r"\bdfc\b", r"intertrav", r"trinco", r"contato\s+de\s+porta", r"cadeia\s+de\s+seguran"
    ]
    avoid_patterns = [
        r"cabo\s+de\s+tra[cç][aã]o", r"contrapeso", r"polia", r"tens[aã]o\s+do\s+cabo"
    ]

    rescored: list[tuple[float, dict]] = []
    for chunk in chunks:
        text = f"{chunk.get('text', '')} {chunk.get('source', '')}".lower()
        base_score = float(chunk.get("score", 0.0))
        bonus = 0.0
        if any(re.search(p, text, re.IGNORECASE) for p in door_patterns):
            bonus += 0.12
        if any(re.search(p, text, re.IGNORECASE) for p in avoid_patterns):
            bonus -= 0.08
        rescored.append((base_score + bonus, chunk))

    rescored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in rescored]


async def get_or_create_session(
    db: AsyncSession,
    user_id: int,
    brand_id: int,
    session_id: str | None = None,
) -> ChatSession:
    """Get existing session or create new one."""
    if session_id:
        result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.last_activity = datetime.utcnow()
            await db.commit()
            return session

    # Create new session
    new_session = ChatSession(
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        brand_id=brand_id,
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session


async def get_session_history(db: AsyncSession, session_id: str) -> list[dict]:
    """Get chat history for a session."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        return []

    msgs_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.id)
    )
    messages = msgs_result.scalars().all()

    return [{"role": m.role, "content": m.content} for m in messages]


async def chat(
    db: AsyncSession,
    user_id: int,
    brand_id: int,
    brand_slug: str,
    brand_name: str,
    query: str,
    session_id: str | None = None,
    external_history: list[dict] | None = None,
) -> dict:
    """
    Main chat function — progressive intelligence approach:
    1. Get/create session + history
    2. Greeting check
    3. Extract accumulated context (model/board/drive/symptom from all turns)
    4. Count how many clarification rounds we've already done
    5. Progressive questioning: ask targeted questions until we have enough info
    6. Search Qdrant with enriched query
    7. Confidence analysis + document disambiguation
    8. Answer with alternatives or ask another progressive question
    9. After MAX rounds, ALWAYS answer with best available info
    """
    # Session management
    session = await get_or_create_session(db, user_id, brand_id, session_id)
    history = await get_session_history(db, session.session_id)

    # If no internal history, use external history from the frontend
    if not history and external_history:
        history = external_history

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=query,
    )
    db.add(user_msg)
    await db.commit()

    # ── Phase 1: Greeting check ─────────────────────────────────────────
    if _is_greeting_only(query):
        greeting_answer = (
            f"Olá! 👋 Bom te ver por aqui. Sou seu assistente técnico da **{brand_name}**.\n\n"
            "Qual é o **modelo/geração**, a **placa/controlador** e o **código de erro** (se houver)?"
        )
        return await _save_and_return(db, session, greeting_answer, [], True)

    if _is_cross_brand_query(query, brand_name):
        cross_brand_answer = (
            f"Esse assistente está configurado para **{brand_name}**. "
            "Se o equipamento for de outra marca, posso te orientar melhor se você confirmar "
            f"o modelo equivalente em **{brand_name}** ou abrir no agente da marca correta."
        )
        return await _save_and_return(db, session, cross_brand_answer, [], False)

    # ── Phase 2: Extract accumulated context from entire conversation ───
    known_context = extract_known_context(query, history)
    clarification_rounds = count_clarification_rounds(history)
    can_still_ask = clarification_rounds < MAX_CLARIFICATION_ROUNDS

    logger.info(
        f"Context: model={known_context.get('model')}, board={known_context.get('board')}, "
        f"drive={known_context.get('drive')}, symptom={known_context.get('symptom')}, "
        f"error={known_context.get('error_code')}, rounds={clarification_rounds}/{MAX_CLARIFICATION_ROUNDS}"
    )

    # ── Phase 3: Pre-search clarification (only on first message) ───────
    # If technical question with NO model info at all and NO history context,
    # ask for model first (but only if we haven't asked yet).
    # BYPASS if user already specified a specific equipment identifier.
    # BYPASS meta-questions about available documentation.
    _is_meta_question = _is_meta_docs_question(query)
    _is_general_manual = _is_general_manual_query(query)
    if can_still_ask and clarification_rounds == 0 and not _has_explicit_model_identifier(query) and not _is_meta_question and not _is_general_manual:
        if should_require_model_clarification(query, history):
            missing = determine_missing_info(known_context)
            if missing:
                if len(history) == 0:
                    clarification = (
                        f"Olá! Eu sou seu assistente técnico da **{brand_name}**.\n\n"
                        "Para te responder com precisão (inclusive em modelos antigos e novos), preciso destes dados:\n"
                        "1. **Modelo/geração** do elevador (como na etiqueta)\n"
                        "2. **Placa/controlador**\n"
                        "3. **Código de erro** e sintoma observado\n\n"
                        "Exemplo: **OVF10 Gen2, placa LCB2, erro UV1, porta abre e fecha e não parte**."
                    )
                else:
                    clarification = (
                        "Para te responder com precisão, me informe primeiro o **modelo/geração do elevador** "
                        "(como aparece na etiqueta) e, se tiver, a **placa/controlador** "
                        "e o **código de falha** exibido."
                    )
                return await _save_and_return(db, session, clarification, [], True)

    # ── Phase 3.5: Quick heuristic check (very short first queries) ─────
    # If user gave a specific equipment identifier, trust them and skip Phase 3.5.
    # Post-search Phase 6c handles disambiguation for ambiguous identifiers.
    identifier_present = _has_explicit_model_identifier(query)
    short_ambiguous_identifier = bool(
        identifier_present
        and len((query or "").split()) <= 2
        and re.search(r"\b(gen\s?\d|adv|mag|vw\s?\d?|urm|manual)\b", query or "", re.IGNORECASE)
    )
    if (
        can_still_ask
        and clarification_rounds == 0
        and not _is_general_manual
        and (not identifier_present or short_ambiguous_identifier)
        and needs_clarification(query, history)
    ):
        clarification = await get_clarification_question(query, brand_name)
        if clarification:
            return await _save_and_return(db, session, clarification, [], True)

    # ── Phase 4: Build enriched query from conversation history ─────────
    if history and len(history) >= 2:
        enriched_query = await build_enriched_query_from_history(
            query, brand_name, history
        )
    else:
        enriched_query = query

    enriched_query = _expand_brand_query_terms(enriched_query, brand_name)
    logger.info(f"Query: '{query}' | Enriched: '{enriched_query}'")

    # ── Phase 5: Search Qdrant (multi-strategy) ─────────────────────────
    chunks = search_brand(brand_slug, enriched_query, top_k=20)
    chunks = _prioritize_symptom_chunks(chunks, enriched_query, brand_name)

    # Fallback search strategies
    confidence = analyze_search_confidence(chunks, enriched_query)

    if not confidence["confident"] or confidence["top_score"] < 0.70:
        keywords = _extract_search_keywords(enriched_query)
        if keywords:
            logger.info(f"Low confidence ({confidence['reason']}), trying keyword fallback: {keywords}")
            existing_keys = {(c["doc_id"], c["page"]) for c in chunks}
            for term in keywords[:3]:
                extra_chunks = search_brand(brand_slug, term, top_k=10)
                for ec in extra_chunks:
                    key = (ec["doc_id"], ec["page"])
                    if key not in existing_keys:
                        chunks.append(ec)
                        existing_keys.add(key)

            chunks.sort(key=lambda x: x["score"], reverse=True)
            chunks = _prioritize_symptom_chunks(chunks, enriched_query, brand_name)
            chunks = chunks[:25]
            confidence = analyze_search_confidence(chunks, enriched_query)
            logger.info(f"After fallback: confidence={confidence['reason']}, top={confidence['top_score']:.3f}")

    # Also try the original query separately if enriched query is very different
    if (enriched_query != query and len(enriched_query) > len(query) * 1.5
            and (not confidence["confident"] or confidence["top_score"] < 0.70)):
        fallback_query = _expand_brand_query_terms(query, brand_name)
        logger.info(f"Trying original query as fallback: '{fallback_query}'")
        original_chunks = search_brand(brand_slug, fallback_query, top_k=10)
        existing_keys = {(c["doc_id"], c["page"]) for c in chunks}
        for oc in original_chunks:
            key = (oc["doc_id"], oc["page"])
            if key not in existing_keys:
                chunks.append(oc)
                existing_keys.add(key)
        chunks.sort(key=lambda x: x["score"], reverse=True)
        chunks = _prioritize_symptom_chunks(chunks, enriched_query, brand_name)
        chunks = chunks[:25]
        confidence = analyze_search_confidence(chunks, enriched_query)

    logger.info(
        f"Search confidence: {confidence['reason']} "
        f"(top={confidence['top_score']:.3f}, "
        f"docs={len(confidence['unique_docs'])}, "
        f"spread={confidence['score_spread']:.3f})"
    )

    # ── Phase 6: Progressive intelligence decision engine ───────────────
    # Decide: answer now, ask another targeted question, or disambiguate

    if can_still_ask:
        # 6a. If no model/board/drive identified in entire conversation AND results span
        #     multiple docs → ask which model/equipment
        has_any_equipment = (
            known_context.get("model")
            or known_context.get("board")
            or known_context.get("drive")
        )
        if not _is_meta_question and not _is_general_manual and not has_any_equipment and not _has_explicit_model_identifier(enriched_query):
            unique_docs = confidence.get("unique_docs", [])
            # Only disambiguate if results are NOT confident (scattered across many docs)
            # If the search is confident (high score, one dominant doc), just answer.
            if len(unique_docs) >= 2 and not confidence["confident"]:
                # Try disambiguation first
                disambig = await generate_disambiguation_question(
                    enriched_query, brand_name, chunks
                )
                if disambig:
                    logger.info(f"Disambiguation question: '{disambig}'")
                    return await _save_and_return(db, session, disambig, [], True)

                # Fallback: generic model question
                model_guard = (
                    "Antes de eu fechar o diagnóstico, me confirme o **modelo/geração** e a **placa/controlador** "
                    "(ex.: Gen2 com GECB, ADV-210 com LCB1, MRL, OVF10). "
                    "Sem isso eu posso cruzar versões diferentes e te passar um procedimento errado."
                )
                return await _save_and_return(db, session, model_guard, [], True)

        # 6b. If NO specific equipment/model was identified AND results are NOT confident,
        #     ask for more specific info (board, error, symptom).
        #     Skip this if user already gave a specific identifier — just answer with what we have.
        has_specific = has_any_equipment or _has_explicit_model_identifier(enriched_query)
        if not _is_meta_question and not has_specific and not confidence["confident"]:
            missing = determine_missing_info(known_context)
            if missing:
                progressive_q = await generate_progressive_question(
                    enriched_query, brand_name, known_context,
                    clarification_rounds + 1, chunks, history,
                )
                if progressive_q:
                    logger.info(f"Progressive question (round {clarification_rounds + 1}): '{progressive_q}'")
                    return await _save_and_return(db, session, progressive_q, [], True)

        # 6c. Variant disambiguation for queries that return many similar-scoring docs.
        #     Two-tier: stricter when user gave a specific identifier (we don't want to
        #     annoy them), looser when query is generic.
        unique_docs_6c = confidence.get("unique_docs", [])
        score_spread_6c = confidence.get("score_spread", 1.0)

        should_disambig_6c = False
        is_lookup_query = bool(re.search(r"\b(diagrama|esquema|manual|guia|menu|completo)\b", enriched_query, re.IGNORECASE))
        is_ambiguous_family = bool(re.search(r"\b(cme\s*\d{3}|adv\s?-?\s?210|gen\s?2|vw\s?2|baa\d{5}|mag)\b", enriched_query, re.IGNORECASE))
        if has_specific:
            # User gave an identifier → still disambiguate if results are clearly ambiguous
            should_disambig_6c = is_lookup_query and (
                (len(unique_docs_6c) >= 3 and score_spread_6c < 0.08)
                or len(unique_docs_6c) >= 6
                or (is_ambiguous_family and len(unique_docs_6c) >= 2)
            )
        else:
            # No identifier → disambiguate more easily
            should_disambig_6c = len(unique_docs_6c) >= 3 and score_spread_6c < 0.08

        if not _is_meta_question and not _is_general_manual and should_disambig_6c:
            disambig = await generate_disambiguation_question(
                enriched_query, brand_name, chunks
            )
            if disambig:
                return await _save_and_return(db, session, disambig, [], True)
            if len(unique_docs_6c) >= 2:
                fallback_disambig = (
                    "Encontrei mais de uma versão de manual/diagrama para esse tema. "
                    "Qual versão exata você quer (modelo, revisão/arquivo ou código completo)?"
                )
                return await _save_and_return(db, session, fallback_disambig, [], True)

    # ── Phase 7: We're answering now ────────────────────────────────────
    # Either we have enough confidence, or we've exhausted our question budget

    if not can_still_ask and not confidence["confident"]:
        logger.info(
            f"Reached max clarification rounds ({MAX_CLARIFICATION_ROUNDS}), "
            f"answering with best available (confidence: {confidence['reason']})"
        )

    # Rerank with Gemini
    if chunks:
        chunks = await rerank_chunks(enriched_query, chunks)
        chunks = chunks[:7]  # top 7 after rerank

    # Find alternative docs that might be useful
    alternative_docs = get_alternative_docs_for_context(known_context, chunks)

    # Generate answer
    answer, sources = await generate_answer(
        enriched_query, brand_name, chunks, history, alternative_docs
    )

    return await _save_and_return(db, session, answer, sources, False)


async def _save_and_return(
    db: AsyncSession,
    session: ChatSession,
    answer: str,
    sources: list[dict],
    needs_clarification: bool,
) -> dict:
    """Save assistant message and return response dict."""
    asst_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        sources=json.dumps(sources),
    )
    db.add(asst_msg)
    await db.commit()
    return {
        "session_id": session.session_id,
        "answer": answer,
        "sources": sources,
        "needs_clarification": needs_clarification,
    }
