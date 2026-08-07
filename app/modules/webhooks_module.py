"""Module: webhooks."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class WebhooksType(Enum):
    """Type enum."""
    TYPE_A = 'type_a'
    TYPE_B = 'type_b'
    TYPE_C = 'type_c'


@dataclass
class WebhooksConfig:
    """Config."""
    name: str = 'webhooks'
    enabled: bool = True
    max_items: int = 1000
    timeout: float = 30.0
    retry_count: int = 3


@dataclass
class WebhooksItem:
    """Item."""
    id: str = ''
    name: str = ''
    type: WebhooksType = WebhooksType.TYPE_A
    data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WebhooksResult:
    """Result."""
    success: bool = False
    items: list[WebhooksItem] = field(default_factory=list)
    total: int = 0
    error: str | None = None


class WebhooksManager:
    """Manager."""

    def __init__(self, config: WebhooksConfig | None = None):
        self.config = config or WebhooksConfig()
        self._items: dict[str, WebhooksItem] = {}
        self._hooks: dict[str, list[Callable]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize."""
        self._initialized = True
        logger.info(f'{self.config.name} manager initialized')

    async def create(self, name: str, type_: WebhooksType, data: dict | None = None) -> WebhooksItem:
        """Create."""
        import uuid
        item = WebhooksItem(
            id=str(uuid.uuid4()),
            name=name,
            type=type_,
            data=data or {},
        )
        self._items[item.id] = item
        await self._fire_hook('create', item)
        return item

    async def get(self, item_id: str) -> WebhooksItem | None:
        """Get."""
        return self._items.get(item_id)

    async def update(self, item_id: str, **fields) -> WebhooksItem | None:
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

    async def list_items(self, type_: WebhooksType | None = None) -> WebhooksResult:
        """List items."""
        items = list(self._items.values())
        if type_:
            items = [i for i in items if i.type == type_]
        return WebhooksResult(success=True, items=items, total=len(items))

    def on(self, event: str, handler: Callable) -> None:
        """Register hook."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)

    async def _fire_hook(self, event: str, item: WebhooksItem) -> None:
        """Fire hook."""
        for handler in self._hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(item)
                else:
                    handler(item)
            except Exception as e:
                logger.error(f'Hook error: {e}')
