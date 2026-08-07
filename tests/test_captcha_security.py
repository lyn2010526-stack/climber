"""Tests for captcha security."""


from app.security.captcha_security import (
    CaptchaAuditLog,
    CaptchaEncryption,
    CaptchaRateLimiter,
    CaptchaValidator,
)


class TestCaptchaEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = CaptchaEncryption.hash_password('testpass')
        assert CaptchaEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = CaptchaEncryption.hash_password('testpass')
        assert not CaptchaEncryption.verify_password('wrong', hashed)


class TestCaptchaValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert CaptchaValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not CaptchaValidator.validate_email('invalid')


class TestCaptchaRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = CaptchaRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = CaptchaRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestCaptchaAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = CaptchaAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = CaptchaAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
