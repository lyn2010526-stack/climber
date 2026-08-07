"""Tests for hashing security."""


from app.security.hashing_security import (
    HashingAuditLog,
    HashingEncryption,
    HashingRateLimiter,
    HashingValidator,
)


class TestHashingEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = HashingEncryption.hash_password('testpass')
        assert HashingEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = HashingEncryption.hash_password('testpass')
        assert not HashingEncryption.verify_password('wrong', hashed)


class TestHashingValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert HashingValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not HashingValidator.validate_email('invalid')


class TestHashingRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = HashingRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = HashingRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestHashingAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = HashingAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = HashingAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
