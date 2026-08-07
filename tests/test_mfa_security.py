"""Tests for mfa security."""


from app.security.mfa_security import (
    MfaAuditLog,
    MfaEncryption,
    MfaRateLimiter,
    MfaValidator,
)


class TestMfaEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = MfaEncryption.hash_password('testpass')
        assert MfaEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = MfaEncryption.hash_password('testpass')
        assert not MfaEncryption.verify_password('wrong', hashed)


class TestMfaValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert MfaValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not MfaValidator.validate_email('invalid')


class TestMfaRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = MfaRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = MfaRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestMfaAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = MfaAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = MfaAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
