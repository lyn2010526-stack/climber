"""Schema: decision - Pydantic schemas for data validation."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DecisionStatus(StrEnum):
    """Status enum."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    PENDING = 'pending'
    SUSPENDED = 'suspended'
    ARCHIVED = 'archived'


class DecisionPriority(StrEnum):
    """Priority enum."""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class DecisionCategory(StrEnum):
    """Category enum."""
    GENERAL = 'general'
    TECHNICAL = 'technical'
    BUSINESS = 'business'
    PERSONAL = 'personal'
    OTHER = 'other'


class DecisionBase(BaseModel):
    """Base schema with common fields."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    name: str = Field(..., min_length=1, max_length=255, description='Name')
    description: str = Field(default='', max_length=2000, description='Description')
    status: DecisionStatus = Field(default=DecisionStatus.ACTIVE, description='Status')
    priority: DecisionPriority = Field(default=DecisionPriority.MEDIUM, description='Priority')
    category: DecisionCategory = Field(default=DecisionCategory.GENERAL, description='Category')
    tags: list[str] = Field(default_factory=list, max_length=50, description='Tags')
    is_active: bool = Field(default=True, description='Whether active')
    is_archived: bool = Field(default=False, description='Whether archived')
    sort_order: int = Field(default=0, ge=0, le=99999, description='Sort order')
    metadata: dict[str, Any] = Field(default_factory=dict, description='Metadata')


class DecisionCreate(DecisionBase):
    """Create schema."""

    name: str = Field(..., min_length=1, max_length=255)
    owner_id: int | None = Field(default=None, description='Owner ID')
    parent_id: int | None = Field(default=None, description='Parent ID')

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name."""
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty')
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters')
        return v

    @field_validator('tags', mode='before')
    @classmethod
    def validate_tags(cls, v: Any) -> list[str]:
        """Validate tags."""
        if v is None:
            return []
        if isinstance(v, str):
            return [t.strip() for t in v.split(',') if t.strip()]
        if isinstance(v, list):
            return [str(t).strip() for t in v if str(t).strip()]
        return []


class DecisionUpdate(BaseModel):
    """Update schema."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    status: DecisionStatus | None = None
    priority: DecisionPriority | None = None
    category: DecisionCategory | None = None
    tags: list[str] | None = None
    is_active: bool | None = None
    is_archived: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=99999)
    metadata: dict[str, Any] | None = None


class DecisionResponse(DecisionBase):
    """Response schema."""

    id: int = Field(..., description='ID')
    uuid: UUID = Field(default_factory=UUID, description='UUID')
    created_at: datetime = Field(..., description='Created at')
    updated_at: datetime = Field(..., description='Updated at')
    created_by: int | None = Field(default=None, description='Created by')
    updated_by: int | None = Field(default=None, description='Updated by')
    owner_id: int | None = Field(default=None, description='Owner ID')
    parent_id: int | None = Field(default=None, description='Parent ID')
    version: int = Field(default=1, description='Version')


class DecisionListResponse(BaseModel):
    """List response schema."""

    items: list[DecisionResponse] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    total_pages: int = Field(default=0, ge=0)


class DecisionFilter(BaseModel):
    """Filter schema."""

    search: str | None = Field(default=None, max_length=255)
    status: DecisionStatus | None = None
    priority: DecisionPriority | None = None
    category: DecisionCategory | None = None
    is_active: bool | None = None
    is_archived: bool | None = None
    tags: list[str] | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    updated_from: datetime | None = None
    updated_to: datetime | None = None
    owner_id: int | None = None
    parent_id: int | None = None


class DecisionSort(BaseModel):
    """Sort schema."""

    sort_by: str = Field(default='created_at')
    sort_order: str = Field(default='desc', pattern='^(asc|desc)$')


class DecisionBulkAction(BaseModel):
    """Bulk action schema."""

    ids: list[int] = Field(..., min_length=1, description='IDs')
    action: str = Field(..., description='Action')


class DecisionStats(BaseModel):
    """Stats schema."""

    total: int = 0
    active: int = 0
    inactive: int = 0
    pending: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
