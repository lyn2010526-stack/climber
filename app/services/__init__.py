"""Service layer."""
from __future__ import annotations

from typing import Any


class BaseService:
    """Base service class."""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def get(self, id: str) -> dict[str, Any] | None:
        return None

    async def list(self, **filters: Any) -> list[dict[str, Any]]:
        return []

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        return data

    async def update(self, id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        return None

    async def delete(self, id: str) -> bool:
        return False
