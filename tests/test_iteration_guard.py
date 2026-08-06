from app.core.iteration_guard import GuardConfig, IterationGuard


def test_max_rounds_limit():
    config = GuardConfig(max_rounds=5)
    guard = IterationGuard(config)
    guard.start_session("s1")
    for _ in range(4):
        status = guard.record_round("s1")
        assert status["continue"]
    status = guard.record_round("s1")
    assert not status["continue"]
    assert "Max rounds" in status["reason"]

def test_stagnation_detection():
    config = GuardConfig(max_stagnation_rounds=3)
    guard = IterationGuard(config)
    guard.start_session("s1")
    for _ in range(4):
        status = guard.record_round("s1", score=0.5)
    assert not status["continue"]
    assert "Stagnation" in status["reason"]

def test_improvement_resets_stagnation():
    config = GuardConfig(max_stagnation_rounds=3)
    guard = IterationGuard(config)
    guard.start_session("s1")
    guard.record_round("s1", score=0.5)
    guard.record_round("s1", score=0.5)
    guard.record_round("s1", score=0.6)  # improvement
    status = guard.record_round("s1", score=0.6)
    assert status["continue"]
