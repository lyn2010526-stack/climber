"""Tests for oauth security."""


from app.security.oauth_security import (
    OauthAuditLog,
    OauthEncryption,
    OauthRateLimiter,
    OauthValidator,
)


class TestOauthEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = OauthEncryption.hash_password('testpass')
        assert OauthEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = OauthEncryption.hash_password('testpass')
        assert not OauthEncryption.verify_password('wrong', hashed)


class TestOauthValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert OauthValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not OauthValidator.validate_email('invalid')


class TestOauthRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = OauthRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = OauthRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestOauthAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = OauthAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = OauthAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
