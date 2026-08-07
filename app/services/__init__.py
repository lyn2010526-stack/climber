"""Service layer."""
from __future__ import annotations
from typing import Any, Optional


class BaseService:
    """Base service class."""
    def __init__(self, *args, **kwargs):
        pass

    async def get(self, id: str) -> Optional[dict]:
        return None

    async def list(self, **filters) -> list[dict]:
        return []

    async def create(self, data: dict) -> dict:
        return data

    async def update(self, id: str, data: dict) -> Optional[dict]:
        return None

    async def delete(self, id: str) -> bool:
        return False
