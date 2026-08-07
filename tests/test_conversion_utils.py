"""Tests for conversion utility."""

from datetime import UTC, datetime, timedelta

from app.utils.conversion_utils import (
    ConversionCollectionUtils,
    ConversionCryptoUtils,
    ConversionDateUtils,
    ConversionNumericUtils,
    ConversionStringUtils,
    ConversionValidationUtils,
)


class TestConversionStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert ConversionStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert ConversionStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = ConversionStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert ConversionStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = ConversionStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestConversionDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = ConversionDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = ConversionDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = ConversionDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestConversionNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert ConversionNumericUtils.clamp(15, 0, 10) == 10
        assert ConversionNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert ConversionNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = ConversionNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestConversionCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(ConversionCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = ConversionCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = ConversionCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestConversionCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = ConversionCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = ConversionCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestConversionValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert ConversionValidationUtils.is_empty('')
        assert ConversionValidationUtils.is_empty([])
        assert not ConversionValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert ConversionValidationUtils.is_valid_json('{"key": "value"}')
        assert not ConversionValidationUtils.is_valid_json('invalid')
