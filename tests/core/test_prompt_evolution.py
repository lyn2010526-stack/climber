import pytest

from app.core.prompts.evolution import (
    EvolutionConfig,
    FitnessWeights,
    PromptEvolutionEngine,
    PromptGenome,
)


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


def test_safety_penalty_lowers_composite() -> None:
    weights = FitnessWeights()
    clean = {"task_success": 1.0, "metaphor_comprehension": 1.0, "meta_correction": 1.0, "safety_violation": 0.0}
    unsafe = dict(clean, safety_violation=0.5)
    assert weights.composite(unsafe) < weights.composite(clean)


def test_population_best_improves_across_generations() -> None:
    config = EvolutionConfig(population_size=8, elite_count=2, max_generations=6, random_seed=3)
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
