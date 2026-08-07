"""Tests for secrets security."""


from app.security.secrets_security import (
    SecretsAuditLog,
    SecretsEncryption,
    SecretsRateLimiter,
    SecretsValidator,
)


class TestSecretsEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = SecretsEncryption.hash_password('testpass')
        assert SecretsEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = SecretsEncryption.hash_password('testpass')
        assert not SecretsEncryption.verify_password('wrong', hashed)


class TestSecretsValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert SecretsValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not SecretsValidator.validate_email('invalid')


class TestSecretsRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = SecretsRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = SecretsRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestSecretsAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = SecretsAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = SecretsAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
