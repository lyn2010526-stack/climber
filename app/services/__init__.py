"""Service layer."""
from __future__ import annotations


class BaseService:
    """Base service class."""
    def __init__(self, *args, **kwargs):
        pass

    async def get(self, entity_id: str) -> dict | None:  # noqa: ARG002  # BaseService interface
        return None

    async def list(self, **filters) -> list[dict]:  # noqa: ARG002  # BaseService interface
        return []

    async def create(self, data: dict) -> dict:
        return data

    async def update(self, entity_id: str, data: dict) -> dict | None:  # noqa: ARG002  # BaseService interface
        return None

    async def delete(self, entity_id: str) -> bool:  # noqa: ARG002  # BaseService interface
        return False
