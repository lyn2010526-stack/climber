"""Tests for logging utility."""

from datetime import UTC, datetime, timedelta

from app.utils.logging_utils import (
    LoggingCollectionUtils,
    LoggingCryptoUtils,
    LoggingDateUtils,
    LoggingNumericUtils,
    LoggingStringUtils,
    LoggingValidationUtils,
)


class TestLoggingStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert LoggingStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert LoggingStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = LoggingStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert LoggingStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = LoggingStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestLoggingDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = LoggingDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = LoggingDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = LoggingDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestLoggingNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert LoggingNumericUtils.clamp(15, 0, 10) == 10
        assert LoggingNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert LoggingNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = LoggingNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestLoggingCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(LoggingCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = LoggingCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = LoggingCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestLoggingCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = LoggingCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = LoggingCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestLoggingValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert LoggingValidationUtils.is_empty('')
        assert LoggingValidationUtils.is_empty([])
        assert not LoggingValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert LoggingValidationUtils.is_valid_json('{"key": "value"}')
        assert not LoggingValidationUtils.is_valid_json('invalid')
