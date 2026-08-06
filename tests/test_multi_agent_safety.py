from app.multi_agent.safety import (
    CommunicationEnforcer,
    CommunicationRule,
    ConflictArbitrator,
    ConflictRecord,
    ConflictType,
    DeadlockDetector,
)


class TestDeadlockDetector:
    def test_no_deadlock_initially(self):
        detector = DeadlockDetector()
        status = detector.record_round(["proposal A"], ["decision 1"])
        assert not status["deadlock"]

    def test_max_rounds_trigger(self):
        detector = DeadlockDetector(max_total_rounds=5)
        for i in range(4):
            status = detector.record_round([f"prop {i}"], [f"dec {i}"])
            assert not status["deadlock"]
        status = detector.record_round(["prop 5"], ["dec 5"])
        assert status["deadlock"]
        assert "Max rounds" in status["reason"]

    def test_stagnation_detection(self):
        detector = DeadlockDetector(max_rounds_without_progress=3)
        # Same proposals over and over
        for _ in range(4):
            status = detector.record_round(["same proposal"], ["same decision"])
        assert status["deadlock"]
        assert "No progress" in status["reason"]


class TestConflictArbitrator:
    def test_register_and_resolve(self):
        arbitrator = ConflictArbitrator()
        conflict = ConflictRecord(
            conflict_type=ConflictType.APPROACH,
            parties=["coder", "reviewer"],
            description="Disagree on implementation",
            round_number=5,
        )
        arbitrator.register_conflict(conflict)
        resolution = arbitrator.resolve(conflict)
        assert resolution["strategy"] == "hybrid"

    def test_escalate_after_max_attempts(self):
        arbitrator = ConflictArbitrator()
        conflict = ConflictRecord(
            conflict_type=ConflictType.DISAGREEMENT,
            parties=["a", "b"],
            description="Stuck",
            round_number=10,
            attempts=3,
        )
        resolution = arbitrator.resolve(conflict)
        assert resolution["escalate"]

    def test_unresolved_tracking(self):
        arbitrator = ConflictArbitrator()
        conflict = ConflictRecord(
            conflict_type=ConflictType.SCOPE,
            parties=["planner", "coder"],
            description="Scope disagreement",
            round_number=3,
        )
        arbitrator.register_conflict(conflict)
        unresolved = arbitrator.get_unresolved()
        assert len(unresolved) == 1


class TestCommunicationEnforcer:
    def test_valid_message(self):
        enforcer = CommunicationEnforcer()
        result = enforcer.check_message("agent", "We should use approach X because it's faster (benchmark: 2x)")
        assert result["valid"]

    def test_message_too_long(self):
        rules = CommunicationRule(max_message_length=100)
        enforcer = CommunicationEnforcer(rules)
        result = enforcer.check_message("agent", "x" * 200)
        assert not result["valid"]

    def test_max_rebuttals(self):
        rules = CommunicationRule(max_rebuttals=2)
        enforcer = CommunicationEnforcer(rules)
        enforcer.check_message("a1", "disagree", topic="design")
        enforcer.check_message("a1", "still disagree", topic="design")
        result = enforcer.check_message("a1", "keep disagreeing", topic="design")
        assert not result["valid"]
        assert "Max rebuttals" in result["issues"][0]

    def test_reset_topic(self):
        rules = CommunicationRule(max_rebuttals=1)
        enforcer = CommunicationEnforcer(rules)
        enforcer.check_message("a1", "disagree", topic="design")
        enforcer.reset_topic("design")
        result = enforcer.check_message("a1", "disagree again", topic="design")
        assert result["valid"]
