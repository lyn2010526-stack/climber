"""Tests for firewall security."""


from app.security.firewall_security import (
    FirewallAuditLog,
    FirewallEncryption,
    FirewallRateLimiter,
    FirewallValidator,
)


class TestFirewallEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = FirewallEncryption.hash_password('testpass')
        assert FirewallEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = FirewallEncryption.hash_password('testpass')
        assert not FirewallEncryption.verify_password('wrong', hashed)


class TestFirewallValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert FirewallValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not FirewallValidator.validate_email('invalid')


class TestFirewallRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = FirewallRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = FirewallRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestFirewallAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = FirewallAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = FirewallAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
