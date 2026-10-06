from app.core.metacognition.causal import CausalGraph
from app.core.metacognition.hypothesis import WorldState
from app.core.observability.trace import TraceCollector


def test_causal_graph_tracks_uncertainty_and_suggests_probe():
    graph = CausalGraph()
    edge = graph.update({"mode": "unknown"}, "probe", {"mode": "known"}, "observed", success=True, prediction_error=0.7)

    assert edge.success_count == 1
    assert edge.uncertainty == 0.7
    assert graph.suggest_probes({"mode": "unknown"})[0]["action"] == "probe"


def test_causal_graph_decay_weakens_stale_confidence():
    graph = CausalGraph()
    edge = graph.update({"mode": "unknown"}, "probe", {"mode": "known"}, "observed")
    graph.decay(0.5)

    assert edge.confidence == 0.125
    assert edge.uncertainty == 0.875


def test_world_state_observation_and_decay_are_explicit():
    state = WorldState({"temperature": 20}, uncertainty=0.1)
    state.observe({"temperature": 21}, uncertainty=0.2)
    state.decay(0.5)

    assert state.values["temperature"] == 21
    assert state.uncertainty == 0.6


def test_trace_collector_records_factual_tool_observation():
    collector = TraceCollector()
    span = collector.start_span("tool")
    assert span is not None
    collector.record_tool_observation(span, "read_file", {"path": "x"}, result="ok", success=True, prediction_error=0.25)

    stored = collector.get_span(span.span_id)
    assert stored is not None
    assert stored.events[-1]["type"] == "tool_observation"
    assert stored.events[-1]["data"]["prediction_error"] == 0.25
    collector.close()
