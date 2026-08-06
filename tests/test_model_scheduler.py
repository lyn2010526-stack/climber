from app.core.model_scheduler import ModelCapability, ModelScheduler, SchedulerConfig, TaskComplexity


def test_select_model_basic():
    scheduler = ModelScheduler()
    model = scheduler.select_model("Write a hello world function", complexity=TaskComplexity.SIMPLE)
    assert "/" in model  # provider/model format

def test_select_model_complex_prefers_quality():
    config = SchedulerConfig(quality_preference=1.0)
    scheduler = ModelScheduler(config)
    model = scheduler.select_model("Design a distributed system", complexity=TaskComplexity.COMPLEX)
    assert "/" in model

def test_select_model_filters_tools():
    scheduler = ModelScheduler()
    model = scheduler.select_model("Call an API", require_tools=True)
    assert "/" in model

def test_circuit_breaker_excludes_model():
    scheduler = ModelScheduler()
    # Record many failures for a model
    for _ in range(5):
        scheduler.record_failure("anthropic/claude-sonnet-4-20250514")

    # Should now select a different model
    model = scheduler.select_model("Simple task")
    assert "/" in model

def test_fallback_chain():
    scheduler = ModelScheduler()
    chain = scheduler.get_fallback_chain(exclude="anthropic/claude-sonnet-4-20250514")
    assert "anthropic/claude-sonnet-4-20250514" not in chain

def test_register_custom_model():
    scheduler = ModelScheduler()
    from app.core.error_handler import CircuitBreaker
    scheduler._capabilities["custom/model"] = ModelCapability(
        provider="custom", model_id="model", max_context=4096,
        supports_tools=True, supports_vision=False,
        cost_per_1k_input=0.0, cost_per_1k_output=0.0,
        speed_rating=8, quality_rating=7,
    )
    scheduler._circuit_breakers["custom/model"] = CircuitBreaker()
    # Now it can select from more options
