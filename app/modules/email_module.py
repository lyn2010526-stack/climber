"""Module: email."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EmailType(Enum):
    """Type enum."""
    TYPE_A = 'type_a'
    TYPE_B = 'type_b'
    TYPE_C = 'type_c'


@dataclass
class EmailConfig:
    """Config."""
    name: str = 'email'
    enabled: bool = True
    max_items: int = 1000
    timeout: float = 30.0
    retry_count: int = 3


@dataclass
class EmailItem:
    """Item."""
    id: str = ''
    name: str = ''
    type: EmailType = EmailType.TYPE_A
    data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EmailResult:
    """Result."""
    success: bool = False
    items: list[EmailItem] = field(default_factory=list)
    total: int = 0
    error: str | None = None


class EmailManager:
    """Manager."""

    def __init__(self, config: EmailConfig | None = None):
        self.config = config or EmailConfig()
        self._items: dict[str, EmailItem] = {}
        self._hooks: dict[str, list[Callable]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize."""
        self._initialized = True
        logger.info(f'{self.config.name} manager initialized')

    async def create(self, name: str, type_: EmailType, data: dict | None = None) -> EmailItem:
        """Create."""
        import uuid
        item = EmailItem(
            id=str(uuid.uuid4()),
            name=name,
            type=type_,
            data=data or {},
        )
        self._items[item.id] = item
        await self._fire_hook('create', item)
        return item

    async def get(self, item_id: str) -> EmailItem | None:
        """Get."""
        return self._items.get(item_id)

    async def update(self, item_id: str, **fields) -> EmailItem | None:
        """Update."""
        item = self._items.get(item_id)
        if item is None:
            return None
        for key, value in fields.items():
            if hasattr(item, key):
                setattr(item, key, value)
        item.updated_at = datetime.utcnow()
        await self._fire_hook('update', item)
        return item

    async def delete(self, item_id: str) -> bool:
        """Delete."""
        item = self._items.pop(item_id, None)
        if item:
            await self._fire_hook('delete', item)
            return True
        return False

    async def list_items(self, type_: EmailType | None = None) -> EmailResult:
        """List items."""
        items = list(self._items.values())
        if type_:
            items = [i for i in items if i.type == type_]
        return EmailResult(success=True, items=items, total=len(items))

    def on(self, event: str, handler: Callable) -> None:
        """Register hook."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)

    async def _fire_hook(self, event: str, item: EmailItem) -> None:
        """Fire hook."""
        for handler in self._hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(item)
                else:
                    handler(item)
            except Exception as e:
                logger.error(f'Hook error: {e}')
