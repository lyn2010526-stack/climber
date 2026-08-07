"""Domain: client."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ClientStatus(Enum):
    """Status enum."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    PENDING = 'pending'
    ARCHIVED = 'archived'


@dataclass
class ClientEntity:
    """Entity."""
    id: str = ''
    name: str = ''
    description: str = ''
    status: ClientStatus = ClientStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClientCreateDTO:
    """Create DTO."""
    name: str = ''
    description: str = ''
    metadata: dict[str, Any] | None = None


@dataclass
class ClientUpdateDTO:
    """Update DTO."""
    name: str | None = None
    description: str | None = None
    status: ClientStatus | None = None
    metadata: dict[str, Any] | None = None


class ClientRepository:
    """Repository."""

    def __init__(self):
        self._store: dict[str, ClientEntity] = {}

    async def create(self, dto: ClientCreateDTO) -> ClientEntity:
        """Create."""
        import uuid
        entity = ClientEntity(
            id=str(uuid.uuid4()),
            name=dto.name,
            description=dto.description,
            metadata=dto.metadata or {},
        )
        self._store[entity.id] = entity
        return entity

    async def get(self, entity_id: str) -> ClientEntity | None:
        """Get."""
        return self._store.get(entity_id)

    async def update(self, entity_id: str, dto: ClientUpdateDTO) -> ClientEntity | None:
        """Update."""
        entity = self._store.get(entity_id)
        if entity is None:
            return None
        if dto.name is not None:
            entity.name = dto.name
        if dto.description is not None:
            entity.description = dto.description
        if dto.status is not None:
            entity.status = dto.status
        entity.updated_at = datetime.utcnow()
        return entity

    async def delete(self, entity_id: str) -> bool:
        """Delete."""
        if entity_id in self._store:
            del self._store[entity_id]
            return True
        return False

    async def list_all(self, status: ClientStatus | None = None) -> list[ClientEntity]:
        """List all."""
        entities = list(self._store.values())
        if status:
            entities = [e for e in entities if e.status == status]
        return entities
