"""Tests for serialization utility."""

from datetime import UTC, datetime, timedelta

from app.utils.serialization_utils import (
    SerializationCollectionUtils,
    SerializationCryptoUtils,
    SerializationDateUtils,
    SerializationNumericUtils,
    SerializationStringUtils,
    SerializationValidationUtils,
)


class TestSerializationStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert SerializationStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert SerializationStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = SerializationStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert SerializationStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = SerializationStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestSerializationDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = SerializationDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = SerializationDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = SerializationDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestSerializationNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert SerializationNumericUtils.clamp(15, 0, 10) == 10
        assert SerializationNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert SerializationNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = SerializationNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestSerializationCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(SerializationCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = SerializationCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = SerializationCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestSerializationCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = SerializationCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = SerializationCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestSerializationValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert SerializationValidationUtils.is_empty('')
        assert SerializationValidationUtils.is_empty([])
        assert not SerializationValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert SerializationValidationUtils.is_valid_json('{"key": "value"}')
        assert not SerializationValidationUtils.is_valid_json('invalid')
