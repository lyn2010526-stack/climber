"""Tests for xss security."""


from app.security.xss_security import (
    XssAuditLog,
    XssEncryption,
    XssRateLimiter,
    XssValidator,
)


class TestXssEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = XssEncryption.hash_password('testpass')
        assert XssEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = XssEncryption.hash_password('testpass')
        assert not XssEncryption.verify_password('wrong', hashed)


class TestXssValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert XssValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not XssValidator.validate_email('invalid')


class TestXssRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = XssRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = XssRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestXssAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = XssAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = XssAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
