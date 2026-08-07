"""Tests for token security."""


from app.security.token_security import (
    TokenAuditLog,
    TokenEncryption,
    TokenRateLimiter,
    TokenValidator,
)


class TestTokenEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = TokenEncryption.hash_password('testpass')
        assert TokenEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = TokenEncryption.hash_password('testpass')
        assert not TokenEncryption.verify_password('wrong', hashed)


class TestTokenValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert TokenValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not TokenValidator.validate_email('invalid')


class TestTokenRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = TokenRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = TokenRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestTokenAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = TokenAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = TokenAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
