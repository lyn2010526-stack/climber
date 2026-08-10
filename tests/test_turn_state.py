"""TDD: TurnState state machine."""

import os

os.environ["APP_TESTING"] = "true"

from app.core.turn_state import TurnState, TurnStateMachine, can_transition


def test_can_transition_valid():
    assert can_transition(TurnState.PENDING, TurnState.RUNNING)
    assert can_transition(TurnState.RUNNING, TurnState.COMPLETED)
    assert can_transition(TurnState.RUNNING, TurnState.AWAITING_APPROVAL)
    assert can_transition(TurnState.AWAITING_APPROVAL, TurnState.RUNNING)


def test_can_transition_invalid():
    assert not can_transition(TurnState.COMPLETED, TurnState.RUNNING)
    assert not can_transition(TurnState.FAILED, TurnState.PENDING)
    assert not can_transition(TurnState.PENDING, TurnState.COMPLETED)


def test_state_machine_lifecycle():
    sm = TurnStateMachine(turn_id="t1", session_id="s1")
    assert sm.record.state == TurnState.PENDING
    assert not sm.is_terminal

    assert sm.transition(TurnState.RUNNING)
    assert sm.record.started_at is not None

    assert sm.transition(TurnState.COMPLETED)
    assert sm.is_terminal
    assert sm.record.completed_at is not None


def test_state_machine_invalid_transition():
    sm = TurnStateMachine(turn_id="t1", session_id="s1")
    assert not sm.transition(TurnState.COMPLETED)
    assert sm.record.state == TurnState.PENDING


def test_state_machine_awaiting_approval():
    sm = TurnStateMachine(turn_id="t1", session_id="s1")
    sm.transition(TurnState.RUNNING)
    assert sm.transition(TurnState.AWAITING_APPROVAL)
    assert sm.transition(TurnState.RUNNING)
    assert sm.transition(TurnState.COMPLETED)
