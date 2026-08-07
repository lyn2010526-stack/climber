"""Tests for color utility."""

from datetime import UTC, datetime, timedelta

from app.utils.color_utils import (
    ColorCollectionUtils,
    ColorCryptoUtils,
    ColorDateUtils,
    ColorNumericUtils,
    ColorStringUtils,
    ColorValidationUtils,
)


class TestColorStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert ColorStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert ColorStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = ColorStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert ColorStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = ColorStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestColorDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = ColorDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = ColorDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = ColorDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestColorNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert ColorNumericUtils.clamp(15, 0, 10) == 10
        assert ColorNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert ColorNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = ColorNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestColorCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(ColorCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = ColorCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = ColorCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestColorCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = ColorCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = ColorCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestColorValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert ColorValidationUtils.is_empty('')
        assert ColorValidationUtils.is_empty([])
        assert not ColorValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert ColorValidationUtils.is_valid_json('{"key": "value"}')
        assert not ColorValidationUtils.is_valid_json('invalid')
