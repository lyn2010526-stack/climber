"""Tests for saml security."""


from app.security.saml_security import (
    SamlAuditLog,
    SamlEncryption,
    SamlRateLimiter,
    SamlValidator,
)


class TestSamlEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = SamlEncryption.hash_password('testpass')
        assert SamlEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = SamlEncryption.hash_password('testpass')
        assert not SamlEncryption.verify_password('wrong', hashed)


class TestSamlValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert SamlValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not SamlValidator.validate_email('invalid')


class TestSamlRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = SamlRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = SamlRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestSamlAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = SamlAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = SamlAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
