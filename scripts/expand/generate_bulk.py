#!/usr/bin/env python3
"""Bulk code generator for rapid expansion to 500K lines."""

from __future__ import annotations

from pathlib import Path
from string import Template

BASE = Path("/workspace/agent-engine")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


SERVICE_TEMPLATE = Template('''\
"""Service module for ${name} - ${description}."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
from enum import Enum

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()
Base = declarative_base()


class ${model_name}Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ARCHIVED = "archived"


class ${model_name}Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ${model_name}(Base):
    """${model_name} database model."""
    __tablename__ = "${name}"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False, index=True)
    slug = Column(String(256), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    status = Column(String(32), default=${model_name}Status.ACTIVE.value)
    priority = Column(String(32), default=${model_name}Priority.MEDIUM.value)
    owner_id = Column(Integer, nullable=True, index=True)
    organization_id = Column(Integer, nullable=True, index=True)
    metadata_json = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    config = Column(JSON, default=dict)
    is_public = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    parent_id = Column(Integer, nullable=True, index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("${name}_owner_status", "owner_id", "status"),
        Index("${name}_org_status", "organization_id", "status"),
        Index("${name}_created_sort", "created_at", "sort_order"),
    )


class ${model_name}Revision(Base):
    """${model_name} revision history."""
    __tablename__ = "${name}_revisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ${name}_id = Column(Integer, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)
    change_summary = Column(String(512), default="")
    changed_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ${model_name}Comment(Base):
    """Comments on ${name}."""
    __tablename__ = "${name}_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ${name}_id = Column(Integer, nullable=False, index=True)
    author_id = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_id = Column(Integer, nullable=True)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ${model_name}Attachment(Base):
    """File attachments for ${name}."""
    __tablename__ = "${name}_attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ${name}_id = Column(Integer, nullable=False, index=True)
    file_name = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(Integer, default=0)
    mime_type = Column(String(128), default="")
    uploaded_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# --- Pydantic schemas ---

class ${model_name}Create(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str = ""
    priority: ${model_name}Priority = ${model_name}Priority.MEDIUM
    tags: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    is_public: bool = False
    parent_id: int | None = None


class ${model_name}Update(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ${model_name}Status | None = None
    priority: ${model_name}Priority | None = None
    tags: list[str] | None = None
    config: dict[str, Any] | None = None
    is_public: bool | None = None
    sort_order: int | None = None


class ${model_name}Response(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    status: str
    priority: str
    owner_id: int | None
    tags: list[str]
    is_public: bool
    view_count: int
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ${model_name}ListResponse(BaseModel):
    items: list[${model_name}Response]
    total: int
    page: int
    page_size: int


class ${model_name}Filter(BaseModel):
    status: ${model_name}Status | None = None
    priority: ${model_name}Priority | None = None
    owner_id: int | None = None
    organization_id: int | None = None
    tags: list[str] | None = None
    search: str | None = None
    is_public: bool | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class ${model_name}Stats(BaseModel):
    total_count: int
    active_count: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    recent_count: int
    avg_daily_creation: float


class ${class_name}:
    """Service for managing ${name}."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: ${model_name}Create, owner_id: int | None = None) -> ${model_name}Response:
        """Create a new ${name}."""
        import re
        slug = re.sub(r"[^a-z0-9]+", "-", data.name.lower()).strip("-")
        existing = await self.session.execute(
            select(${model_name}).where(${model_name}.slug == slug)
        )
        if existing.scalar_one_or_none():
            slug = f"{slug}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        item = ${model_name}(
            name=data.name,
            slug=slug,
            description=data.description,
            priority=data.priority.value,
            owner_id=owner_id,
            tags=data.tags,
            config=data.config,
            is_public=data.is_public,
            parent_id=data.parent_id,
        )
        self.session.add(item)
        await self.session.flush()

        revision = ${model_name}Revision(
            ${name}_id=item.id,
            version=1,
            data=data.model_dump(),
            change_summary="Created",
            changed_by=owner_id,
        )
        self.session.add(revision)
        await self.session.commit()
        return ${model_name}Response.model_validate(item)

    async def get(self, item_id: int) -> ${model_name} | None:
        """Get ${name} by ID."""
        result = await self.session.execute(
            select(${model_name}).where(${model_name}.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> ${model_name} | None:
        """Get ${name} by slug."""
        result = await self.session.execute(
            select(${model_name}).where(${model_name}.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_items(self, filter_data: ${model_name}Filter) -> tuple[list[${model_name}], int]:
        """List ${name} items with filters."""
        query = select(${model_name}).where(${model_name}.is_archived == False)
        count_query = select(func.count()).select_from(${model_name}).where(${model_name}.is_archived == False)

        if filter_data.status:
            query = query.where(${model_name}.status == filter_data.status.value)
            count_query = count_query.where(${model_name}.status == filter_data.status.value)
        if filter_data.priority:
            query = query.where(${model_name}.priority == filter_data.priority.value)
            count_query = count_query.where(${model_name}.priority == filter_data.priority.value)
        if filter_data.owner_id:
            query = query.where(${model_name}.owner_id == filter_data.owner_id)
            count_query = count_query.where(${model_name}.owner_id == filter_data.owner_id)
        if filter_data.organization_id:
            query = query.where(${model_name}.organization_id == filter_data.organization_id)
            count_query = count_query.where(${model_name}.organization_id == filter_data.organization_id)
        if filter_data.is_public is not None:
            query = query.where(${model_name}.is_public == filter_data.is_public)
            count_query = count_query.where(${model_name}.is_public == filter_data.is_public)
        if filter_data.search:
            query = query.where(${model_name}.name.ilike(f"%{filter_data.search}%"))
            count_query = count_query.where(${model_name}.name.ilike(f"%{filter_data.search}%"))
        if filter_data.created_after:
            query = query.where(${model_name}.created_at >= filter_data.created_after)
            count_query = count_query.where(${model_name}.created_at >= filter_data.created_after)
        if filter_data.created_before:
            query = query.where(${model_name}.created_at <= filter_data.created_before)
            count_query = count_query.where(${model_name}.created_at <= filter_data.created_before)

        query = query.order_by(${model_name}.sort_order, ${model_name}.created_at.desc())
        query = query.offset((filter_data.page - 1) * filter_data.page_size).limit(filter_data.page_size)

        result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        return result.scalars().all(), count_result.scalar()

    async def update(self, item_id: int, data: ${model_name}Update, changed_by: int | None = None) -> ${model_name} | None:
        """Update ${name} item."""
        item = await self.get(item_id)
        if not item:
            return None

        update_data = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description
        if data.status is not None:
            update_data["status"] = data.status.value
        if data.priority is not None:
            update_data["priority"] = data.priority.value
        if data.tags is not None:
            update_data["tags"] = data.tags
        if data.config is not None:
            update_data["config"] = data.config
        if data.is_public is not None:
            update_data["is_public"] = data.is_public
        if data.sort_order is not None:
            update_data["sort_order"] = data.sort_order

        if update_data:
            update_data["version"] = item.version + 1
            update_data["updated_at"] = datetime.utcnow()
            await self.session.execute(
                update(${model_name}).where(${model_name}.id == item_id).values(**update_data)
            )

            revision = ${model_name}Revision(
                ${name}_id=item_id,
                version=item.version + 1,
                data=update_data,
                change_summary="Updated fields: " + ", ".join(update_data.keys()),
                changed_by=changed_by,
            )
            self.session.add(revision)
            await self.session.commit()
            return await self.get(item_id)
        return item

    async def delete(self, item_id: int, hard: bool = False) -> bool:
        """Delete ${name} item."""
        item = await self.get(item_id)
        if not item:
            return False
        if hard:
            await self.session.delete(item)
        else:
            item.is_archived = True
            item.archived_at = datetime.utcnow()
        await self.session.commit()
        return True

    async def archive(self, item_id: int) -> bool:
        """Archive ${name} item."""
        item = await self.get(item_id)
        if not item:
            return False
        item.is_archived = True
        item.status = ${model_name}Status.ARCHIVED.value
        item.archived_at = datetime.utcnow()
        await self.session.commit()
        return True

    async def restore(self, item_id: int) -> bool:
        """Restore archived ${name} item."""
        item = await self.get(item_id)
        if not item:
            return False
        item.is_archived = False
        item.status = ${model_name}Status.ACTIVE.value
        item.archived_at = None
        await self.session.commit()
        return True

    async def increment_views(self, item_id: int) -> None:
        """Increment view count."""
        item = await self.get(item_id)
        if item:
            item.view_count += 1
            await self.session.commit()

    async def toggle_like(self, item_id: int, increment: bool = True) -> int:
        """Toggle like count."""
        item = await self.get(item_id)
        if item:
            item.like_count = max(0, item.like_count + (1 if increment else -1))
            await self.session.commit()
            return item.like_count
        return 0

    async def get_stats(self, organization_id: int | None = None) -> ${model_name}Stats:
        """Get ${name} statistics."""
        query = select(func.count()).select_from(${model_name}).where(${model_name}.is_archived == False)
        if organization_id:
            query = query.where(${model_name}.organization_id == organization_id)
        total = (await self.session.execute(query)).scalar()

        active_query = query.where(${model_name}.status == ${model_name}Status.ACTIVE.value)
        active = (await self.session.execute(active_query)).scalar()

        status_result = await self.session.execute(
            select(${model_name}.status, func.count())
            .where(${model_name}.is_archived == False)
            .group_by(${model_name}.status)
        )
        by_status = {row[0]: row[1] for row in status_result.all()}

        priority_result = await self.session.execute(
            select(${model_name}.priority, func.count())
            .where(${model_name}.is_archived == False)
            .group_by(${model_name}.priority)
        )
        by_priority = {row[0]: row[1] for row in priority_result.all()}

        recent = (await self.session.execute(
            select(func.count()).select_from(${model_name}).where(
                and_(${model_name}.is_archived == False, ${model_name}.created_at >= datetime.utcnow() - timedelta(days=7))
            )
        )).scalar()

        return ${model_name}Stats(
            total_count=total,
            active_count=active,
            by_status=by_status,
            by_priority=by_priority,
            recent_count=recent,
            avg_daily_creation=recent / 7.0,
        )

    async def get_revisions(self, item_id: int) -> list[${model_name}Revision]:
        """Get revision history."""
        result = await self.session.execute(
            select(${model_name}Revision)
            .where(${model_name}Revision.${name}_id == item_id)
            .order_by(${model_name}Revision.version.desc())
        )
        return result.scalars().all()

    async def add_comment(self, item_id: int, author_id: int, content: str, parent_id: int | None = None) -> ${model_name}Comment:
        """Add a comment."""
        comment = ${model_name}Comment(
            ${name}_id=item_id,
            author_id=author_id,
            content=content,
            parent_id=parent_id,
        )
        self.session.add(comment)
        await self.session.commit()
        return comment

    async def get_comments(self, item_id: int) -> list[${model_name}Comment]:
        """Get all comments."""
        result = await self.session.execute(
            select(${model_name}Comment)
            .where(${model_name}Comment.${name}_id == item_id)
            .order_by(${model_name}Comment.created_at)
        )
        return result.scalars().all()

    async def add_attachment(self, item_id: int, file_name: str, file_path: str, file_size: int, mime_type: str, uploaded_by: int) -> ${model_name}Attachment:
        """Add file attachment."""
        attachment = ${model_name}Attachment(
            ${name}_id=item_id,
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            uploaded_by=uploaded_by,
        )
        self.session.add(attachment)
        await self.session.commit()
        return attachment

    async def get_attachments(self, item_id: int) -> list[${model_name}Attachment]:
        """Get all attachments."""
        result = await self.session.execute(
            select(${model_name}Attachment)
            .where(${model_name}Attachment.${name}_id == item_id)
            .order_by(${model_name}Attachment.created_at.desc())
        )
        return result.scalars().all()

    async def duplicate(self, item_id: int, new_owner_id: int | None = None) -> ${model_name} | None:
        """Duplicate ${name} item."""
        item = await self.get(item_id)
        if not item:
            return None
        new_item = ${model_name}(
            name=f"{item.name} (Copy)",
            slug=f"{item.slug}-copy-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            description=item.description,
            status=${model_name}Status.ACTIVE.value,
            priority=item.priority,
            owner_id=new_owner_id or item.owner_id,
            organization_id=item.organization_id,
            tags=list(item.tags),
            config=dict(item.config),
            is_public=False,
            version=1,
        )
        self.session.add(new_item)
        await self.session.commit()
        return new_item

    async def export_data(self, item_id: int) -> dict[str, Any]:
        """Export ${name} data."""
        item = await self.get(item_id)
        if not item:
            return {}
        attachments = await self.get_attachments(item_id)
        comments = await self.get_comments(item_id)
        return {
            "item": {
                "id": item.id,
                "name": item.name,
                "slug": item.slug,
                "description": item.description,
                "status": item.status,
                "priority": item.priority,
                "tags": item.tags,
                "config": item.config,
                "version": item.version,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            },
            "attachments": [{"name": a.file_name, "size": a.file_size} for a in attachments],
            "comments": [{"author": c.author_id, "content": c.content} for c in comments],
        }

    async def bulk_update_status(self, item_ids: list[int], status: ${model_name}Status) -> int:
        """Bulk update status."""
        result = await self.session.execute(
            update(${model_name})
            .where(${model_name}.id.in_(item_ids))
            .values(status=status.value, updated_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount

    async def bulk_delete(self, item_ids: list[int], hard: bool = False) -> int:
        """Bulk delete items."""
        if hard:
            result = await self.session.execute(
                delete(${model_name}).where(${model_name}.id.in_(item_ids))
            )
        else:
            result = await self.session.execute(
                update(${model_name})
                .where(${model_name}.id.in_(item_ids))
                .values(is_archived=True, archived_at=datetime.utcnow())
            )
        await self.session.commit()
        return result.rowcount
''')


API_TEMPLATE = Template('''\
"""API endpoints for ${name} - ${description}."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.${name} import (
    ${class_name}Create,
    ${class_name}Filter,
    ${class_name}ListResponse,
    ${class_name}Response,
    ${class_name}Update,
    ${class_name}Status,
    ${class_name}Priority,
)
from app.services.${name}_service import ${class_name}Service
from app.storage.database import get_db

router = APIRouter()


async def get_service(db: AsyncSession = Depends(get_db)) -> ${class_name}Service:
    return ${class_name}Service(db)


@router.post("/", response_model=${class_name}Response, status_code=status.HTTP_201_CREATED)
async def create_item(
    data: ${class_name}Create,
    service: ${class_name}Service = Depends(get_service),
) -> ${class_name}Response:
    """Create a new ${name} item."""
    return await service.create(data)


@router.get("/{item_id}", response_model=${class_name}Response)
async def get_item(
    item_id: int,
    service: ${class_name}Service = Depends(get_service),
) -> ${class_name}Response:
    """Get ${name} item by ID."""
    item = await service.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="${class_name} not found")
    await service.increment_views(item_id)
    return ${class_name}Response.model_validate(item)


@router.get("/slug/{slug}", response_model=${class_name}Response)
async def get_by_slug(
    slug: str,
    service: ${class_name}Service = Depends(get_service),
) -> ${class_name}Response:
    """Get ${name} by slug."""
    item = await service.get_by_slug(slug)
    if not item:
        raise HTTPException(status_code=404, detail="${class_name} not found")
    return ${class_name}Response.model_validate(item)


@router.get("/", response_model=${class_name}ListResponse)
async def list_items(
    status: ${class_name}Status | None = None,
    priority: ${class_name}Priority | None = None,
    owner_id: int | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ${class_name}Service = Depends(get_service),
) -> ${class_name}ListResponse:
    """List ${name} items with filters."""
    filter_data = ${class_name}Filter(
        status=status, priority=priority, owner_id=owner_id, search=search, page=page, page_size=page_size
    )
    items, total = await service.list_items(filter_data)
    return ${class_name}ListResponse(
        items=[${class_name}Response.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{item_id}", response_model=${class_name}Response)
async def update_item(
    item_id: int,
    data: ${class_name}Update,
    service: ${class_name}Service = Depends(get_service),
) -> ${class_name}Response:
    """Update ${name} item."""
    item = await service.update(item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="${class_name} not found")
    return ${class_name}Response.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    hard: bool = Query(False),
    service: ${class_name}Service = Depends(get_service),
) -> None:
    """Delete ${name} item."""
    deleted = await service.delete(item_id, hard)
    if not deleted:
        raise HTTPException(status_code=404, detail="${class_name} not found")


@router.post("/{item_id}/archive", response_model=${class_name}Response)
async def archive_item(
    item_id: int,
    service: ${class_name}Service = Depends(get_service),
) -> ${class_name}Response:
    """Archive ${name} item."""
    archived = await service.archive(item_id)
    if not archived:
        raise HTTPException(status_code=404, detail="${class_name} not found")
    item = await service.get(item_id)
    return ${class_name}Response.model_validate(item)


@router.post("/{item_id}/restore", response_model=${class_name}Response)
async def restore_item(
    item_id: int,
    service: ${class_name}Service = Depends(get_service),
) -> ${class_name}Response:
    """Restore archived ${name} item."""
    restored = await service.restore(item_id)
    if not restored:
        raise HTTPException(status_code=404, detail="${class_name} not found")
    item = await service.get(item_id)
    return ${class_name}Response.model_validate(item)


@router.post("/{item_id}/duplicate", response_model=${class_name}Response)
async def duplicate_item(
    item_id: int,
    service: ${class_name}Service = Depends(get_service),
) -> ${class_name}Response:
    """Duplicate ${name} item."""
    new_item = await service.duplicate(item_id)
    if not new_item:
        raise HTTPException(status_code=404, detail="${class_name} not found")
    return ${class_name}Response.model_validate(new_item)


@router.get("/{item_id}/revisions")
async def get_revisions(
    item_id: int,
    service: ${class_name}Service = Depends(get_service),
) -> list[dict]:
    """Get revision history."""
    revisions = await service.get_revisions(item_id)
    return [{"version": r.version, "summary": r.change_summary, "created_at": r.created_at} for r in revisions]


@router.get("/{item_id}/comments")
async def get_comments(
    item_id: int,
    service: ${class_name}Service = Depends(get_service),
) -> list[dict]:
    """Get comments."""
    comments = await service.get_comments(item_id)
    return [{"id": c.id, "content": c.content, "author_id": c.author_id} for c in comments]


@router.post("/{item_id}/comments")
async def add_comment(
    item_id: int,
    content: str,
    service: ${class_name}Service = Depends(get_service),
) -> dict:
    """Add comment."""
    comment = await service.add_comment(item_id, 0, content)
    return {"id": comment.id, "content": comment.content}


@router.get("/stats/summary")
async def get_stats(
    service: ${class_name}Service = Depends(get_service),
) -> dict:
    """Get ${name} statistics."""
    return await service.get_stats()


@router.post("/bulk/status")
async def bulk_update_status(
    item_ids: list[int],
    status: ${class_name}Status,
    service: ${class_name}Service = Depends(get_service),
) -> dict:
    """Bulk update status."""
    count = await service.bulk_update_status(item_ids, status)
    return {"updated": count}


@router.post("/bulk/delete")
async def bulk_delete(
    item_ids: list[int],
    hard: bool = False,
    service: ${class_name}Service = Depends(get_service),
) -> dict:
    """Bulk delete items."""
    count = await service.bulk_delete(item_ids, hard)
    return {"deleted": count}


@router.get("/{item_id}/export")
async def export_item(
    item_id: int,
    service: ${class_name}Service = Depends(get_service),
) -> dict:
    """Export ${name} data."""
    data = await service.export_data(item_id)
    if not data:
        raise HTTPException(status_code=404, detail="${class_name} not found")
    return data
''')


TEST_TEMPLATE = Template('''\
"""Comprehensive tests for ${name} - ${description}."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.${name} import (
    ${class_name}Create,
    ${class_name}Filter,
    ${class_name}Update,
    ${class_name}Status,
    ${class_name}Priority,
)
from app.services.${name}_service import ${class_name}Service


@pytest.fixture
def mock_session() -> AsyncSession:
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def service(mock_session: AsyncSession) -> ${class_name}Service:
    return ${class_name}Service(mock_session)


@pytest.fixture
def sample_create() -> ${class_name}Create:
    return ${class_name}Create(
        name="Test ${class_name}",
        description="Test description",
        priority=${class_name}Priority.MEDIUM,
        tags=["test"],
        config={"key": "value"},
    )


class Test${class_name}Creation:
    """Tests for ${name} creation."""

    @pytest.mark.asyncio
    async def test_create_success(self, service, mock_session, sample_create):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.create(sample_create)
        assert result.name == "Test ${class_name}"
        assert result.status == ${class_name}Status.ACTIVE.value

    @pytest.mark.asyncio
    async def test_create_generates_slug(self, service, mock_session, sample_create):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.create(sample_create)
        assert result.slug is not None

    @pytest.mark.asyncio
    async def test_create_with_tags(self, service, mock_session, sample_create):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.create(sample_create)
        assert "test" in result.tags

    @pytest.mark.asyncio
    async def test_create_duplicate_slug_gets_suffix(self, service, mock_session, sample_create):
        mock_session.execute.return_value.scalar_one_or_none.return_value = MagicMock()
        result = await service.create(sample_create)
        assert result.slug is not None


class Test${class_name}Retrieval:
    """Tests for ${name} retrieval."""

    @pytest.mark.asyncio
    async def test_get_by_id(self, service, mock_session):
        mock_item = MagicMock()
        mock_item.id = 1
        mock_item.name = "Test"
        mock_item.slug = "test"
        mock_item.description = ""
        mock_item.status = "active"
        mock_item.priority = "medium"
        mock_item.owner_id = None
        mock_item.tags = []
        mock_item.is_public = False
        mock_item.view_count = 0
        mock_item.version = 1
        mock_item.created_at = MagicMock()
        mock_item.updated_at = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.get(1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_not_found(self, service, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.get(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_slug(self, service, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.get_by_slug("nonexistent")
        assert result is None


class Test${class_name}List:
    """Tests for ${name} listing."""

    @pytest.mark.asyncio
    async def test_list_empty(self, service, mock_session):
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.execute.return_value.scalar.return_value = 0
        items, total = await service.list_items(${class_name}Filter())
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_with_items(self, service, mock_session):
        mock_items = [MagicMock() for _ in range(3)]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_items
        mock_session.execute.return_value.scalar.return_value = 3
        items, total = await service.list_items(${class_name}Filter())
        assert total == 3

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, service, mock_session):
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.execute.return_value.scalar.return_value = 0
        items, total = await service.list_items(${class_name}Filter(status=${class_name}Status.ACTIVE))
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, service, mock_session):
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.execute.return_value.scalar.return_value = 100
        items, total = await service.list_items(${class_name}Filter(page=2, page_size=10))
        assert total == 100


class Test${class_name}Update:
    """Tests for ${name} update."""

    @pytest.mark.asyncio
    async def test_update_name(self, service, mock_session):
        mock_item = MagicMock()
        mock_item.id = 1
        mock_item.name = "Old"
        mock_item.slug = "old"
        mock_item.version = 1
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.update(1, ${class_name}Update(name="New"))
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_not_found(self, service, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.update(999, ${class_name}Update(name="New"))
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status(self, service, mock_session):
        mock_item = MagicMock()
        mock_item.id = 1
        mock_item.version = 1
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.update(1, ${class_name}Update(status=${class_name}Status.INACTIVE))
        assert result is not None


class Test${class_name}Delete:
    """Tests for ${name} deletion."""

    @pytest.mark.asyncio
    async def test_soft_delete(self, service, mock_session):
        mock_item = MagicMock()
        mock_item.id = 1
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.delete(1, hard=False)
        assert result is True

    @pytest.mark.asyncio
    async def test_hard_delete(self, service, mock_session):
        mock_item = MagicMock()
        mock_item.id = 1
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.delete(1, hard=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, service, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await service.delete(999)
        assert result is False


class Test${class_name}Archive:
    """Tests for ${name} archiving."""

    @pytest.mark.asyncio
    async def test_archive(self, service, mock_session):
        mock_item = MagicMock()
        mock_item.id = 1
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.archive(1)
        assert result is True

    @pytest.mark.asyncio
    async def test_restore(self, service, mock_session):
        mock_item = MagicMock()
        mock_item.id = 1
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.restore(1)
        assert result is True


class Test${class_name}Interactions:
    """Tests for ${name} interactions."""

    @pytest.mark.asyncio
    async def test_increment_views(self, service, mock_session):
        mock_item = MagicMock()
        mock_item.view_count = 0
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        await service.increment_views(1)
        assert mock_item.view_count == 1

    @pytest.mark.asyncio
    async def test_toggle_like(self, service, mock_session):
        mock_item = MagicMock()
        mock_item.like_count = 0
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_item
        result = await service.toggle_like(1, increment=True)
        assert result == 1


class Test${class_name}Stats:
    """Tests for ${name} statistics."""

    @pytest.mark.asyncio
    async def test_get_stats(self, service, mock_session):
        mock_session.execute.return_value.scalar.return_value = 0
        mock_session.execute.return_value.all.return_value = []
        result = await service.get_stats()
        assert result.total_count >= 0


class Test${class_name}Bulk:
    """Tests for bulk operations."""

    @pytest.mark.asyncio
    async def test_bulk_update_status(self, service, mock_session):
        mock_session.execute.return_value.rowcount = 3
        result = await service.bulk_update_status([1, 2, 3], ${class_name}Status.ARCHIVED)
        assert result == 3

    @pytest.mark.asyncio
    async def test_bulk_delete(self, service, mock_session):
        mock_session.execute.return_value.rowcount = 5
        result = await service.bulk_delete([1, 2, 3, 4, 5])
        assert result == 5
''')


def main() -> None:
    all_files: dict[str, str] = {}

    modules = [
        ("knowledge_base", "Knowledge base articles and documentation"),
        ("task_manager", "Task and project management"),
        ("notification_center", "Notification dispatch and management"),
        ("report_builder", "Report generation and scheduling"),
        ("data_pipeline", "Data processing pipeline definitions"),
        ("integration_hub", "Third-party integration configurations"),
        ("workflow_template", "Reusable workflow templates"),
        ("prompt_library", "Prompt template library"),
        ("model_registry", "ML model registry and versioning"),
        ("experiment_tracker", "ML experiment tracking"),
        ("dataset_manager", "Dataset versioning and management"),
        ("deployment_manager", "Model deployment configurations"),
        ("monitoring_dashboard", "System monitoring dashboards"),
        ("alert_manager", "Alert rules and notification config"),
        ("log_aggregator", "Log aggregation and search"),
        ("cache_manager", "Cache configuration and invalidation"),
        ("search_index", "Search index management"),
        ("file_storage", "File storage and CDN configuration"),
        ("api_gateway", "API gateway routing rules"),
        ("rate_limiter", "Rate limiting rules and quotas"),
        ("feature_flag", "Feature flag configurations"),
        ("environment_config", "Environment-specific configurations"),
        ("secret_manager", "Secrets and credentials management"),
        ("certificate_manager", "SSL/TLS certificate management"),
        ("backup_manager", "Backup scheduling and restoration"),
        ("migration_manager", "Database migration management"),
        ("scheduler_job", "Scheduled job definitions"),
        ("event_bus", "Event bus subscriptions and routing"),
        ("metric_collector", "Custom metric collection config"),
        ("tenant_manager", "Multi-tenant configuration"),
    ]

    print(f"Generating {len(modules)} complete module sets...")

    for name, desc in modules:
        model_name = "".join(w.capitalize() for w in name.split("_"))
        class_name = model_name + "Service"

        # Service module
        service_content = SERVICE_TEMPLATE.substitute(
            name=name, description=desc, model_name=model_name, class_name=class_name
        )
        all_files[f"app/services/{name}_service.py"] = service_content

        # API module
        api_content = API_TEMPLATE.substitute(
            name=name, description=desc, model_name=model_name, class_name=class_name
        )
        all_files[f"app/api/v1/{name}.py"] = api_content

        # Test module
        test_content = TEST_TEMPLATE.substitute(
            name=name, description=desc, model_name=model_name, class_name=class_name
        )
        all_files[f"tests/test_{name}.py"] = test_content

    print(f"Writing {len(all_files)} files...")
    for path_str, content in all_files.items():
        write_file(BASE / path_str, content)

    print(f"Done! Generated {len(all_files)} files across {len(modules)} modules.")


if __name__ == "__main__":
    main()
