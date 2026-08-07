"""Tests for key_management security."""


from app.security.key_management_security import (
    KeyManagementAuditLog,
    KeyManagementEncryption,
    KeyManagementRateLimiter,
    KeyManagementValidator,
)


class TestKeyManagementEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = KeyManagementEncryption.hash_password('testpass')
        assert KeyManagementEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = KeyManagementEncryption.hash_password('testpass')
        assert not KeyManagementEncryption.verify_password('wrong', hashed)


class TestKeyManagementValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert KeyManagementValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not KeyManagementValidator.validate_email('invalid')


class TestKeyManagementRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = KeyManagementRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = KeyManagementRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestKeyManagementAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = KeyManagementAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = KeyManagementAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
