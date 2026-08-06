"""Core Memory service — Letta-style core memory blocks with XML injection.

- Letta `core_memory` blocks (persona, user_profile, etc.)
- XML injection into system prompt
- LLM self-managed tools: core_memory_append, core_memory_replace
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import structlog
from sqlalchemy import delete, select

from app.storage import async_session
from app.storage.models_memory import CoreMemoryBlock

logger = structlog.get_logger()


class CoreMemoryService:
    """Manage core memory blocks and inject them into system prompts."""

    async def get_blocks(self, user_id: str, agent_id: str | None = None) -> list[CoreMemoryBlock]:
        async with async_session() as db:
            query = select(CoreMemoryBlock).where(CoreMemoryBlock.user_id == user_id)
            if agent_id:
                query = query.where(CoreMemoryBlock.agent_id == agent_id)
            query = query.order_by(CoreMemoryBlock.label)
            result = await db.execute(query)
            return list(result.scalars().all())

    async def get_block(self, user_id: str, label: str, agent_id: str | None = None) -> CoreMemoryBlock | None:
        async with async_session() as db:
            query = select(CoreMemoryBlock).where(
                CoreMemoryBlock.user_id == user_id,
                CoreMemoryBlock.label == label,
            )
            if agent_id:
                query = query.where(CoreMemoryBlock.agent_id == agent_id)
            else:
                query = query.where(CoreMemoryBlock.agent_id.is_(None))
            result = await db.execute(query)
            return result.scalar_one_or_none()

    async def create_or_update_block(
        self,
        user_id: str,
        label: str,
        value: str,
        agent_id: str | None = None,
        limit: int = 4096,
        description: str = "",
        read_only: bool = False,
    ) -> CoreMemoryBlock:
        async with async_session() as db:
            query = select(CoreMemoryBlock).where(
                CoreMemoryBlock.user_id == user_id,
                CoreMemoryBlock.label == label,
            )
            if agent_id:
                query = query.where(CoreMemoryBlock.agent_id == agent_id)
            else:
                query = query.where(CoreMemoryBlock.agent_id.is_(None))
            result = await db.execute(query)
            block = result.scalar_one_or_none()
            if block is None:
                block = CoreMemoryBlock(
                    user_id=user_id,
                    agent_id=agent_id,
                    label=label,
                    value=value[:limit],
                    limit=limit,
                    description=description,
                    read_only=read_only,
                )
                db.add(block)
            else:
                block.value = value[:limit]
                block.limit = limit
                block.description = description
                block.read_only = read_only
            await db.commit()
            await db.refresh(block)
            return block

    async def append_block(
        self,
        user_id: str,
        label: str,
        text: str,
        agent_id: str | None = None,
    ) -> CoreMemoryBlock | None:
        block = await self.get_block(user_id, label, agent_id)
        if block is None:
            return await self.create_or_update_block(user_id, label, text, agent_id=agent_id)
        if block.read_only:
            return block
        new_value = (block.value + "\n" + text).strip()[:block.limit]
        block.value = new_value
        await self._update_block(block)
        return block

    async def replace_in_block(
        self,
        user_id: str,
        label: str,
        old_text: str,
        new_text: str,
        agent_id: str | None = None,
    ) -> CoreMemoryBlock | None:
        block = await self.get_block(user_id, label, agent_id)
        if block is None:
            return None
        if block.read_only:
            return block
        if old_text not in block.value:
            return block
        block.value = block.value.replace(old_text, new_text, 1)[: block.limit]
        await self._update_block(block)
        return block

    async def delete_block(self, user_id: str, label: str, agent_id: str | None = None) -> bool:
        async with async_session() as db:
            query = delete(CoreMemoryBlock).where(
                CoreMemoryBlock.user_id == user_id,
                CoreMemoryBlock.label == label,
            )
            if agent_id:
                query = query.where(CoreMemoryBlock.agent_id == agent_id)
            else:
                query = query.where(CoreMemoryBlock.agent_id.is_(None))
            result = await db.execute(query)
            await db.commit()
            return result.rowcount > 0

    @staticmethod
    async def _update_block(block: CoreMemoryBlock) -> None:
        """Update an existing block using UPDATE instead of merge."""
        from app.storage import async_session
        from app.storage.models_memory import CoreMemoryBlock
        async with async_session() as db:
            await db.execute(
                CoreMemoryBlock.__table__.update()
                .where(CoreMemoryBlock.id == block.id)
                .values(value=block.value)
            )
            await db.commit()

    def format_for_prompt(self, blocks: list[CoreMemoryBlock]) -> str:
        """Format blocks as XML tags for system prompt injection."""
        if not blocks:
            return ""
        root = ET.Element("core_memory")
        for block in blocks:
            el = ET.SubElement(root, "block")
            el.set("label", block.label)
            if block.description:
                el.set("description", block.description)
            if block.read_only:
                el.set("read_only", "true")
            el.text = block.value
        return ET.tostring(root, encoding="unicode")


# Global singleton
core_memory = CoreMemoryService()
