import uuid
import json
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import ChatSession, ChatMessage, Brand
from ingestion.embedder import search_brand
from ingestion.gemini_vision import rerank_chunks
from agent.clarifier import (
    needs_clarification,
    get_clarification_question,
    generate_answer,
)

logger = logging.getLogger(__name__)


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
) -> dict:
    """
    Main chat function:
    1. Get/create session
    2. Check if clarification needed
    3. Search Qdrant
    4. Rerank results
    5. Generate answer
    6. Persist messages
    """
    # Session management
    session = await get_or_create_session(db, user_id, brand_id, session_id)
    history = await get_session_history(db, session.session_id)

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=query,
    )
    db.add(user_msg)
    await db.commit()

    # Check if clarification needed
    if needs_clarification(query, history):
        clarification = await get_clarification_question(query, brand_name)
        if clarification:
            # Save clarification as assistant message
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

    # Build enriched query with history context
    enriched_query = query
    if history:
        # Append last user context to improve search
        last_answers = [m["content"] for m in history[-4:] if m["role"] == "user"]
        if last_answers:
            enriched_query = " ".join(last_answers[-2:]) + " " + query

    # Semantic search in Qdrant
    chunks = search_brand(brand_slug, enriched_query, top_k=10)

    # Rerank with Gemini
    if chunks:
        chunks = await rerank_chunks(query, chunks)
        chunks = chunks[:5]  # top 5 after rerank

    # Generate answer
    answer, sources = await generate_answer(query, brand_name, chunks, history)

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
