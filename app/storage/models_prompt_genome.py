"""Durable storage for the genetic prompt-evolution population.

Each ``prompt_genomes`` row is one ``PromptGenome`` candidate owned by a user.
The repository folds repeated saves of the same ``genome_id`` into a single
row (upsert by ``genome_id``) so replaying an evolution run stays idempotent,
and reads return the latest generation of every genome for fast reload.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base


class PromptGenomeRow(Base):
    """One evolved prompt/parameter candidate in a user's population."""

    __tablename__ = "prompt_genomes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    genome_id: Mapped[str] = mapped_column(String(256), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_params: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    scores: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    generation: Mapped[int] = mapped_column(nullable=False, default=0)
    parent_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "genome_id", name="uq_prompt_genomes_user_genome"),
    )
