"""Repository pattern for database CRUD operations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.database import (
    Agent,
    ApiKey,
    Document,
    Message,
    Session,
    Turn,
    UsageLog,
)
from app.storage.models_plugins import MCPServerRecord, PluginRecord


class AgentRepository:
    """CRUD operations for agents."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        user_id: str,
        name: str,
        provider: str,
        model_id: str,
        api_key_encrypted: str,
        description: str = "",
        system_prompt: str = "",
        base_url: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tool_ids: list[str] | None = None,
        skill_ids: list[str] | None = None,
        memory_config: dict[str, Any] | None = None,
    ) -> Agent:
        agent = Agent(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            provider=provider,
            model_id=model_id,
            api_key_encrypted=api_key_encrypted,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            tool_ids=tool_ids or [],
            skill_ids=skill_ids or [],
            memory_config=memory_config or {},
        )
        self._session.add(agent)
        await self._session.flush()
        return agent

    async def get_by_id(self, agent_id: str) -> Agent | None:
        result = await self._session.execute(select(Agent).where(Agent.id == agent_id))
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> Sequence[Agent]:
        result = await self._session.execute(
            select(Agent).where(Agent.user_id == user_id).where(Agent.is_active == True)
        )
        return result.scalars().all()

    async def update(self, agent_id: str, **kwargs: Any) -> Agent | None:
        await self._session.execute(
            update(Agent).where(Agent.id == agent_id).values(**kwargs)
        )
        return await self.get_by_id(agent_id)

    async def delete(self, agent_id: str) -> bool:
        result = await self._session.execute(delete(Agent).where(Agent.id == agent_id))
        return result.rowcount > 0


class SessionRepository:
    """CRUD operations for sessions."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        agent_id: str,
        user_id: str,
        title: str | None = None,
        status: str = "pending",
    ) -> Session:
        db_session = Session(
            id=str(uuid4()),
            agent_id=agent_id,
            user_id=user_id,
            title=title or "New Chat",
            status=status,
        )
        self._session.add(db_session)
        await self._session.flush()
        return db_session

    async def get_by_id(self, session_id: str) -> Session | None:
        result = await self._session.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> Sequence[Session]:
        result = await self._session.execute(
            select(Session).where(Session.user_id == user_id).order_by(Session.created_at.desc())
        )
        return result.scalars().all()

    async def update(self, session_id: str, **kwargs: Any) -> Session | None:
        await self._session.execute(
            update(Session).where(Session.id == session_id).values(**kwargs)
        )
        return await self.get_by_id(session_id)

    async def delete(self, session_id: str) -> bool:
        result = await self._session.execute(delete(Session).where(Session.id == session_id))
        return result.rowcount > 0


class TurnRepository:
    """CRUD operations for turns."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    async def _get_session(self):
        if self._session_factory is not None:
            return self._session_factory()
        from app.storage import async_session
        return async_session()

    async def create(
        self,
        session_id: str,
        status: str = "running",
        checkpoint_id: str | None = None,
        metadata_: dict[str, Any] | None = None,
    ) -> Turn:
        async with await self._get_session() as db:
            turn = Turn(
                id=str(uuid4()),
                session_id=session_id,
                status=status,
                checkpoint_id=checkpoint_id,
                started_at=datetime.utcnow() if status == "running" else None,
                metadata_=metadata_ or {},
            )
            db.add(turn)
            await db.flush()
            return turn

    async def get_by_id(self, turn_id: str) -> Turn | None:
        async with await self._get_session() as db:
            result = await db.execute(select(Turn).where(Turn.id == turn_id))
            return result.scalar_one_or_none()

    async def list_by_session(self, session_id: str) -> Sequence[Turn]:
        async with await self._get_session() as db:
            result = await db.execute(
                select(Turn).where(Turn.session_id == session_id).order_by(Turn.created_at.asc())
            )
            return result.scalars().all()

    async def update(self, turn_id: str, **kwargs: Any) -> Turn | None:
        async with await self._get_session() as db:
            await db.execute(
                update(Turn).where(Turn.id == turn_id).values(**kwargs)
            )
            await db.flush()
            await db.commit()
            result = await db.execute(select(Turn).where(Turn.id == turn_id))
            return result.scalar_one_or_none()

    async def complete(self, turn_id: str, result: str | None = None, error: str | None = None) -> Turn | None:
        now = datetime.utcnow()
        values: dict[str, Any] = {"completed_at": now}
        if result is not None:
            values["result"] = result
        if error is not None:
            values["error"] = error
            values["error_message"] = error
        status = "failed" if error else "completed"
        values["status"] = status
        return await self.update(turn_id, **values)

    async def start_turn(
        self,
        session_id: str,
        checkpoint_id: str | None = None,
        metadata_: dict[str, Any] | None = None,
    ) -> Turn:
        """Create a new turn in running state."""
        async with await self._get_session() as db:
            turn = Turn(
                id=str(uuid4()),
                session_id=session_id,
                status="running",
                checkpoint_id=checkpoint_id,
                started_at=datetime.utcnow(),
                metadata_=metadata_ or {},
            )
            db.add(turn)
            await db.flush()
            await db.commit()
            return turn

    async def complete_turn(
        self,
        turn_id: str,
        result: str | None = None,
        iteration_count: int = 0,
        tokens_used: int = 0,
    ) -> Turn | None:
        """Mark a turn as completed with metrics."""
        now = datetime.utcnow()
        values: dict[str, Any] = {
            "completed_at": now,
            "status": "completed",
            "iteration_count": iteration_count,
            "tokens_used": tokens_used,
        }
        if result is not None:
            values["result"] = result
        return await self.update(turn_id, **values)

    async def fail_turn(
        self,
        turn_id: str,
        error_message: str,
        iteration_count: int = 0,
        tokens_used: int = 0,
    ) -> Turn | None:
        """Mark a turn as failed with error details."""
        now = datetime.utcnow()
        values: dict[str, Any] = {
            "completed_at": now,
            "status": "failed",
            "error": error_message,
            "error_message": error_message,
            "iteration_count": iteration_count,
            "tokens_used": tokens_used,
        }
        return await self.update(turn_id, **values)

    async def delete(self, turn_id: str) -> bool:
        async with await self._get_session() as db:
            result = await db.execute(delete(Turn).where(Turn.id == turn_id))
            return result.rowcount > 0


class MessageRepository:
    """CRUD operations for messages."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        session_id: str,
        role: str,
        content: str | None = None,
        tool_call_id: str | None = None,
        tool_calls: list[dict] | None = None,
        tool_name: str | None = None,
        tokens: int = 0,
        metadata_: dict[str, Any] | None = None,
    ) -> Message:
        msg = Message(
            id=str(uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            tool_calls=tool_calls or [],
            tool_name=tool_name,
            tokens=tokens,
            metadata_=metadata_ or {},
        )
        self._session.add(msg)
        await self._session.flush()
        return msg

    async def list_by_session(self, session_id: str) -> Sequence[Message]:
        result = await self._session.execute(
            select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
        )
        return result.scalars().all()

    async def delete_by_session(self, session_id: str) -> int:
        result = await self._session.execute(delete(Message).where(Message.session_id == session_id))
        return result.rowcount


class ApiKeyRepository:
    """CRUD operations for user API keys."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        user_id: str,
        provider: str,
        name: str,
        api_key_encrypted: str,
        base_url: str | None = None,
    ) -> ApiKey:
        key = ApiKey(
            id=str(uuid4()),
            user_id=user_id,
            provider=provider,
            name=name,
            api_key_encrypted=api_key_encrypted,
            base_url=base_url,
        )
        self._session.add(key)
        await self._session.flush()
        return key

    async def get_by_id(self, key_id: str) -> ApiKey | None:
        result = await self._session.execute(select(ApiKey).where(ApiKey.id == key_id))
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> Sequence[ApiKey]:
        result = await self._session.execute(
            select(ApiKey).where(ApiKey.user_id == user_id).where(ApiKey.is_active == True)
        )
        return result.scalars().all()

    async def delete(self, key_id: str) -> bool:
        result = await self._session.execute(delete(ApiKey).where(ApiKey.id == key_id))
        return result.rowcount > 0


class DocumentRepository:
    """CRUD operations for documents."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        user_id: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        collection: str,
    ) -> Document:
        doc = Document(
            id=str(uuid4()),
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            collection=collection,
        )
        self._session.add(doc)
        await self._session.flush()
        return doc

    async def get_by_id(self, doc_id: str) -> Document | None:
        result = await self._session.execute(select(Document).where(Document.id == doc_id))
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> Sequence[Document]:
        result = await self._session.execute(
            select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
        )
        return result.scalars().all()

    async def update(self, doc_id: str, **kwargs: Any) -> Document | None:
        await self._session.execute(
            update(Document).where(Document.id == doc_id).values(**kwargs)
        )
        return await self.get_by_id(doc_id)

    async def delete(self, doc_id: str) -> bool:
        result = await self._session.execute(delete(Document).where(Document.id == doc_id))
        return result.rowcount > 0


class UsageLogRepository:
    """CRUD operations for usage logs."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        user_id: str,
        provider: str,
        model_id: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        session_id: str | None = None,
    ) -> UsageLog:
        log = UsageLog(
            id=str(uuid4()),
            user_id=user_id,
            session_id=session_id,
            provider=provider,
            model_id=model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
        self._session.add(log)
        await self._session.flush()
        return log

    async def list_by_user(
        self, user_id: str, limit: int = 100
    ) -> Sequence[UsageLog]:
        result = await self._session.execute(
            select(UsageLog)
            .where(UsageLog.user_id == user_id)
            .order_by(UsageLog.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_user_totals(self, user_id: str) -> dict[str, int]:
        """Get aggregated usage for a user."""
        from sqlalchemy import func
        result = await self._session.execute(
            select(
                func.coalesce(func.sum(UsageLog.prompt_tokens), 0),
                func.coalesce(func.sum(UsageLog.completion_tokens), 0),
                func.coalesce(func.sum(UsageLog.total_tokens), 0),
            ).where(UsageLog.user_id == user_id)
        )
        row = result.one()
        return {
            "prompt_tokens": row[0],
            "completion_tokens": row[1],
            "total_tokens": row[2],
        }


class PluginRepository:
    """CRUD operations for plugins."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, **kwargs) -> PluginRecord:
        plugin = PluginRecord(**kwargs)
        self._session.add(plugin)
        await self._session.flush()
        return plugin

    async def get_by_id(self, plugin_id: str) -> PluginRecord | None:
        result = await self._session.execute(select(PluginRecord).where(PluginRecord.id == plugin_id))
        return result.scalar_one_or_none()

    async def get_by_name_type(self, name: str, type: str) -> PluginRecord | None:
        result = await self._session.execute(
            select(PluginRecord).where(PluginRecord.name == name, PluginRecord.type == type)
        )
        return result.scalar_one_or_none()

    async def list_by_type(self, type: str) -> Sequence[PluginRecord]:
        result = await self._session.execute(
            select(PluginRecord).where(PluginRecord.type == type).order_by(PluginRecord.name)
        )
        return result.scalars().all()

    async def list_enabled(self) -> Sequence[PluginRecord]:
        result = await self._session.execute(
            select(PluginRecord).where(PluginRecord.status == "enabled")
        )
        return result.scalars().all()

    async def list_all(self) -> Sequence[PluginRecord]:
        result = await self._session.execute(select(PluginRecord).order_by(PluginRecord.name))
        return result.scalars().all()

    async def update_status(self, plugin_id: str, status: str, error_message: str | None = None) -> None:
        values = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message
        await self._session.execute(
            update(PluginRecord).where(PluginRecord.id == plugin_id).values(**values)
        )

    async def delete(self, plugin_id: str) -> bool:
        result = await self._session.execute(
            delete(PluginRecord).where(PluginRecord.id == plugin_id)
        )
        return result.rowcount > 0


class MCPServerRepository:
    """CRUD operations for MCP server records."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, **kwargs) -> MCPServerRecord:
        record = MCPServerRecord(**kwargs)
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_by_id(self, server_id: str) -> MCPServerRecord | None:
        result = await self._session.execute(select(MCPServerRecord).where(MCPServerRecord.id == server_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[MCPServerRecord]:
        result = await self._session.execute(select(MCPServerRecord))
        return result.scalars().all()

    async def update_status(self, server_id: str, status: str, tools_count: int | None = None) -> None:
        values = {"status": status}
        if tools_count is not None:
            values["tools_count"] = tools_count
        await self._session.execute(
            update(MCPServerRecord).where(MCPServerRecord.id == server_id).values(**values)
        )

    async def delete(self, server_id: str) -> bool:
        result = await self._session.execute(
            delete(MCPServerRecord).where(MCPServerRecord.id == server_id)
        )
        return result.rowcount > 0
