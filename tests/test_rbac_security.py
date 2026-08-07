"""Tests for rbac security."""


from app.security.rbac_security import (
    RbacAuditLog,
    RbacEncryption,
    RbacRateLimiter,
    RbacValidator,
)


class TestRbacEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = RbacEncryption.hash_password('testpass')
        assert RbacEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = RbacEncryption.hash_password('testpass')
        assert not RbacEncryption.verify_password('wrong', hashed)


class TestRbacValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert RbacValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not RbacValidator.validate_email('invalid')


class TestRbacRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = RbacRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = RbacRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestRbacAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = RbacAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = RbacAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
