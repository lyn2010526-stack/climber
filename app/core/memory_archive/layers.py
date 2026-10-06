"""L0/L1 directory sidecar generation, persistence and refresh.

A sidecar pair describes one memory directory: L0 (``.abstract.md``) is the
short semantic abstract used for quick filtering and retrieval, L1
(``.overview.md``) is the broader directory overview used for navigation and
deciding whether to load L2 details. Sidecars are persisted to
``memory_sidecars`` and mirrored as hidden files in MemFS when provided.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.memory_archive.index import SemanticIndex, semantic_index
from app.core.memory_archive.retrieval import normalize_scope
from app.core.memory_archive.summarizer import (
    L0_MAX_CHARS,
    L1_MAX_CHARS,
    TextSummarizer,
    _first_sentence,
    clamp,
    extract_abstract_from_overview,
)
from app.storage import async_session
from app.storage.models_memory_archive import MemorySidecar

logger = structlog.get_logger()

SIDECAR_ABSTRACT = ".abstract.md"  # L0
SIDECAR_OVERVIEW = ".overview.md"  # L1

_L1_SAMPLE_LIMIT = 32


@dataclass
class SidecarBundle:
    """Generated L0/L1 pair for one directory scope."""

    scope: str
    abstract: str = ""
    overview: str = ""
    generated_by: str = "rule"
    entry_count: int = 0
    sample_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["abstract_level"] = 0
        payload["overview_level"] = 1
        return payload


class MemorySidecarService:
    """Generate, persist and read L0/L1 sidecars for memory directories."""

    def __init__(
        self,
        *,
        summarizer: TextSummarizer | None = None,
        semantic: SemanticIndex | None = None,
    ) -> None:
        self._summarizer = summarizer or TextSummarizer(use_llm=False)
        self._semantic = semantic or semantic_index

    async def summarize_query(self, body: str, *, scope: str = "") -> tuple[str, str]:
        """Generate (L0, L1) from a directory body."""
        overview = await self._summarizer.overview(body, scope=scope)
        abstract = extract_abstract_from_overview(overview) or (
            await self._summarizer.abstract(body, scope=scope)
        )
        return abstract, overview

    async def persist(
        self,
        user_id: str,
        *,
        scope: str,
        abstract: str,
        overview: str,
        generated_by: str = "rule",
        entry_count: int = 0,
        sample_note: str = "",
        memfs: Any = None,
    ) -> list[MemorySidecar]:
        """Upsert L0/L1 sidecars, register vectors and mirror to MemFS."""
        scope = normalize_scope(scope)
        rows: list[MemorySidecar] = []
        for level, body in (
            (0, clamp(abstract, L0_MAX_CHARS)),
            (1, clamp(overview, L1_MAX_CHARS)),
        ):
            row = await self._upsert(
                user_id,
                scope=scope,
                level=level,
                body=body,
                generated_by=generated_by,
                sample_note=sample_note,
                entry_count=entry_count,
            )
            rows.append(row)
            await self._semantic.index(
                body, scope=scope, level=level, doc_id=str(row.id), user_id=user_id,
                kind="sidecar",
            )
        if memfs is not None:
            await self._write_memfs_sidecars(memfs, scope, abstract, overview)
        logger.info(
            "sidecar_persisted",
            user_id=user_id,
            scope=scope,
            generated_by=generated_by,
            entry_count=entry_count,
        )
        return rows

    async def _upsert(
        self,
        user_id: str,
        *,
        scope: str,
        level: int,
        body: str,
        generated_by: str,
        sample_note: str,
        entry_count: int,
    ) -> MemorySidecar:
        async with async_session() as db:
            stmt = select(MemorySidecar).where(
                MemorySidecar.user_id == user_id,
                MemorySidecar.scope == scope,
                MemorySidecar.level == level,
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if row is None:
                row = MemorySidecar(
                    user_id=user_id,
                    scope=scope,
                    level=level,
                    body=body,
                    generated_by=generated_by,
                    sample_note=sample_note,
                    freshness={"entry_count": entry_count},
                )
                db.add(row)
            else:
                row.body = body
                row.generated_by = generated_by
                row.sample_note = sample_note
                row.freshness = {"entry_count": entry_count}
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                row = (await db.execute(stmt)).scalar_one_or_none()
                if row is None:
                    raise
                row.body = body
                row.generated_by = generated_by
                row.sample_note = sample_note
                row.freshness = {"entry_count": entry_count}
                await db.commit()
            await db.refresh(row)
            return row

    async def read(self, user_id: str, scope: str, level: int) -> MemorySidecar | None:
        scope = normalize_scope(scope)
        async with async_session() as db:
            stmt = select(MemorySidecar).where(
                MemorySidecar.user_id == user_id,
                MemorySidecar.scope == scope,
                MemorySidecar.level == level,
            )
            return (await db.execute(stmt)).scalar_one_or_none()

    async def read_pair(
        self, user_id: str, scope: str,
    ) -> tuple[MemorySidecar | None, MemorySidecar | None]:
        """Read (L0, L1); either may be None when it was never generated."""
        l0 = await self.read(user_id, scope, 0)
        l1 = await self.read(user_id, scope, 1)
        return l0, l1

    async def has_sidecar(self, user_id: str, scope: str, level: int) -> bool:
        return await self.read(user_id, scope, level) is not None

    async def list_scopes(self, user_id: str) -> list[str]:
        async with async_session() as db:
            rows = (await db.execute(
                select(MemorySidecar.scope)
                .where(MemorySidecar.user_id == user_id)
                .distinct()
            )).scalars().all()
        return sorted(rows)

    async def summarize_directory(
        self,
        user_id: str,
        scope: str,
        entries: list[dict[str, Any]] | None = None,
        *,
        memfs: Any = None,
    ) -> SidecarBundle:
        """Generate and persist L0/L1 for a directory given L2 entries."""
        scope = normalize_scope(scope)
        body, total, note = self._directory_body(scope, entries or [])
        abstract, overview = await self.summarize_query(body, scope=scope)
        generated_by = "llm" if self._summarizer.llm_available() else "rule"
        rows = await self.persist(
            user_id,
            scope=scope,
            abstract=abstract,
            overview=overview,
            generated_by=generated_by,
            entry_count=total,
            sample_note=note,
            memfs=memfs,
        )
        return SidecarBundle(
            scope=scope,
            abstract=rows[0].body if rows else abstract,
            overview=rows[1].body if len(rows) > 1 else overview,
            generated_by=generated_by,
            entry_count=total,
            sample_note=note,
        )

    @staticmethod
    def _directory_body(scope: str, entries: list[dict[str, Any]]) -> tuple[str, int, str]:
        """Fold L2 file excerpts into one overview source body (stable sample)."""
        total = len(entries)
        samples = entries if total <= _L1_SAMPLE_LIMIT else entries[:_L1_SAMPLE_LIMIT]
        note = "" if total == len(samples) else f"{len(samples)} of {total} entries sampled"
        excerpts = [MemorySidecarService._entry_excerpt(entry) for entry in samples]
        lines = [f"# {scope or 'root'} directory", *excerpts]
        return "\n".join(lines), total, note

    @staticmethod
    def _entry_excerpt(entry: dict[str, Any]) -> str:
        path = entry.get("path", entry.get("name", "")) or ""
        content = entry.get("content", entry.get("text", "")) or ""
        first = _first_sentence(content)
        return f"- `{path}`: {first}" if first else f"- `{path}`"

    async def _write_memfs_sidecars(
        self, memfs: Any, scope: str, abstract: str, overview: str,
    ) -> None:
        """Mirror sidecars as hidden files inside the MemFS scope directory."""
        for _, body, fname in (
            (0, abstract, SIDECAR_ABSTRACT),
            (1, overview, SIDECAR_OVERVIEW),
        ):
            if not body:
                continue
            await memfs.write(f"{scope}/{fname}", body)


# Global singleton
sidecar_service = MemorySidecarService()
