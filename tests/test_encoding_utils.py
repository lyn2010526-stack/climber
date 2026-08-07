"""Tests for encoding utility."""

from datetime import UTC, datetime, timedelta

from app.utils.encoding_utils import (
    EncodingCollectionUtils,
    EncodingCryptoUtils,
    EncodingDateUtils,
    EncodingNumericUtils,
    EncodingStringUtils,
    EncodingValidationUtils,
)


class TestEncodingStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert EncodingStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert EncodingStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = EncodingStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert EncodingStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = EncodingStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestEncodingDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = EncodingDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = EncodingDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = EncodingDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestEncodingNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert EncodingNumericUtils.clamp(15, 0, 10) == 10
        assert EncodingNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert EncodingNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = EncodingNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestEncodingCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(EncodingCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = EncodingCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = EncodingCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestEncodingCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = EncodingCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = EncodingCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestEncodingValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert EncodingValidationUtils.is_empty('')
        assert EncodingValidationUtils.is_empty([])
        assert not EncodingValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert EncodingValidationUtils.is_valid_json('{"key": "value"}')
        assert not EncodingValidationUtils.is_valid_json('invalid')
