import pytest

from app.core.metrics import MetricsCollector


@pytest.fixture
def collector():
    return MetricsCollector()

def test_start_and_end_session(collector):
    collector.start_session("s1")
    assert collector.get_global_metrics().active_sessions == 1
    collector.end_session("s1")
    assert collector.get_global_metrics().active_sessions == 0

def test_record_iteration(collector):
    collector.record_iteration("s1")
    collector.record_iteration("s1")
    metrics = collector.get_session_metrics("s1")
    assert metrics.iteration_count == 2

def test_record_tool_call(collector):
    collector.record_tool_call("s1", success=True)
    collector.record_tool_call("s1", success=False)
    metrics = collector.get_session_metrics("s1")
    assert metrics.tool_calls == 2
    assert metrics.success_rate == 0.5

def test_record_api_call(collector):
    collector.record_api_call("s1", latency_ms=100.0)
    collector.record_api_call("s1", latency_ms=200.0, error=True)
    g = collector.get_global_metrics()
    assert g.total_api_calls == 2
    assert g.api_success_rate == 0.5

def test_record_tokens(collector):
    collector.record_tokens("s1", 1000, 500)
    collector.record_tokens("s1", 2000, 1000)
    metrics = collector.get_session_metrics("s1")
    assert metrics.total_tokens == 4500

def test_p95_latency(collector):
    for i in range(100):
        collector.record_api_call("s1", latency_ms=float(i))
    g = collector.get_global_metrics()
    assert g.p95_api_latency_ms >= 94  # ~95th percentile

def test_get_snapshot(collector):
    collector.start_session("s1")
    collector.record_iteration("s1")
    collector.record_tool_call("s1", success=True)
    snapshot = collector.get_snapshot()
    assert "global" in snapshot
    assert "sessions" in snapshot
