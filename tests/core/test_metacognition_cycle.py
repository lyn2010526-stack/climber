from app.core.metacognition.orchestrator import ExecutionContext, MetacognitionOrchestrator


def test_run_cycle_records_selected_hypothesis_and_causal_edge():
    orchestrator = MetacognitionOrchestrator()

    result = orchestrator.run_cycle(
        goal="inspect the repository",
        observation={"phase": "inspect"},
        action="read_file",
        outcome="observed repository",
        available_tools=["read_file", "list_files"],
    )

    assert result.selected is not None
    assert result.record["selected_hypothesis"] == result.selected.id
    assert result.monitoring.prediction_error == 0.0
    assert len(orchestrator._causal.graph.edges) == 1
    assert orchestrator.get_state().cycle_records == [result.record]


def test_run_cycle_exposes_contradictions_and_risk():
    orchestrator = MetacognitionOrchestrator()
    orchestrator.initialize(
        ExecutionContext(
            goal="implement and verify",
            available_tools=["read_file", "write_file"],
        )
    )
    orchestrator._state.simulation.paths[0].risk_factors.append("uncertain outcome")

    result = orchestrator.run_cycle(
        goal="implement and verify",
        observation={"phase": "verify", "status": "failed"},
        action="write_file",
        outcome="Error: verification failed",
        iteration=2,
    )

    assert result.monitoring.contradiction_count >= 1
    assert result.monitoring.risk_score > 0
    assert result.attribution.causal_chain[-1].is_failure_point
