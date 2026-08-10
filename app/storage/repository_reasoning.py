"""Repository for reasoning traces and feedback."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models_reasoning import ReasoningFeedbackDB, ReasoningTraceDB


class ReasoningTraceRepository:
    """CRUD operations for reasoning traces."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, data: dict[str, Any]) -> ReasoningTraceDB:
        trace = ReasoningTraceDB(**data)
        self._session.add(trace)
        await self._session.flush()
        return trace

    async def get_by_trace_id(self, trace_id: str) -> ReasoningTraceDB | None:
        result = await self._session.execute(
            select(ReasoningTraceDB).where(ReasoningTraceDB.trace_id == trace_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[ReasoningTraceDB]:
        result = await self._session.execute(
            select(ReasoningTraceDB)
            .where(ReasoningTraceDB.user_id == user_id)
            .order_by(desc(ReasoningTraceDB.created_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def delete(self, trace_id: str) -> bool:
        result = await self._session.execute(
            delete(ReasoningTraceDB).where(ReasoningTraceDB.trace_id == trace_id)
        )
        return result.rowcount > 0


class ReasoningFeedbackRepository:
    """CRUD operations for reasoning feedback."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, data: dict[str, Any]) -> ReasoningFeedbackDB:
        feedback = ReasoningFeedbackDB(**data)
        self._session.add(feedback)
        await self._session.flush()
        return feedback

    async def list_by_trace_id(self, trace_id: str) -> Sequence[ReasoningFeedbackDB]:
        result = await self._session.execute(
            select(ReasoningFeedbackDB)
            .where(ReasoningFeedbackDB.trace_id == trace_id)
            .order_by(ReasoningFeedbackDB.created_at.desc())
        )
        return result.scalars().all()

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
    ) -> Sequence[ReasoningFeedbackDB]:
        result = await self._session.execute(
            select(ReasoningFeedbackDB)
            .where(ReasoningFeedbackDB.user_id == user_id)
            .order_by(desc(ReasoningFeedbackDB.created_at))
            .limit(limit)
        )
        return result.scalars().all()
