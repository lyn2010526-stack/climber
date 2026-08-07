"""API module: configurations - REST endpoints for configurations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.storage import get_db

router = APIRouter(prefix='/configurations', tags=['configurations'])


class ConfigurationCreateRequest(BaseModel):
    """Request model for creating configurations."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default='', max_length=2000)
    status: str = Field(default='active')
    priority: int = Field(default=0, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConfigurationUpdateRequest(BaseModel):
    """Request model for updating configurations."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None)
    priority: int | None = Field(default=None, ge=0, le=100)
    tags: list[str] | None = Field(default=None)
    metadata: dict[str, Any] | None = Field(default=None)


class ConfigurationResponse(BaseModel):
    """Response model for configurations."""
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


class ConfigurationListResponse(BaseModel):
    """List response for configurations."""
    items: list[ConfigurationResponse]
    total: int
    page: int
    page_size: int


def _make_response(record_id: int, name: str, description: str = '', status: str = 'active',
                    priority: int = 0, tags: list | None = None, metadata: dict | None = None,
                    created_by: int = 0) -> dict[str, Any]:
    now = datetime.utcnow()
    return {
        'id': record_id,
        'name': name,
        'description': description,
        'status': status,
        'priority': priority,
        'tags': tags or [],
        'metadata': metadata or {},
        'created_at': now,
        'updated_at': now,
        'created_by': created_by,
    }


@router.post('/', response_model=ConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_configurations(
    data: ConfigurationCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Create new configurations."""
    try:
        created_by = int(user_id)
    except (ValueError, TypeError):
        created_by = 0
    return _make_response(1, data.name, data.description, data.status, data.priority, data.tags, data.metadata, created_by)


@router.get('/{record_id}', response_model=ConfigurationResponse)
async def get_configurations(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Get configurations by ID."""
    return _make_response(record_id, 'test')


@router.get('/', response_model=ConfigurationListResponse)
async def list_configurations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """List configurations records."""
    return {'items': [], 'total': 0, 'page': page, 'page_size': page_size}


@router.put('/{record_id}', response_model=ConfigurationResponse)
async def update_configurations(
    record_id: int,
    data: ConfigurationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Update configurations."""
    return _make_response(record_id, data.name or 'updated')


@router.delete('/{record_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_configurations(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Delete configurations."""
    return None
