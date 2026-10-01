import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.core.prompts.evolution as evolution_module
from app.core.prompts.evolution import (
    EvolutionConfig,
    FitnessWeights,
    PromptEvolutionEngine,
    PromptGenome,
    aggregate_scores,
    bootstrap_population,
    load_population,
    save_population,
)
from app.storage import Base
from app.storage.models_prompt_genome import PromptGenomeRow
from app.storage.repository_prompt_genome import get_best_genome


def make_genome(text: str, temperature: float = 0.7) -> PromptGenome:
    return PromptGenome(id=f"g_{text[:12]}", prompt_text=text, model_params={"temperature": temperature})


def clarity_evaluator(genome: PromptGenome) -> dict[str, float]:
    has_clarity = "goal" in genome.prompt_text or "Verify" in genome.prompt_text
    return {
        "task_success": 1.0 if has_clarity else 0.3,
        "metaphor_comprehension": 1.0 if has_clarity else 0.2,
        "meta_correction": 0.5,
        "safety_violation": 0.0,
    }


async def make_initialized_sessions() -> async_sessionmaker:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return factory


def test_same_seed_is_deterministic() -> None:
    config = EvolutionConfig(random_seed=42, max_generations=3)
    population = [make_genome("plain prompt one"), make_genome("plain prompt two")]
    population_b = [make_genome("plain prompt one"), make_genome("plain prompt two")]
    engine_a = PromptEvolutionEngine(config)
    engine_b = PromptEvolutionEngine(config)
    result_a, history_a = engine_a.run_evolution(population, clarity_evaluator)
    result_b, history_b = engine_b.run_evolution(population_b, clarity_evaluator)
    assert history_a == history_b
    assert [genome.prompt_text for genome in result_a] == [genome.prompt_text for genome in result_b]


def test_elite_genomes_survive_unchanged() -> None:
    config = EvolutionConfig(population_size=4, elite_count=1, crossover_rate=0.0, mutation_rate=0.0, random_seed=7)
    best = make_genome("Restate the user's underlying goal before acting.")
    weak = make_genome("do stuff")
    engine = PromptEvolutionEngine(config)
    next_generation = engine.evolve([best, weak, weak, weak], clarity_evaluator)
    assert best.prompt_text in [genome.prompt_text for genome in next_generation]
    assert best.scores == clarity_evaluator(best)


def test_elite_slot_keeps_highest_fitness_genome() -> None:
    config = EvolutionConfig(population_size=3, elite_count=1, crossover_rate=0.0, mutation_rate=0.0, random_seed=9)
    best = make_genome("Verify the goal before acting")
    mid = make_genome("plain prompt alpha")
    weak = make_genome("do stuff")
    engine = PromptEvolutionEngine(config)
    next_generation = engine.evolve([weak, mid, best], clarity_evaluator)
    assert next_generation[0].id == best.id
    assert next_generation[0].scores == clarity_evaluator(best)


def test_scored_ranks_descending_by_composite() -> None:
    engine = PromptEvolutionEngine(EvolutionConfig(random_seed=1))
    ranked = engine._scored([make_genome("do stuff"), make_genome("Verify the goal"), make_genome("plain prompt")])
    scores = [score for score, _ in ranked]
    assert scores == sorted(scores, reverse=True)


def test_safety_penalty_lowers_composite() -> None:
    weights = FitnessWeights()
    clean = {"task_success": 1.0, "metaphor_comprehension": 1.0, "meta_correction": 1.0, "safety_violation": 0.0}
    unsafe = dict(clean, safety_violation=0.5)
    assert weights.composite(unsafe) < weights.composite(clean)


def test_population_best_improves_across_generations() -> None:
    config = EvolutionConfig(
        population_size=8, elite_count=2, max_generations=6, min_improvement=0.0, random_seed=3
    )
    population = [
        make_genome("plain prompt"),
        make_genome("another plain prompt"),
        make_genome("third plain prompt"),
    ]
    engine = PromptEvolutionEngine(config)
    _population, history = engine.run_evolution(population, clarity_evaluator)
    assert len(history) == config.max_generations
    assert history[-1] > history[0]
    assert history == sorted(history)


def test_offspring_are_valid_genomes() -> None:
    config = EvolutionConfig(population_size=6, elite_count=1, max_generations=2, random_seed=11)
    population = [
        make_genome("line one\nline two\ntemperature hint"),
        make_genome("other line"),
    ]
    engine = PromptEvolutionEngine(config)
    final_population, _history = engine.run_evolution(population, clarity_evaluator)
    assert len(final_population) == config.population_size
    for genome in final_population:
        temperature = genome.model_params.get("temperature")
        assert temperature is not None
        assert 0.0 <= temperature <= 1.5
        assert genome.id
        assert genome.prompt_text


def test_serialization_round_trip() -> None:
    genome = PromptGenome(
        id="g1",
        prompt_text="line\nVerify the result.",
        model_params={"temperature": 0.4},
        scores={"task_success": 0.9},
        generation=2,
        parent_ids=("p1", "p2"),
    )
    assert PromptGenome.from_dict(genome.to_dict()) == genome


def test_module_tick_entry_is_discoverable() -> None:
    assert callable(evolution_module.run_evolution_tick)


def test_model_annotations_are_parameterized() -> None:
    annotations = PromptGenomeRow.__annotations__
    assert annotations["model_params"] == "Mapped[dict[str, float]]"
    assert annotations["scores"] == "Mapped[dict[str, float]]"
    assert annotations["parent_ids"] == "Mapped[list[str]]"


def test_invalid_config_raises() -> None:
    with pytest.raises(ValueError, match="population_size"):
        EvolutionConfig(population_size=1)
    with pytest.raises(ValueError, match="elite_count"):
        EvolutionConfig(population_size=4, elite_count=4)
    with pytest.raises(ValueError, match="crossover_rate"):
        EvolutionConfig(crossover_rate=1.5)
    with pytest.raises(ValueError, match="mutation_rate"):
        EvolutionConfig(mutation_rate=-0.1)
    with pytest.raises(ValueError, match="max_generations"):
        EvolutionConfig(max_generations=0)
    with pytest.raises(ValueError, match="min_improvement"):
        EvolutionConfig(min_improvement=-0.5)


def test_min_improvement_stops_on_plateau() -> None:
    config = EvolutionConfig(
        population_size=4, elite_count=1, max_generations=10, min_improvement=0.5, random_seed=5
    )
    population = [make_genome("plain prompt"), make_genome("another plain prompt")]
    engine = PromptEvolutionEngine(config)
    _population, history = engine.run_evolution(population, clarity_evaluator)
    assert 1 <= len(history) < config.max_generations
    assert history == sorted(history)


def test_min_improvement_zero_disables_early_stop() -> None:
    config = EvolutionConfig(
        population_size=4, elite_count=1, max_generations=4, min_improvement=0.0, random_seed=5
    )
    population = [make_genome("plain prompt"), make_genome("another plain prompt")]
    engine = PromptEvolutionEngine(config)
    _population, history = engine.run_evolution(population, clarity_evaluator)
    assert len(history) == config.max_generations


def test_aggregate_scores_averages_per_key() -> None:
    aggregated = aggregate_scores(
        [
            {"task_success": 1.0, "meta_correction": 0.5},
            {"task_success": 0.0},
            {"task_success": 0.5, "meta_correction": 1.5, "safety_violation": 1.0},
        ]
    )
    assert aggregated == pytest.approx(
        {"task_success": 0.5, "meta_correction": 1.0, "safety_violation": 1.0}
    )


def test_aggregate_scores_empty_input() -> None:
    assert aggregate_scores([]) == {}


def test_bootstrap_population_shapes_seed_variants() -> None:
    seed_prompt = "Restate the user's underlying goal before acting."
    population = bootstrap_population(seed_prompt, 5, random_seed=9)
    assert len(population) == 5
    root = population[0]
    assert root.id == "seed_0"
    assert root.prompt_text == seed_prompt
    assert root.generation == 0
    assert root.parent_ids == ()
    for mutant in population[1:]:
        assert mutant.generation == 1
        assert mutant.parent_ids == ("seed_0",)
        assert mutant.prompt_text
        temperature = mutant.model_params.get("temperature")
        if temperature is not None:
            assert 0.0 <= temperature <= 1.5


def test_bootstrap_population_is_deterministic() -> None:
    def snapshot(population: list[PromptGenome]) -> list[tuple[object, ...]]:
        return [
            (genome.id, genome.prompt_text, dict(genome.model_params), genome.parent_ids)
            for genome in population
        ]

    first = snapshot(bootstrap_population("Do the task.", 4, random_seed=21))
    second = snapshot(bootstrap_population("Do the task.", 4, random_seed=21))
    assert first == second


def test_bootstrap_population_validates_size() -> None:
    with pytest.raises(ValueError, match="size"):
        bootstrap_population("seed", 0)


async def test_save_and_load_population_round_trip() -> None:
    sessions = await make_initialized_sessions()

    population = bootstrap_population("Restate the goal. Verify the result.", 3, random_seed=2)
    for genome in population:
        genome.scores = clarity_evaluator(genome)

    assert await save_population("user-evo", population, session_factory=sessions) == 3

    async with sessions() as db:
        total = await db.execute(
            select(func.count())
            .select_from(PromptGenomeRow)
            .where(PromptGenomeRow.user_id == "user-evo")
        )
        assert total.scalar_one() == 3

    latest_generation = max(genome.generation for genome in population)
    latest_ids = sorted(genome.id for genome in population if genome.generation == latest_generation)
    loaded = await load_population("user-evo", session_factory=sessions)
    assert sorted(genome.id for genome in loaded) == latest_ids
    assert all(genome.generation == latest_generation for genome in loaded)
    by_id = {genome.id: genome for genome in loaded}
    for original in population:
        if original.generation != latest_generation:
            continue
        assert by_id[original.id].scores == clarity_evaluator(original)
        assert by_id[original.id].parent_ids == original.parent_ids

    assert await load_population("user-other", session_factory=sessions) == []

    population[0].scores = dict(population[0].scores, task_success=0.1)
    assert await save_population("user-evo", population, session_factory=sessions) == 3
    async with sessions() as db:
        total = await db.execute(
            select(func.count())
            .select_from(PromptGenomeRow)
            .where(PromptGenomeRow.user_id == "user-evo")
        )
        assert total.scalar_one() == 3
        best = await get_best_genome(db, "user-evo")
    assert best is not None
    assert best.id != population[0].id
    assert best.scores["task_success"] == pytest.approx(1.0)

    child = PromptGenome(
        id="child_1",
        prompt_text=population[0].prompt_text,
        model_params=dict(population[0].model_params),
        scores=clarity_evaluator(population[0]),
        generation=latest_generation + 1,
        parent_ids=(population[0].id,),
    )
    await save_population("user-evo", [child], session_factory=sessions)
    latest = await load_population("user-evo", session_factory=sessions)
    assert [genome.id for genome in latest] == ["child_1"]
    assert latest[0].generation == latest_generation + 1
