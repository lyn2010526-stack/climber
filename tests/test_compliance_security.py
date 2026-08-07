"""Tests for compliance security."""


from app.security.compliance_security import (
    ComplianceAuditLog,
    ComplianceEncryption,
    ComplianceRateLimiter,
    ComplianceValidator,
)


class TestComplianceEncryption:
    """Tests for encryption."""

    def test_hash_and_verify(self):
        hashed = ComplianceEncryption.hash_password('testpass')
        assert ComplianceEncryption.verify_password('testpass', hashed)

    def test_wrong_password(self):
        hashed = ComplianceEncryption.hash_password('testpass')
        assert not ComplianceEncryption.verify_password('wrong', hashed)


class TestComplianceValidator:
    """Tests for validator."""

    def test_valid_email(self):
        assert ComplianceValidator.validate_email('test@example.com')

    def test_invalid_email(self):
        assert not ComplianceValidator.validate_email('invalid')


class TestComplianceRateLimiter:
    """Tests for rate limiter."""

    def test_within_limit(self):
        limiter = ComplianceRateLimiter(max_requests=5)
        for _ in range(5):
            assert limiter.is_allowed('user1')

    def test_exceeds_limit(self):
        limiter = ComplianceRateLimiter(max_requests=2)
        limiter.is_allowed('user1')
        limiter.is_allowed('user1')
        assert not limiter.is_allowed('user1')


class TestComplianceAuditLog:
    """Tests for audit log."""

    def test_log(self):
        log = ComplianceAuditLog()
        entry = log.log('create', 'user1', 'resource1')
        assert entry['action'] == 'create'

    def test_query(self):
        log = ComplianceAuditLog()
        log.log('create', 'user1', 'r1')
        log.log('delete', 'user2', 'r2')
        results = log.query(actor='user1')
        assert len(results) == 1
