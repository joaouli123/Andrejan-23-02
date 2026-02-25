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
    needs_clarification,
    should_require_model_clarification,
    get_clarification_question,
    generate_answer,
    analyze_search_confidence,
    generate_smart_clarification,
    build_enriched_query_from_history,
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
        r"\b[a-z]{1,5}\s?-?\s?\d{2,5}[a-z]?\b",  # OVF10, XO 508, ADV-210
        r"\b(gen\s?\d|g\d)\b",                    # gen2, g3
        r"\b(lcb\d|tcbc|gscb|mcp\d{2,4}|atc|cvf|ovf\d{1,3})\b",
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
    Main chat function — search-first approach:
    1. Get/create session + history
    2. Quick check if query is too short → ask clarification
    3. Enrich query with history context (model info from previous turns)
    4. Search Qdrant
    5. Analyze search confidence
    6. If ambiguous results across many docs → smart clarification
    7. Rerank + generate answer
    """
    # Session management
    session = await get_or_create_session(db, user_id, brand_id, session_id)
    history = await get_session_history(db, session.session_id)

    # If no internal history, use external history from the frontend.
    # This allows multi-turn context (model from previous turns, etc.).
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

    if _is_greeting_only(query):
        greeting_answer = (
            f"Olá! 👋 Bom te ver por aqui. Sou seu assistente técnico da **{brand_name}**.\n\n"
            "Pode me descrever a falha com **modelo/geração**, **placa/controlador** e **código de erro** (se houver) que eu te respondo direto e objetivo."
        )
        asst_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=greeting_answer,
            sources=json.dumps([]),
        )
        db.add(asst_msg)
        await db.commit()
        return {
            "session_id": session.session_id,
            "answer": greeting_answer,
            "sources": [],
            "needs_clarification": False,
        }

    # --- Step 0: Mandatory model/board/code clarification gate ---
    # If technical question lacks identifying info, always ask first.
    if should_require_model_clarification(query, history):
        if len(history) == 0:
            clarification = (
                f"Olá! Eu sou seu assistente técnico da **{brand_name}**.\n\n"
                "Para te responder com precisão (inclusive em modelos antigos e novos), preciso destes dados:\n"
                "1. **Modelo/geração** do elevador (como na etiqueta)\n"
                "2. **Placa/controlador**\n"
                "3. **Código de erro** e sintoma observado\n\n"
                "Exemplo: **OVF10 Gen2, placa C.07.10, erro E015, porta abre e fecha e não parte**."
            )
        else:
            clarification = (
                "Para te responder com precisão, me informe primeiro o **modelo/geração do elevador** "
                "(como aparece na etiqueta) e, se tiver, a **placa/controlador** "
                "e o **código de falha** exibido."
            )
        asst_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=clarification,
            sources=json.dumps([]),
        )
        db.add(asst_msg)
        await db.commit()
        return {
            "session_id": session.session_id,
            "answer": clarification,
            "sources": [],
            "needs_clarification": True,
        }

    # --- Step 1: Quick heuristic check (very short queries) ---
    if needs_clarification(query, history):
        clarification = await get_clarification_question(query, brand_name)
        if clarification:
            asst_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=clarification,
                sources=json.dumps([]),
            )
            db.add(asst_msg)
            await db.commit()
            return {
                "session_id": session.session_id,
                "answer": clarification,
                "sources": [],
                "needs_clarification": True,
            }

    # --- Step 2: Build enriched query from conversation history ---
    # This combines model/board info from previous turns with current question
    # Critical: when user answers a clarification (e.g. "OVF10"), we need
    # to combine that with the original question from history.
    if history and len(history) >= 2:
        enriched_query = await build_enriched_query_from_history(
            query, brand_name, history
        )
    else:
        enriched_query = query

    enriched_query = _expand_brand_query_terms(enriched_query, brand_name)

    logger.info(f"Query: '{query}' | Enriched: '{enriched_query}'")

    # --- Step 3: Search Qdrant (multi-strategy) ---
    chunks = search_brand(brand_slug, enriched_query, top_k=20)
    chunks = _prioritize_symptom_chunks(chunks, enriched_query, brand_name)

    # --- Step 3.5: Fallback search strategies ---
    # If the main search didn't find confident results and the query has
    # specific terms (model codes, etc.), try searching with just those terms.
    # This handles cases where the enriched query is too broad.
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

            # Re-sort all chunks by score
            chunks.sort(key=lambda x: x["score"], reverse=True)
            chunks = _prioritize_symptom_chunks(chunks, enriched_query, brand_name)
            # Keep top results
            chunks = chunks[:25]
            # Re-analyze confidence with expanded results
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

    # --- Guardrail: never lock into a specific model if user did not provide one ---
    if not _has_explicit_model_identifier(enriched_query):
        unique_docs = confidence.get("unique_docs", [])
        top_score = float(confidence.get("top_score", 0.0) or 0.0)
        if len(unique_docs) >= 2 or top_score < 0.90:
            model_guard = (
                "Antes de eu fechar o diagnóstico, me confirme o **modelo/geração** e a **placa/controlador** "
                "(ex.: LCB1, LCB2, TCBC, GSCB). Sem isso eu posso cruzar versões diferentes e te passar um procedimento errado."
            )
            asst_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=model_guard,
                sources=json.dumps([]),
            )
            db.add(asst_msg)
            await db.commit()
            return {
                "session_id": session.session_id,
                "answer": model_guard,
                "sources": [],
                "needs_clarification": True,
            }

    # --- Step 5: Smart clarification if results are ambiguous ---
    # Only ask clarification if we haven't asked recently (avoid loops)
    asked_recently = False
    if history:
        recent_asst = [m for m in history[-4:] if m["role"] == "assistant"]
        asked_recently = any("?" in m["content"] for m in recent_asst)

    if not confidence["confident"] and not asked_recently:
        smart_question = await generate_smart_clarification(
            enriched_query, brand_name, chunks, confidence, history
        )
        if smart_question:
            asst_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=smart_question,
                sources=json.dumps([]),
            )
            db.add(asst_msg)
            await db.commit()
            return {
                "session_id": session.session_id,
                "answer": smart_question,
                "sources": [],
                "needs_clarification": True,
            }

    # --- Step 6: Rerank with Gemini ---
    # Use enriched_query so reranking considers full context
    # (e.g. user answered "OVF10" to clarification about their original question)
    if chunks:
        chunks = await rerank_chunks(enriched_query, chunks)
        chunks = chunks[:7]  # top 7 after rerank

    # --- Step 7: Generate answer ---
    # Pass enriched_query so the answer covers the full conversation context
    answer, sources = await generate_answer(enriched_query, brand_name, chunks, history)

    # Save assistant message
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
        "needs_clarification": False,
    }
