"""Tests for authorization security."""


from app.security.authorization_security import (
    AuthorizationAuditLog,
    AuthorizationEncryption,
    AuthorizationRateLimiter,
    AuthorizationValidator,
)


class TestAuthorizationEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = AuthorizationEncryption.hash_password('testpass')
        assert AuthorizationEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = AuthorizationEncryption.hash_password('testpass')
        assert not AuthorizationEncryption.verify_password('wrong', hashed)


class TestAuthorizationValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert AuthorizationValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not AuthorizationValidator.validate_email('invalid')


class TestAuthorizationRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = AuthorizationRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = AuthorizationRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestAuthorizationAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = AuthorizationAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = AuthorizationAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
