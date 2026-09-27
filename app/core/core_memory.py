"""Core Memory service — Letta-style core memory blocks with XML injection.

- Letta `core_memory` blocks (persona, user_profile, etc.)
- XML injection into system prompt
- LLM self-managed tools: core_memory_append, core_memory_replace

Design references:
- https://docs.letta.com/v1-sdk/concepts/stateful-agents
- https://langchain-ai.github.io/langmem/concepts/conceptual_guide/
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
        """Return the blocks visible to an agent: its own blocks plus global ones.

        Letta semantics: an agent sees global (user-level) blocks AND its own
        agent-specific overrides. When ``agent_id`` is falsy, only global blocks
        are returned (shared-pool default preserved).
        """
        async with async_session() as db:
            query = select(CoreMemoryBlock).where(CoreMemoryBlock.user_id == user_id)
            if agent_id:
                from sqlalchemy import or_
                query = query.where(
                    or_(
                        CoreMemoryBlock.agent_id == agent_id,
                        CoreMemoryBlock.agent_id.is_(None),
                    )
                )
            else:
                query = query.where(CoreMemoryBlock.agent_id.is_(None))
            query = query.order_by(CoreMemoryBlock.label, CoreMemoryBlock.agent_id)
            result = await db.execute(query)
            blocks = list(result.scalars().all())
            if not agent_id:
                return blocks
            # An agent-scoped block is an override, so hide the same-label
            # global block from the injected context.
            overrides = {block.label for block in blocks if block.agent_id == agent_id}
            return [block for block in blocks if block.agent_id == agent_id or block.label not in overrides]

    async def get_block(self, user_id: str, label: str, agent_id: str | None = None) -> CoreMemoryBlock | None:
        """Resolve a single block: prefer the agent-specific block, else the global.

        Returns the agent's override when it exists; otherwise the user's global
        block with the same label; otherwise ``None``.
        """
        async with async_session() as db:
            base = select(CoreMemoryBlock).where(
                CoreMemoryBlock.user_id == user_id,
                CoreMemoryBlock.label == label,
            )
            if agent_id:
                scoped = await db.execute(base.where(CoreMemoryBlock.agent_id == agent_id))
                block = scoped.scalar_one_or_none()
                if block is not None:
                    return block
                glob = await db.execute(base.where(CoreMemoryBlock.agent_id.is_(None)))
                return glob.scalar_one_or_none()
            result = await db.execute(base.where(CoreMemoryBlock.agent_id.is_(None)))
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
        if not label.strip():
            raise ValueError("Memory block label cannot be empty")
        if limit < 1:
            raise ValueError("Memory block limit must be positive")
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
