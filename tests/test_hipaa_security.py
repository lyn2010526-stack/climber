"""Tests for hipaa security."""


from app.security.hipaa_security import (
    HipaaAuditLog,
    HipaaEncryption,
    HipaaRateLimiter,
    HipaaValidator,
)


class TestHipaaEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = HipaaEncryption.hash_password('testpass')
        assert HipaaEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = HipaaEncryption.hash_password('testpass')
        assert not HipaaEncryption.verify_password('wrong', hashed)


class TestHipaaValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert HipaaValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not HipaaValidator.validate_email('invalid')


class TestHipaaRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = HipaaRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = HipaaRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestHipaaAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = HipaaAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = HipaaAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
