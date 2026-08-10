import pytest

from app.core.token_tracker import QuotaExceededError, TokenBudget, TokenTracker


def test_record_usage():
    tracker = TokenTracker()
    tracker.record_usage("s1", 1000, 500)
    usage = tracker.get_session_usage("s1")
    assert usage.input_tokens == 1000
    assert usage.output_tokens == 500
    assert usage.total_tokens == 1500

def test_session_limit_enforcement():
    budget = TokenBudget(max_tokens_per_session=1000)
    tracker = TokenTracker(budget)
    with pytest.raises(QuotaExceededError):
        tracker.record_usage("s1", 2000, 0)

def test_daily_cost_limit():
    budget = TokenBudget(max_cost_per_day=0.001)
    tracker = TokenTracker(budget)
    with pytest.raises(QuotaExceededError):
        tracker.record_usage("s1", 100000, 100000)
