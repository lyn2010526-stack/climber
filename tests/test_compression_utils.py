"""Tests for compression utility."""

from datetime import UTC, datetime, timedelta

from app.utils.compression_utils import (
    CompressionCollectionUtils,
    CompressionCryptoUtils,
    CompressionDateUtils,
    CompressionNumericUtils,
    CompressionStringUtils,
    CompressionValidationUtils,
)


class TestCompressionStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert CompressionStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert CompressionStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = CompressionStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert CompressionStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = CompressionStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestCompressionDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = CompressionDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = CompressionDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = CompressionDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestCompressionNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert CompressionNumericUtils.clamp(15, 0, 10) == 10
        assert CompressionNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert CompressionNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = CompressionNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestCompressionCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(CompressionCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = CompressionCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = CompressionCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestCompressionCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = CompressionCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = CompressionCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestCompressionValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert CompressionValidationUtils.is_empty('')
        assert CompressionValidationUtils.is_empty([])
        assert not CompressionValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert CompressionValidationUtils.is_valid_json('{"key": "value"}')
        assert not CompressionValidationUtils.is_valid_json('invalid')
