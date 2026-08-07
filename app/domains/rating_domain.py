"""Domain model: rating - Business domain entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4


class RatingEntityType(StrEnum):
    """Entity type enum."""
    INDIVIDUAL = 'individual'
    ORGANIZATION = 'organization'
    SYSTEM = 'system'
    AUTOMATED = 'automated'


class RatingStatus(StrEnum):
    """Status enum."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    PENDING = 'pending'
    SUSPENDED = 'suspended'
    ARCHIVED = 'archived'


class RatingPriority(StrEnum):
    """Priority enum."""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


@dataclass
class RatingAddress:
    """Address value object."""
    street: str = ''
    city: str = ''
    state: str = ''
    postal_code: str = ''
    country: str = 'US'


@dataclass
class RatingContact:
    """Contact value object."""
    email: str = ''
    phone: str = ''
    fax: str = ''
    website: str = ''


@dataclass
class RatingMoney:
    """Money value object."""
    amount: Decimal = Decimal('0.00')
    currency: str = 'USD'


@dataclass
class RatingTimeRange:
    """Time range value object."""
    start: datetime | None = None
    end: datetime | None = None


@dataclass
class RatingEntity:
    """Base entity."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ''
    description: str = ''
    entity_type: str = 'individual'
    status: str = 'active'
    priority: str = 'medium'
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ''
    updated_by: str = ''
    version: int = 1
    is_deleted: bool = False


@dataclass
class RatingAuditEntry:
    """Audit entry."""
    id: str = field(default_factory=lambda: str(uuid4()))
    entity_id: str = ''
    entity_type: str = ''
    action: str = ''
    changes: dict[str, Any] = field(default_factory=dict)
    actor: str = ''
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ip_address: str = ''
    user_agent: str = ''


@dataclass
class RatingRelationship:
    """Entity relationship."""
    id: str = field(default_factory=lambda: str(uuid4()))
    source_id: str = ''
    target_id: str = ''
    relationship_type: str = ''
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class RatingEntityFactory:
    """Entity factory."""

    @staticmethod
    def create(
        name: str,
        entity_type: str = 'individual',
        **kwargs: Any,
    ) -> RatingEntity:
        """Create new entity."""
        return RatingEntity(name=name, entity_type=entity_type, **kwargs)

    @staticmethod
    def create_from_dict(data: dict[str, Any]) -> RatingEntity:
        """Create entity from dict."""
        return RatingEntity(**{k: v for k, v in data.items() if hasattr(RatingEntity, k)})


class RatingEntityRepository:
    """Entity repository."""

    def __init__(self):
        self._entities: dict[str, RatingEntity] = {}
        self._indexes: dict[str, dict[str, set[str]]] = {}

    def save(self, entity: RatingEntity) -> str:
        """Save entity."""
        entity.updated_at = datetime.utcnow()
        entity.version += 1
        self._entities[entity.id] = entity
        self._update_indexes(entity)
        return entity.id

    def find_by_id(self, entity_id: str) -> RatingEntity | None:
        """Find by ID."""
        return self._entities.get(entity_id)

    def find_all(
        self,
        status: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RatingEntity]:
        """Find all with filters."""
        results = list(self._entities.values())
        if status:
            results = [e for e in results if e.status == status]
        if entity_type:
            results = [e for e in results if e.entity_type == entity_type]
        return results[offset:offset + limit]

    def delete(self, entity_id: str) -> bool:
        """Soft delete entity."""
        entity = self._entities.get(entity_id)
        if entity:
            entity.is_deleted = True
            entity.status = 'archived'
            return True
        return False

    def hard_delete(self, entity_id: str) -> bool:
        """Hard delete entity."""
        if entity_id in self._entities:
            del self._entities[entity_id]
            return True
        return False

    def count(self, status: str | None = None) -> int:
        """Count entities."""
        if status:
            return sum(1 for e in self._entities.values() if e.status == status)
        return len(self._entities)

    def _update_indexes(self, entity: RatingEntity) -> None:
        """Update indexes."""
        if 'status' not in self._indexes:
            self._indexes['status'] = {}
        if entity.status not in self._indexes['status']:
            self._indexes['status'][entity.status] = set()
        self._indexes['status'][entity.status].add(entity.id)


class RatingValidator:
    """Entity validator."""

    @staticmethod
    def validate(entity: RatingEntity) -> list[str]:
        """Validate entity."""
        errors = []
        if not entity.name:
            errors.append('Name is required')
        if len(entity.name) > 255:
            errors.append('Name too long')
        if entity.status not in ('active', 'inactive', 'pending', 'suspended', 'archived'):
            errors.append('Invalid status')
        if entity.priority not in ('low', 'medium', 'high', 'critical'):
            errors.append('Invalid priority')
        return errors

    @staticmethod
    def is_valid(entity: RatingEntity) -> bool:
        """Check if entity is valid."""
        return len(RatingValidator.validate(entity)) == 0
