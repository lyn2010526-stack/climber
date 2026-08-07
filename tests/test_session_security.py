"""Tests for session security."""


from app.security.session_security import (
    SessionAuditLog,
    SessionEncryption,
    SessionRateLimiter,
    SessionValidator,
)


class TestSessionEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = SessionEncryption.hash_password('testpass')
        assert SessionEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = SessionEncryption.hash_password('testpass')
        assert not SessionEncryption.verify_password('wrong', hashed)


class TestSessionValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert SessionValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not SessionValidator.validate_email('invalid')


class TestSessionRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = SessionRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = SessionRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestSessionAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = SessionAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = SessionAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
