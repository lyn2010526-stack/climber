"""Tests for vpn security."""


from app.security.vpn_security import (
    VpnAuditLog,
    VpnEncryption,
    VpnRateLimiter,
    VpnValidator,
)


class TestVpnEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = VpnEncryption.hash_password('testpass')
        assert VpnEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = VpnEncryption.hash_password('testpass')
        assert not VpnEncryption.verify_password('wrong', hashed)


class TestVpnValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert VpnValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not VpnValidator.validate_email('invalid')


class TestVpnRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = VpnRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = VpnRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestVpnAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = VpnAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = VpnAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
