"""API key management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.core.api_key_crypto import encrypt_api_key
from app.core.auth import get_current_user
from app.storage import async_session
from app.storage.database import ApiKey as ApiKeyModel

router = APIRouter(dependencies=[Depends(get_current_user)])

class ApiKeyCreate(BaseModel):
    provider: str
    name: str
    api_key: str
    base_url: str | None = None


class ApiKeyOut(BaseModel):
    id: str
    provider: str
    name: str
    base_url: str | None
    is_active: bool
    created_at: str


@router.get("", response_model=list[ApiKeyOut])
@router.get("/", response_model=list[ApiKeyOut])
async def list_api_keys(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[ApiKeyOut]:
    async with async_session() as session:
        result = await session.execute(
            select(ApiKeyModel)
            .where(ApiKeyModel.user_id == "default-user")
            .order_by(ApiKeyModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            ApiKeyOut(
                id=r.id,
                provider=r.provider,
                name=r.name,
                base_url=r.base_url,
                is_active=r.is_active,
                created_at=r.created_at.isoformat() if r.created_at else "",
            )
            for r in rows
        ]


@router.post("", response_model=ApiKeyOut)
@router.post("/", response_model=ApiKeyOut)
async def add_api_key(payload: ApiKeyCreate) -> ApiKeyOut:
    encrypted = encrypt_api_key(payload.api_key)
    async with async_session() as session:
        row = ApiKeyModel(
            user_id="default-user",
            provider=payload.provider,
            name=payload.name,
            api_key_encrypted=encrypted,
            base_url=payload.base_url,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return ApiKeyOut(
            id=row.id,
            provider=row.provider,
            name=row.name,
            base_url=row.base_url,
            is_active=row.is_active,
            created_at=row.created_at.isoformat() if row.created_at else "",
        )


@router.delete("/{key_id}")
async def delete_api_key(key_id: str) -> dict:
    async with async_session() as session:
        result = await session.execute(
            select(ApiKeyModel).where(
                ApiKeyModel.id == key_id,
                ApiKeyModel.user_id == "default-user",
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="API key not found")
        await session.delete(row)
        await session.commit()
    return {"ok": True}
