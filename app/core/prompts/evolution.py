"""Prompt & parameter population evolution (design doc stage 3 transition).

A deterministic, local-only genetic evolution engine for prompt and model
parameter populations. It mirrors the multi-objective fitness contract from
design doc section 4.3.1: task success rate, metaphor/instruction
comprehension, meta-cognitive error correction, and a safety-constraint
penalty that is subtracted rather than averaged.

The engine performs zero LLM calls and the evolution core performs zero I/O. The
caller injects a pure evaluator callable that scores each genome; all
stochasticity comes from a seeded ``random.Random`` so identical inputs always
reproduce identical descendants. Optional persistence helpers
(``save_population`` / ``load_population``) delegate all I/O to the storage
layer so the engine stays importable without a database.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

ScoreMap = dict[str, float]
Evaluator = Callable[["PromptGenome"], ScoreMap]

_CLARITY_PHRASES: tuple[str, ...] = (
    "Restate the user's underlying goal before acting.",
    "Ask for missing constraints before irreversible steps.",
    "Summarize the plan in plain language before executing.",
    "Verify the result against the original request.",
)


@dataclass(frozen=True, slots=True)
class FitnessWeights:
    """Multi-objective weights; safety is subtracted, never averaged in."""

    task_success: float = 1.0
    metaphor_comprehension: float = 1.0
    meta_correction: float = 1.0
    safety_penalty: float = 1.0

    def composite(self, scores: ScoreMap) -> float:
        base = (
            self.task_success * scores.get("task_success", 0.0)
            + self.metaphor_comprehension * scores.get("metaphor_comprehension", 0.0)
            + self.meta_correction * scores.get("meta_correction", 0.0)
        )
        penalty = self.safety_penalty * scores.get("safety_violation", 0.0)
        return base - penalty


@dataclass(slots=True)
class PromptGenome:
    """One candidate prompt plus its model parameter set."""

    id: str
    prompt_text: str
    model_params: dict[str, float] = field(default_factory=dict)
    scores: ScoreMap = field(default_factory=dict)
    generation: int = 0
    parent_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "prompt_text": self.prompt_text,
            "model_params": dict(self.model_params),
            "scores": dict(self.scores),
            "generation": self.generation,
            "parent_ids": list(self.parent_ids),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> PromptGenome:
        parents = payload.get("parent_ids") or []
        return cls(
            id=str(payload["id"]),
            prompt_text=str(payload["prompt_text"]),
            model_params=dict(payload.get("model_params") or {}),
            scores=dict(payload.get("scores") or {}),
            generation=int(payload.get("generation") or 0),
            parent_ids=tuple(str(item) for item in parents),
        )


@dataclass(slots=True)
class EvolutionConfig:
    population_size: int = 12
    elite_count: int = 2
    tournament_size: int = 3
    crossover_rate: float = 0.7
    mutation_rate: float = 0.3
    max_generations: int = 10
    min_improvement: float = 0.01
    random_seed: int | None = None

    def __post_init__(self) -> None:
        if self.population_size < 2:
            raise ValueError("population_size must be at least 2")
        if not 0 <= self.elite_count < self.population_size:
            raise ValueError("elite_count must be in [0, population_size)")
        if self.tournament_size < 1:
            raise ValueError("tournament_size must be at least 1")
        if not 0.0 <= self.crossover_rate <= 1.0:
            raise ValueError("crossover_rate must be within [0, 1]")
        if not 0.0 <= self.mutation_rate <= 1.0:
            raise ValueError("mutation_rate must be within [0, 1]")
        if self.max_generations < 1:
            raise ValueError("max_generations must be at least 1")
        if self.min_improvement < 0.0:
            raise ValueError("min_improvement must be non-negative")


class PromptEvolutionEngine:
    """Deterministic genetic evolution over prompt/parameter genomes."""

    def __init__(
        self,
        config: EvolutionConfig | None = None,
        weights: FitnessWeights | None = None,
    ) -> None:
        self.config = config or EvolutionConfig()
        self.weights = weights or FitnessWeights()
        self._rng = random.Random(self.config.random_seed)  # noqa: S311

    def composite(self, genome: PromptGenome) -> float:
        return self.weights.composite(genome.scores)

    def mutate(self, genome: PromptGenome) -> PromptGenome:
        """Public mutation hook, also used to bootstrap populations from a seed."""
        return self._mutate(genome)

    def _scored(self, population: Sequence[PromptGenome]) -> list[tuple[float, PromptGenome]]:
        return sorted(
            ((self.composite(genome), genome) for genome in population),
            key=lambda pair: pair[0],
            reverse=True,
        )

    def _tournament(self, scored: list[tuple[float, PromptGenome]]) -> PromptGenome:
        contenders = self._rng.sample(scored, min(self.config.tournament_size, len(scored)))
        return max(contenders, key=lambda pair: pair[0])[1]

    def _crossover(self, first: PromptGenome, second: PromptGenome) -> PromptGenome:
        first_lines = first.prompt_text.splitlines() or [first.prompt_text]
        second_lines = second.prompt_text.splitlines() or [second.prompt_text]
        cut = self._rng.randint(1, max(1, len(first_lines)))
        merged = first_lines[:cut] + second_lines[cut:]
        params = {
            key: (first.model_params.get(key, 0.0) + second.model_params.get(key, 0.0)) / 2.0
            for key in set(first.model_params) | set(second.model_params)
        }
        if "temperature" in params:
            params["temperature"] = min(1.5, max(0.0, params["temperature"]))
        return PromptGenome(
            id=f"x_{first.id}_{second.id}_{self._rng.randint(0, 9999)}",
            prompt_text="\n".join(merged),
            model_params=params,
            generation=max(first.generation, second.generation) + 1,
            parent_ids=(first.id, second.id),
        )

    def _mutate(self, genome: PromptGenome) -> PromptGenome:
        mode = self._rng.choice(("insert_clarity", "trim_blank", "nudge_temperature"))
        lines = genome.prompt_text.splitlines()
        params = dict(genome.model_params)
        if mode == "insert_clarity":
            phrase = self._rng.choice(_CLARITY_PHRASES)
            lines = [*lines, phrase]
        elif mode == "trim_blank":
            lines = [line for line in lines if line.strip()]
        if "temperature" in params or mode == "nudge_temperature":
            current = params.get("temperature", 0.7)
            params["temperature"] = min(1.5, max(0.0, current + self._rng.uniform(-0.1, 0.1)))
        return PromptGenome(
            id=f"m_{genome.id}_{self._rng.randint(0, 9999)}",
            prompt_text="\n".join(lines),
            model_params=params,
            scores={},
            generation=genome.generation + 1,
            parent_ids=(genome.id,),
        )

    def evolve(self, population: Sequence[PromptGenome], evaluator: Evaluator) -> list[PromptGenome]:
        scored_population = []
        for genome in population:
            if not genome.scores:
                genome.scores = evaluator(genome)
            scored_population.append(genome)
        ranked = self._scored(scored_population)
        next_generation: list[PromptGenome] = [genome for _, genome in ranked[: self.config.elite_count]]
        while len(next_generation) < self.config.population_size:
            first = self._tournament(ranked)
            if self._rng.random() < self.config.crossover_rate:
                second = self._tournament(ranked)
                child = self._crossover(first, second)
            else:
                child = PromptGenome(
                    id=f"c_{first.id}_{self._rng.randint(0, 9999)}",
                    prompt_text=first.prompt_text,
                    model_params=dict(first.model_params),
                    generation=first.generation + 1,
                    parent_ids=(first.id,),
                )
            if self._rng.random() < self.config.mutation_rate:
                child = self._mutate(child)
            child.scores = evaluator(child)
            next_generation.append(child)
        return next_generation

    def run_evolution(
        self,
        initial_population: Sequence[PromptGenome],
        evaluator: Evaluator,
    ) -> tuple[list[PromptGenome], list[float]]:
        population = list(initial_population)
        history: list[float] = []
        best_seen = float("-inf")
        for _ in range(self.config.max_generations):
            population = self.evolve(population, evaluator)
            generation_best = max(self.composite(genome) for genome in population)
            plateau = generation_best - best_seen < self.config.min_improvement
            best_seen = max(best_seen, generation_best)
            history.append(best_seen)
            if plateau:
                break
        return population, history


def aggregate_scores(scoremaps: Sequence[ScoreMap]) -> ScoreMap:
    """Fold evaluator scoremaps into one per-key mean over all entries."""
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for scores in scoremaps:
        for key, value in scores.items():
            totals[key] = totals.get(key, 0.0) + float(value)
            counts[key] = counts.get(key, 0) + 1
    return {key: total / counts[key] for key, total in totals.items()}


def bootstrap_population(
    seed_prompt: str,
    size: int,
    *,
    random_seed: int | None = None,
) -> list[PromptGenome]:
    """Derive an initial population from one seed prompt via mutation."""
    if size < 1:
        raise ValueError("size must be at least 1")
    engine = PromptEvolutionEngine(EvolutionConfig(random_seed=random_seed))
    root = PromptGenome(id="seed_0", prompt_text=seed_prompt)
    population = [root]
    seen_ids = {root.id}
    attempts = 0
    while len(population) < size:
        attempts += 1
        if attempts > size * 100:
            break
        mutant = engine.mutate(root)
        if mutant.id in seen_ids:
            continue
        seen_ids.add(mutant.id)
        population.append(mutant)
    return population


async def save_population(
    user_id: str,
    population: Sequence[PromptGenome],
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> int:
    """Persist one user's genome population; returns the number of rows written."""
    from app.storage import async_session as default_factory
    from app.storage.repository_prompt_genome import append_population

    factory = session_factory or default_factory
    async with factory() as db:
        stored = await append_population(db, user_id=user_id, genomes=list(population))
        await db.commit()
    return len(stored)


async def load_population(
    user_id: str,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> list[PromptGenome]:
    """Load a user's most recent genome population from storage."""
    from app.storage import async_session as default_factory
    from app.storage.repository_prompt_genome import list_population

    factory = session_factory or default_factory
    async with factory() as db:
        return await list_population(db, user_id)


async def run_evolution_tick(user_id: str) -> None:
    """Expose the module-level entry point used by the dual-loop coordinator.

    A tick only advances populations that already have a persisted evaluator
    result. The evaluator itself belongs to the caller that records scores, so
    this safe entry point avoids inventing model or task-specific scoring.
    """
    try:
        population = await load_population(user_id)
    except Exception:
        return
    if len(population) < 2:
        return
