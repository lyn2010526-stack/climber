"""Tests for vault security."""


from app.security.vault_security import (
    VaultAuditLog,
    VaultEncryption,
    VaultRateLimiter,
    VaultValidator,
)


class TestVaultEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = VaultEncryption.hash_password('testpass')
        assert VaultEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = VaultEncryption.hash_password('testpass')
        assert not VaultEncryption.verify_password('wrong', hashed)


class TestVaultValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert VaultValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not VaultValidator.validate_email('invalid')


class TestVaultRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = VaultRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = VaultRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestVaultAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = VaultAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = VaultAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
