"""Data access for the evolved prompt genome population.

Saves are idempotent upserts keyed by ``genome_id`` so replaying an evolution
run folds into the existing rows instead of accumulating duplicates. Reads
return ``PromptGenome`` domain objects: the latest generation for one user, or
the single best genome by composite score.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import func, select

from app.core.prompts.evolution import FitnessWeights, PromptGenome
from app.storage.models_prompt_genome import PromptGenomeRow

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_LIST_LIMIT = 200


def _row_to_genome(row: PromptGenomeRow) -> PromptGenome:
    return PromptGenome(
        id=row.genome_id,
        prompt_text=row.prompt_text,
        model_params=dict(row.model_params or {}),
        scores=dict(row.scores or {}),
        generation=int(row.generation),
        parent_ids=tuple(str(item) for item in row.parent_ids or []),
    )


async def append_population(
    db: AsyncSession,
    *,
    user_id: str,
    genomes: Sequence[PromptGenome],
) -> Sequence[PromptGenomeRow]:
    """Upsert one user's genomes by ``genome_id`` and return the stored rows."""
    genome_ids = [genome.id for genome in genomes]
    existing: dict[str, PromptGenomeRow] = {}
    if genome_ids:
        result = await db.execute(
            select(PromptGenomeRow).where(
                PromptGenomeRow.user_id == user_id,
                PromptGenomeRow.genome_id.in_(genome_ids),
            )
        )
        existing = {row.genome_id: row for row in result.scalars().all()}

    weights = FitnessWeights()
    rows: list[PromptGenomeRow] = []
    seen_ids: set[str] = set()
    for genome in genomes:
        values = {
            "prompt_text": genome.prompt_text,
            "model_params": dict(genome.model_params),
            "scores": dict(genome.scores),
            "generation": int(genome.generation),
            "parent_ids": list(genome.parent_ids),
            "composite_score": weights.composite(genome.scores),
        }
        if genome.id in seen_ids:
            continue
        row = existing.get(genome.id)
        if row is not None:
            for key, value in values.items():
                setattr(row, key, value)
        else:
            row = PromptGenomeRow(id=str(uuid4()), user_id=user_id, genome_id=genome.id, **values)
            db.add(row)
        seen_ids.add(genome.id)
        rows.append(row)
    await db.flush()
    return rows


async def list_population(
    db: AsyncSession,
    user_id: str,
    *,
    limit: int = DEFAULT_LIST_LIMIT,
) -> list[PromptGenome]:
    """Return a user's most recent genome population, best composite first."""
    latest_generation = (
        select(func.max(PromptGenomeRow.generation))
        .where(PromptGenomeRow.user_id == user_id)
        .scalar_subquery()
    )
    stmt = (
        select(PromptGenomeRow)
        .where(PromptGenomeRow.user_id == user_id, PromptGenomeRow.generation == latest_generation)
        .order_by(PromptGenomeRow.composite_score.desc(), PromptGenomeRow.genome_id.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [_row_to_genome(row) for row in result.scalars().all()]


async def get_best_genome(db: AsyncSession, user_id: str) -> PromptGenome | None:
    """Return the user's highest-composite genome, if any."""
    stmt = (
        select(PromptGenomeRow)
        .where(PromptGenomeRow.user_id == user_id)
        .order_by(
            PromptGenomeRow.composite_score.desc(),
            PromptGenomeRow.generation.desc(),
            PromptGenomeRow.genome_id.asc(),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    return None if row is None else _row_to_genome(row)
