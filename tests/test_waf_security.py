"""Tests for waf security."""


from app.security.waf_security import (
    WafAuditLog,
    WafEncryption,
    WafRateLimiter,
    WafValidator,
)


class TestWafEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = WafEncryption.hash_password('testpass')
        assert WafEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = WafEncryption.hash_password('testpass')
        assert not WafEncryption.verify_password('wrong', hashed)


class TestWafValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert WafValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not WafValidator.validate_email('invalid')


class TestWafRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = WafRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = WafRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestWafAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = WafAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = WafAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
