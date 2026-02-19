import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models import Brand, UserBrandAccess, ChatSession, ChatMessage
from auth import get_current_user
from agent.chat import chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class HistoryResponse(BaseModel):
    role: str
    content: str
    sources: list = []


@router.post("/{brand_id}")
async def send_message(
    brand_id: int,
    request: ChatRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the brand agent."""
    # Validate brand access
    brand_result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = brand_result.scalar_one_or_none()
    if not brand or not brand.is_active:
        raise HTTPException(status_code=404, detail="Marca não encontrada")

    if not current_user.is_admin:
        ba = await db.execute(
            select(UserBrandAccess).where(
                UserBrandAccess.user_id == current_user.id,
                UserBrandAccess.brand_id == brand_id,
            )
        )
        if not ba.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Sem acesso a esta marca")

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Mensagem vazia")

    result = await chat(
        db=db,
        user_id=current_user.id,
        brand_id=brand_id,
        brand_slug=brand.slug,
        brand_name=brand.name,
        query=request.query.strip(),
        session_id=request.session_id,
    )

    return result


@router.get("/{brand_id}/sessions")
async def list_sessions(
    brand_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all chat sessions for the current user on a brand."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.user_id == current_user.id,
            ChatSession.brand_id == brand_id,
        ).order_by(ChatSession.last_activity.desc())
    )
    sessions = result.scalars().all()

    return [
        {
            "session_id": s.session_id,
            "created_at": s.created_at.isoformat(),
            "last_activity": s.last_activity.isoformat(),
        }
        for s in sessions
    ]


@router.get("/{brand_id}/sessions/{session_id}/history")
async def get_history(
    brand_id: int,
    session_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full message history of a chat session."""
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    msgs_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.id)
    )
    messages = msgs_result.scalars().all()

    return [
        {
            "role": m.role,
            "content": m.content,
            "sources": json.loads(m.sources) if m.sources else [],
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.delete("/{brand_id}/sessions/{session_id}")
async def delete_session(
    brand_id: int,
    session_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session and its history."""
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    await db.delete(session)
    await db.commit()
    return {"message": "Sessão removida"}
