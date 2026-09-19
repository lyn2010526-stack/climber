"""Service layer."""
from __future__ import annotations


class BaseService:
    """Base service class."""
    def __init__(self, *args, **kwargs):
        pass

    async def get(self, id: str) -> dict | None:
        return None

    async def list(self, **filters) -> list[dict]:
        return []

    async def create(self, data: dict) -> dict:
        return data

    async def update(self, id: str, data: dict) -> dict | None:
        return None

    async def delete(self, id: str) -> bool:
        return False
