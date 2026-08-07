"""Tests for ldap security."""


from app.security.ldap_security import (
    LdapAuditLog,
    LdapEncryption,
    LdapRateLimiter,
    LdapValidator,
)


class TestLdapEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = LdapEncryption.hash_password('testpass')
        assert LdapEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = LdapEncryption.hash_password('testpass')
        assert not LdapEncryption.verify_password('wrong', hashed)


class TestLdapValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert LdapValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not LdapValidator.validate_email('invalid')


class TestLdapRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = LdapRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = LdapRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestLdapAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = LdapAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = LdapAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
