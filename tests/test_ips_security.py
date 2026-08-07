"""Tests for ips security."""


from app.security.ips_security import (
    IpsAuditLog,
    IpsEncryption,
    IpsRateLimiter,
    IpsValidator,
)


class TestIpsEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = IpsEncryption.hash_password('testpass')
        assert IpsEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = IpsEncryption.hash_password('testpass')
        assert not IpsEncryption.verify_password('wrong', hashed)


class TestIpsValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert IpsValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not IpsValidator.validate_email('invalid')


class TestIpsRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = IpsRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = IpsRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestIpsAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = IpsAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = IpsAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
