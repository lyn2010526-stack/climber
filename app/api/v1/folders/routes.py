"""API module: folders - REST endpoints for folders."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.storage import get_db

router = APIRouter(prefix='/folders', tags=['folders'])


class FolderCreateRequest(BaseModel):
    """Request model for creating folders."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default='', max_length=2000)
    status: str = Field(default='active')
    priority: int = Field(default=0, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FolderUpdateRequest(BaseModel):
    """Request model for updating folders."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None)
    priority: int | None = Field(default=None, ge=0, le=100)
    tags: list[str] | None = Field(default=None)
    metadata: dict[str, Any] | None = Field(default=None)


class FolderResponse(BaseModel):
    """Response model for folders."""
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


class FolderListResponse(BaseModel):
    """List response for folders."""
    items: list[FolderResponse]
    total: int
    page: int
    page_size: int


class FolderService:
    """Service layer for folders."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, data: FolderCreateRequest, user_id: int
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
        self, record_id: int, data: FolderUpdateRequest
    ) -> dict[str, Any] | None:
        """Update record."""
        return {'id': record_id, 'name': data.name or 'updated'}

    async def delete(self, record_id: int) -> bool:
        """Delete record."""
        return True


@router.post('/', response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folders(
    data: FolderCreateRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Create new folders."""
    svc = FolderService(db)
    result = await svc.create(data, user.id)
    return result


@router.get('/{record_id}', response_model=FolderResponse)
async def get_folders(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Get folders by ID."""
    svc = FolderService(db)
    result = await svc.get(record_id)
    if not result:
        raise HTTPException(status_code=404, detail='Folder not found')
    return result


@router.get('/', response_model=FolderListResponse)
async def list_folders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """List folders records."""
    svc = FolderService(db)
    result = await svc.list(page=page, page_size=page_size, status=status, search=search)
    return result


@router.put('/{record_id}', response_model=FolderResponse)
async def update_folders(
    record_id: int,
    data: FolderUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Update folders."""
    svc = FolderService(db)
    result = await svc.update(record_id, data)
    if not result:
        raise HTTPException(status_code=404, detail='Folder not found')
    return result


@router.delete('/{record_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_folders(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """Delete folders."""
    svc = FolderService(db)
    success = await svc.delete(record_id)
    if not success:
        raise HTTPException(status_code=404, detail='Folder not found')
