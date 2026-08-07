"""Tests for sqli security."""


from app.security.sqli_security import (
    SqliAuditLog,
    SqliEncryption,
    SqliRateLimiter,
    SqliValidator,
)


class TestSqliEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = SqliEncryption.hash_password('testpass')
        assert SqliEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = SqliEncryption.hash_password('testpass')
        assert not SqliEncryption.verify_password('wrong', hashed)


class TestSqliValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert SqliValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not SqliValidator.validate_email('invalid')


class TestSqliRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = SqliRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = SqliRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestSqliAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = SqliAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = SqliAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
