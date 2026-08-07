"""Tests for encryption security."""


from app.security.encryption_security import (
    EncryptionAuditLog,
    EncryptionEncryption,
    EncryptionRateLimiter,
    EncryptionValidator,
)


class TestEncryptionEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = EncryptionEncryption.hash_password('testpass')
        assert EncryptionEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = EncryptionEncryption.hash_password('testpass')
        assert not EncryptionEncryption.verify_password('wrong', hashed)


class TestEncryptionValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert EncryptionValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not EncryptionValidator.validate_email('invalid')


class TestEncryptionRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = EncryptionRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = EncryptionRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestEncryptionAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = EncryptionAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = EncryptionAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
