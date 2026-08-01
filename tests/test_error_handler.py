import pytest
import asyncio
from app.core.error_handler import (
    APIError, ErrorSeverity, CircuitBreaker, RetryWithBackoff, RetryConfig
)

def test_api_error_classification():
    assert APIError.from_status(401).severity == ErrorSeverity.STOP
    assert APIError.from_status(429).severity == ErrorSeverity.RETRY
    assert APIError.from_status(503).severity == ErrorSeverity.FAILOVER
    assert APIError.from_status(500).severity == ErrorSeverity.FAILOVER

def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=3)
    assert not cb.is_open
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()
    assert cb.is_open

def test_circuit_breaker_recovers():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
    cb.record_failure()
    assert cb.is_open
    import time
    time.sleep(0.15)
    assert not cb.is_open  # half_open after timeout

@pytest.mark.asyncio
async def test_retry_succeeds_eventually():
    config = RetryConfig(max_retries=3, base_delay=0.01)
    retry = RetryWithBackoff(config)

    call_count = 0
    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("temporary failure, retryable")
        return "success"

    result = await retry.execute(flaky)
    assert result == "success"
    assert call_count == 3

@pytest.mark.asyncio
async def test_retry_exhausts_and_raises():
    config = RetryConfig(max_retries=2, base_delay=0.01)
    retry = RetryWithBackoff(config)

    async def always_fail():
        raise Exception("503 service unavailable")

    with pytest.raises(Exception, match="503"):
        await retry.execute(always_fail)
