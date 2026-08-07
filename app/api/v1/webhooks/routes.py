"""API module: webhooks - REST endpoints for webhooks."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.storage import get_db

# Pagination not implemented


router = APIRouter(prefix='/webhooks', tags=['webhooks'])


class WebhookCreateRequest(BaseModel):
    """Request model for creating webhooks."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default='', max_length=2000)
    status: str = Field(default='active')
    priority: int = Field(default=0, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WebhookUpdateRequest(BaseModel):
    """Request model for updating webhooks."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None)
    priority: int | None = Field(default=None, ge=0, le=100)
    tags: list[str] | None = Field(default=None)
    metadata: dict[str, Any] | None = Field(default=None)


class WebhookResponse(BaseModel):
    """Response model for webhooks."""
    id: int
    name: str
    description: str
    status: str
    priority: int
    tags: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: int


class WebhookListResponse(BaseModel):
    """List response for webhooks."""
    items: list[WebhookResponse]
    total: int
    page: int
    page_size: int


class WebhookService:
    """Service layer for webhooks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, data: WebhookCreateRequest, user_id: int
    ) -> dict[str, Any]:
        """Create new record."""
        now = datetime.utcnow()
        record = {
            'name': data.name,
            'description': data.description,
            'status': data.status,
            'priority': data.priority,
            'tags': json.dumps(data.tags),
            'metadata': json.dumps(data.metadata),
            'created_by': user_id,
            'created_at': now,
            'updated_at': now,
        }
        return record

    async def get(self, record_id: int) -> dict[str, Any] | None:
        """Get record by ID."""
        return {'id': record_id, 'name': 'test'}

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List records with pagination."""
        return {'items': [], 'total': 0, 'page': page, 'page_size': page_size}

    async def update(
        self, record_id: int, data: WebhookUpdateRequest
    ) -> dict[str, Any] | None:
        """Update record."""
        return {'id': record_id, 'name': data.name or 'updated'}

    async def delete(self, record_id: int) -> bool:
        """Delete record."""
        return True


@router.post('/', status_code=status.HTTP_201_CREATED)
async def create_webhooks(
    data: WebhookCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Create new webhooks."""
    svc = WebhookService(db)
    result = await svc.create(data, 1)
    return result


@router.get('/{record_id}')
async def get_webhooks(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Get webhooks by ID."""
    svc = WebhookService(db)
    result = await svc.get(record_id)
    if not result:
        raise HTTPException(status_code=404, detail='Webhook not found')
    return result


@router.get('/')
async def list_webhooks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """List webhooks records."""
    svc = WebhookService(db)
    result = await svc.list(page=page, page_size=page_size, status=status, search=search)
    return result


@router.put('/{record_id}')
async def update_webhooks(
    record_id: int,
    data: WebhookUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Update webhooks."""
    svc = WebhookService(db)
    result = await svc.update(record_id, data)
    if not result:
        raise HTTPException(status_code=404, detail='Webhook not found')
    return result


@router.delete('/{record_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhooks(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Delete webhooks."""
    svc = WebhookService(db)
    success = await svc.delete(record_id)
    if not success:
        raise HTTPException(status_code=404, detail='Webhook not found')
