"""Owner-scoped editable context backed by the existing documents table."""

from __future__ import annotations

import hashlib
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.storage import async_session
from app.storage.database import Document

RuleKind = Literal["soul", "memory", "project"]
RULE_KINDS = ("soul", "memory", "project")
COLLECTION = "anchored-ui-rules"
CONTEXT_MARKER = "<!-- USER_UI_RULE_CONTEXT -->"


def rule_id(owner_id: str, kind: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"climber:ui-rule:{owner_id}:{kind}"))


async def list_rules(owner_id: str) -> list[dict]:
    async with async_session() as db:
        rows = (
            await db.scalars(
                select(Document).where(
                    Document.user_id == owner_id,
                    Document.collection == COLLECTION,
                )
            )
        ).all()
        by_id = {row.id: row for row in rows}
        return [
            {
                "id": kind,
                "kind": kind,
                "scope": "user",
                "title": kind,
                "content": row.content or "" if row else "",
                "revision": row.content_hash if row else None,
            }
            for kind in RULE_KINDS
            for row in [by_id.get(rule_id(owner_id, kind))]
        ]


async def save_rule(owner_id: str, kind: RuleKind, content: str, revision: str | None) -> dict:
    """Compare-and-set prevents stale editors from overwriting saved context."""
    digest = hashlib.sha256(content.encode()).hexdigest()
    identity = rule_id(owner_id, kind)
    async with async_session() as db:
        values = {"content": content, "content_hash": digest, "size_bytes": len(content.encode())}
        if revision is None:
            db.add(
                Document(
                    id=identity,
                    user_id=owner_id,
                    filename=kind,
                    collection=COLLECTION,
                    content_type="text/plain",
                    status="ready",
                    **values,
                )
            )
            try:
                await db.commit()
            except IntegrityError as exc:
                await db.rollback()
                raise ValueError("Rule changed; reload its current revision") from exc
        else:
            result = await db.execute(
                update(Document)
                .where(
                    Document.id == identity,
                    Document.user_id == owner_id,
                    Document.collection == COLLECTION,
                    Document.content_hash == revision,
                )
                .values(**values)
            )
            if result.rowcount != 1:
                await db.rollback()
                raise ValueError("Rule changed; reload its current revision")
            await db.commit()
    return {
        "id": kind,
        "kind": kind,
        "scope": "user",
        "title": kind,
        "content": content,
        "revision": digest,
        "effective": "next_iteration",
    }


async def refresh_rule_context(session) -> None:
    """Refresh user instructions without changing system policy or permissions."""
    rules = await list_rules(session.user_id)
    session.messages[:] = [
        m
        for m in session.messages
        if not isinstance(m.get("content"), str) or not m["content"].startswith(CONTEXT_MARKER)
    ]
    content = "\n\n".join(f"[{r['kind']}]\n{r['content']}" for r in rules if r["content"])
    if content:
        index = next(
            (
                i
                for i in range(len(session.messages) - 1, -1, -1)
                if session.messages[i].get("role") == "user"
            ),
            len(session.messages),
        )
        session.messages.insert(
            index,
            {
                "role": "user",
                "content": (
                    CONTEXT_MARKER
                    + "\nUser-maintained context (subject to system policy):\n"
                    + content
                ),
            },
        )
