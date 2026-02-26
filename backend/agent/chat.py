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
    q = (text or "").strip()
    if not q:
        return False
    patterns = [
        r"\b[a-z]{1,5}\s?-?\s?\d{1,5}[a-z]?\b",  # OVF10, XO 508, LCB1, LCB2, RCB2, ADV-210
        r"\b(gen\s?\d|g\d)\b",                    # gen2, g3
        r"\b(lcb[i12]|rcb\d|tcbc|gscb|mcp\d{2,4}|atc|cvf|ovf\d{1,3})\b",  # Otis boards
        r"\b[a-z]{3}\d{4,}[a-z]*\b",              # JAA30171AAA, BAA21000S (Otis part numbers)
    ]
    return any(re.search(p, q, re.IGNORECASE) for p in patterns)


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
            "Pode me descrever a falha com **modelo/geração**, **placa/controlador** e **código de erro** (se houver) que eu te respondo direto e objetivo."
        )
        return await _save_and_return(db, session, greeting_answer, [], False)

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
    # ask for model first (but only if we haven't asked yet)
    if can_still_ask and clarification_rounds == 0:
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
    if can_still_ask and clarification_rounds == 0 and needs_clarification(query, history):
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
        # 6a. If no model identified in entire conversation AND results span
        #     multiple docs → ask which model/equipment
        if not known_context.get("model") and not _has_explicit_model_identifier(enriched_query):
            unique_docs = confidence.get("unique_docs", [])
            if len(unique_docs) >= 2:
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

        # 6b. If we have model but results are NOT confident,
        #     ask for more specific info (board, error, symptom)
        if not confidence["confident"]:
            missing = determine_missing_info(known_context)
            if missing:
                progressive_q = await generate_progressive_question(
                    enriched_query, brand_name, known_context,
                    clarification_rounds + 1, chunks, history,
                )
                if progressive_q:
                    logger.info(f"Progressive question (round {clarification_rounds + 1}): '{progressive_q}'")
                    return await _save_and_return(db, session, progressive_q, [], True)

        # 6c. If confident but results come from multiple docs with similar scores,
        #     ask which variant the user has
        if confidence["confident"] and len(confidence.get("unique_docs", [])) >= 3:
            score_spread = confidence.get("score_spread", 0)
            if score_spread < 0.05:
                # Very similar scores across many docs — worth asking
                disambig = await generate_disambiguation_question(
                    enriched_query, brand_name, chunks
                )
                if disambig:
                    return await _save_and_return(db, session, disambig, [], True)

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
