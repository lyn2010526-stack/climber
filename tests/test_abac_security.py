"""Tests for abac security."""


from app.security.abac_security import (
    AbacAuditLog,
    AbacEncryption,
    AbacRateLimiter,
    AbacValidator,
)


class TestAbacEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = AbacEncryption.hash_password('testpass')
        assert AbacEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = AbacEncryption.hash_password('testpass')
        assert not AbacEncryption.verify_password('wrong', hashed)


class TestAbacValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert AbacValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not AbacValidator.validate_email('invalid')


class TestAbacRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = AbacRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = AbacRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestAbacAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = AbacAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = AbacAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
