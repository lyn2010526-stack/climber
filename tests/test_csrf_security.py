"""Tests for csrf security."""


from app.security.csrf_security import (
    CsrfAuditLog,
    CsrfEncryption,
    CsrfRateLimiter,
    CsrfValidator,
)


class TestCsrfEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = CsrfEncryption.hash_password('testpass')
        assert CsrfEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = CsrfEncryption.hash_password('testpass')
        assert not CsrfEncryption.verify_password('wrong', hashed)


class TestCsrfValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert CsrfValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not CsrfValidator.validate_email('invalid')


class TestCsrfRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = CsrfRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = CsrfRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestCsrfAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = CsrfAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = CsrfAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
