#!/usr/bin/env python3
"""Generate data models, DTOs, and serialization logic."""

from __future__ import annotations

from pathlib import Path

BASE = Path("/workspace/agent-engine")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def gen_model_file(name: str, class_name: str) -> str:
    return f'''"""Data models and DTOs for {name}."""

from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, Float,
    Numeric, JSON, ForeignKey, Index, UniqueConstraint, CheckConstraint,
    Enum as SAEnum, BigInteger, SmallInteger, Table
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY

import structlog

logger = structlog.get_logger()
Base = declarative_base()


# --- Enums ---

class {class_name}Status(str, Enum):
    """Status values for {name}."""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    DELETED = "deleted"


class {class_name}Type(str, Enum):
    """Type classification for {name}."""
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class {class_name}Priority(str, Enum):
    """Priority levels for {name}."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"


# --- Database Models ---

class {class_name}(Base):
    """Primary {name} database model."""
    __tablename__ = "{name}"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    name = Column(String(256), nullable=False, index=True)
    slug = Column(String(256), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    status = Column(String(32), default={class_name}Status.DRAFT.value, nullable=False)
    type = Column(String(32), default={class_name}Type.STANDARD.value)
    priority = Column(String(32), default={class_name}Priority.MEDIUM.value)

    # Ownership
    owner_id = Column(Integer, nullable=True, index=True)
    organization_id = Column(Integer, nullable=True, index=True)
    created_by = Column(Integer, nullable=True, index=True)
    updated_by = Column(Integer, nullable=True)

    # Content
    content = Column(Text, default="")
    content_html = Column(Text, default="")
    metadata_json = Column(JSON, default=dict)
    settings = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    categories = Column(JSON, default=list)

    # Metrics
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    rating_average = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)

    # Financial
    price = Column(Numeric(10, 2), default=0)
    currency = Column(String(8), default="USD")

    # Flags
    is_public = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    allow_comments = Column(Boolean, default=True)
    allow_ratings = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    revisions = relationship("{class_name}Revision", back_populates="parent", cascade="all, delete-orphan")
    comments = relationship("{class_name}Comment", back_populates="parent", cascade="all, delete-orphan")
    attachments = relationship("{class_name}Attachment", back_populates="parent", cascade="all, delete-orphan")

    __table_args__ = (
        Index("{name}_owner_status", "owner_id", "status"),
        Index("{name}_org_status", "organization_id", "status"),
        Index("{name}_type_status", "type", "status"),
        Index("{name}_created_at", "created_at"),
        Index("{name}_published", "published_at", "status"),
    )


class {class_name}Revision(Base):
    """Revision history for {name}."""
    __tablename__ = "{name}_revisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    {name}_id = Column(Integer, ForeignKey("{name}.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)
    change_summary = Column(String(512), default="")
    changed_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    parent = relationship("{class_name}", back_populates="revisions")


class {class_name}Comment(Base):
    """Comments on {name} items."""
    __tablename__ = "{name}_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    {name}_id = Column(Integer, ForeignKey("{name}.id"), nullable=False, index=True)
    author_id = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_id = Column(Integer, nullable=True)
    is_resolved = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = relationship("{class_name}", back_populates="comments")


class {class_name}Attachment(Base):
    """File attachments for {name}."""
    __tablename__ = "{name}_attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    {name}_id = Column(Integer, ForeignKey("{name}.id"), nullable=False, index=True)
    file_name = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(BigInteger, default=0)
    mime_type = Column(String(128), default="")
    file_hash = Column(String(128), default="")
    is_public = Column(Boolean, default=True)
    download_count = Column(Integer, default=0)
    uploaded_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    parent = relationship("{class_name}", back_populates="attachments")


class {class_name}Tag(Base):
    """Tags for {name} categorization."""
    __tablename__ = "{name}_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    slug = Column(String(128), unique=True, nullable=False)
    description = Column(String(512), default="")
    color = Column(String(16), default="#6B7280")
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class {class_name}Category(Base):
    """Categories for {name} organization."""
    __tablename__ = "{name}_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    slug = Column(String(256), unique=True, nullable=False)
    description = Column(Text, default="")
    parent_id = Column(Integer, nullable=True, index=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    item_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class {class_name}Like(Base):
    """User likes for {name} items."""
    __tablename__ = "{name}_likes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    {name}_id = Column(Integer, ForeignKey("{name}.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("{name}_id", "user_id", name="uq_{name}_like"),
    )


class {class_name}View(Base):
    """View tracking for {name} items."""
    __tablename__ = "{name}_views"

    id = Column(Integer, primary_key=True, autoincrement=True)
    {name}_id = Column(Integer, ForeignKey("{name}.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    ip_address = Column(String(64), default="")
    user_agent = Column(String(512), default="")
    referer = Column(String(512), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class {class_name}Rating(Base):
    """User ratings for {name} items."""
    __tablename__ = "{name}_ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    {name}_id = Column(Integer, ForeignKey("{name}.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    score = Column(Integer, nullable=False)
    review = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("{name}_id", "user_id", name="uq_{name}_rating"),
        CheckConstraint("score >= 1 AND score <= 5", name="ck_{name}_rating_score"),
    )


# --- Pydantic DTOs ---

class {class_name}CreateDTO(BaseModel):
    """DTO for creating {name}."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=256)
    description: str = ""
    content: str = ""
    type: {class_name}Type = {class_name}Type.STANDARD
    priority: {class_name}Priority = {class_name}Priority.MEDIUM
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)
    is_public: bool = False
    price: Decimal = Decimal("0.00")
    currency: str = "USD"
    expires_at: datetime | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        return [tag.strip().lower() for tag in v if tag.strip()]

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v


class {class_name}UpdateDTO(BaseModel):
    """DTO for updating {name}."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = None
    content: str | None = None
    status: {class_name}Status | None = None
    type: {class_name}Type | None = None
    priority: {class_name}Priority | None = None
    tags: list[str] | None = None
    categories: list[str] | None = None
    metadata: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None
    is_public: bool | None = None
    price: Decimal | None = None
    expires_at: datetime | None = None


class {class_name}ResponseDTO(BaseModel):
    """DTO for {name} response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    name: str
    slug: str
    description: str
    status: str
    type: str
    priority: str
    owner_id: int | None
    organization_id: int | None
    tags: list[str]
    categories: list[str]
    view_count: int
    like_count: int
    rating_average: float
    is_public: bool
    is_featured: bool
    price: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class {class_name}ListDTO(BaseModel):
    """DTO for paginated {name} list."""
    items: list[{class_name}ResponseDTO]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class {class_name}FilterDTO(BaseModel):
    """DTO for {name} filtering."""
    search: str | None = None
    status: {class_name}Status | None = None
    type: {class_name}Type | None = None
    priority: {class_name}Priority | None = None
    owner_id: int | None = None
    organization_id: int | None = None
    tags: list[str] | None = None
    is_public: bool | None = None
    is_featured: bool | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class {class_name}StatsDTO(BaseModel):
    """DTO for {name} statistics."""
    total_count: int
    active_count: int
    draft_count: int
    archived_count: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    by_priority: dict[str, int]
    total_views: int
    total_likes: int
    avg_rating: float
    recent_count: int
    period_start: datetime
    period_end: datetime


class {class_name}ExportDTO(BaseModel):
    """DTO for {name} export."""
    format: str = "json"
    include_revisions: bool = False
    include_comments: bool = False
    include_attachments: bool = False
    filter: {class_name}FilterDTO | None = None


class {class_name}ImportDTO(BaseModel):
    """DTO for {name} import."""
    data: list[dict[str, Any]]
    skip_validation: bool = False
    update_existing: bool = False
    batch_size: int = 100


class {class_name}BulkActionDTO(BaseModel):
    """DTO for bulk actions on {name}."""
    ids: list[int] = Field(..., min_length=1)
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


# --- Serialization helpers ---

class {class_name}Serializer:
    """Serialization utilities for {name}."""

    @staticmethod
    def to_dict(obj: {class_name}) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {{
            "id": obj.id,
            "uuid": obj.uuid,
            "name": obj.name,
            "slug": obj.slug,
            "description": obj.description,
            "status": obj.status,
            "type": obj.type,
            "priority": obj.priority,
            "owner_id": obj.owner_id,
            "tags": obj.tags,
            "view_count": obj.view_count,
            "like_count": obj.like_count,
            "rating_average": obj.rating_average,
            "is_public": obj.is_public,
            "price": float(obj.price) if obj.price else 0,
            "currency": obj.currency,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        }}

    @staticmethod
    def to_list(items: list[{class_name}]) -> list[dict[str, Any]]:
        """Convert list of models to list of dictionaries."""
        return [{class_name}Serializer.to_dict(item) for item in items]

    @staticmethod
    def from_dict(data: dict[str, Any]) -> {class_name}CreateDTO:
        """Create DTO from dictionary."""
        return {class_name}CreateDTO(**data)

    @staticmethod
    def to_response(obj: {class_name}) -> {class_name}ResponseDTO:
        """Convert model to response DTO."""
        return {class_name}ResponseDTO.model_validate(obj)
'''


def main() -> None:
    all_files: dict[str, str] = {}

    models = [
        "article", "blog_post", "faq_item", "tutorial", "documentation",
        "video", "podcast", "webinar", "course", "lesson",
        "quiz", "assignment", "project", "milestone", "deliverable",
        "ticket", "issue", "bug_report", "feature_request", "change_request",
        "incident", "problem", "release", "deployment", "build",
        "test_case", "test_suite", "test_result", "coverage_report", "quality_gate",
    ]

    print(f"Generating {len(models)} model files...")

    for name in models:
        class_name = "".join(w.capitalize() for w in name.split("_"))
        content = gen_model_file(name, class_name)
        all_files[f"app/models/{name}_models.py"] = content

    print(f"Writing {len(all_files)} files...")
    for path_str, content in all_files.items():
        write_file(BASE / path_str, content)

    print(f"Done! Generated {len(all_files)} model files.")


if __name__ == "__main__":
    main()
