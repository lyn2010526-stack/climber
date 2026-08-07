"""Tests for signing security."""


from app.security.signing_security import (
    SigningAuditLog,
    SigningEncryption,
    SigningRateLimiter,
    SigningValidator,
)


class TestSigningEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = SigningEncryption.hash_password('testpass')
        assert SigningEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = SigningEncryption.hash_password('testpass')
        assert not SigningEncryption.verify_password('wrong', hashed)


class TestSigningValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert SigningValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not SigningValidator.validate_email('invalid')


class TestSigningRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = SigningRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = SigningRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestSigningAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = SigningAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = SigningAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
