import pytest

from app.core.structured_logging import (
    LogTimer,
    clear_context,
    correlation_id,
    get_logger,
    session_ctx,
    set_context,
    set_correlation,
    setup_logging,
)


def test_setup_logging():
    setup_logging(level="DEBUG")
    logger = get_logger("test")
    assert logger is not None

def test_set_correlation():
    cid = set_correlation()
    assert len(cid) == 12
    assert correlation_id.get() == cid

def test_set_context():
    set_context(session_id="s1", agent_id="a1")
    assert session_ctx.get() == "s1"

def test_clear_context():
    set_context(session_id="s1")
    clear_context()
    assert session_ctx.get() == ""

def test_log_timer_success(caplog):
    setup_logging(level="INFO", json_format=False)
    logger = get_logger("timer_test")
    with LogTimer(logger, "test_op"):
        pass
    # No exception means success path executed

def test_log_timer_failure():
    setup_logging(level="INFO", json_format=False)
    logger = get_logger("timer_test")
    with pytest.raises(ValueError):
        with LogTimer(logger, "failing_op"):
            raise ValueError("test error")
