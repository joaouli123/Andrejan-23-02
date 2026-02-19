from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from database import get_db
from models import User, Brand, UserBrandAccess
from auth import (
    create_access_token,
    get_current_user,
    get_current_admin,
)
from security import verify_password, get_password_hash

router = APIRouter(prefix="/auth", tags=["auth"])


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    is_admin: bool = False
    brand_ids: List[int] = []


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    is_admin: bool
    is_active: bool
    brand_ids: List[int] = []

    class Config:
        from_attributes = True


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuário desativado")

    token = create_access_token({"sub": str(user.id)})

    # Get brand access
    ba_result = await db.execute(
        select(UserBrandAccess).where(UserBrandAccess.user_id == user.id)
    )
    brand_ids = [ba.brand_id for ba in ba_result.scalars().all()]

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": user.is_admin,
            "brand_ids": brand_ids,
        },
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ba_result = await db.execute(
        select(UserBrandAccess).where(UserBrandAccess.user_id == current_user.id)
    )
    brand_ids = [ba.brand_id for ba in ba_result.scalars().all()]
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
        "brand_ids": brand_ids,
    }


@router.get("/users", dependencies=[Depends(get_current_admin)])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    out = []
    for u in users:
        ba_result = await db.execute(
            select(UserBrandAccess).where(UserBrandAccess.user_id == u.id)
        )
        brand_ids = [ba.brand_id for ba in ba_result.scalars().all()]
        out.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "brand_ids": brand_ids,
        })
    return out


@router.post("/users", dependencies=[Depends(get_current_admin)])
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        is_admin=data.is_admin,
    )
    db.add(user)
    await db.flush()

    for brand_id in data.brand_ids:
        db.add(UserBrandAccess(user_id=user.id, brand_id=brand_id))

    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "email": user.email, "message": "Usuário criado com sucesso"}


@router.delete("/users/{user_id}", dependencies=[Depends(get_current_admin)])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    await db.delete(user)
    await db.commit()
    return {"message": "Usuário removido"}
