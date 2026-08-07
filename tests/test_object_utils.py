"""Tests for object utility."""

from datetime import UTC, datetime, timedelta

from app.utils.object_utils import (
    ObjectCollectionUtils,
    ObjectCryptoUtils,
    ObjectDateUtils,
    ObjectNumericUtils,
    ObjectStringUtils,
    ObjectValidationUtils,
)


class TestObjectStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert ObjectStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert ObjectStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = ObjectStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert ObjectStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = ObjectStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestObjectDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = ObjectDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = ObjectDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = ObjectDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestObjectNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert ObjectNumericUtils.clamp(15, 0, 10) == 10
        assert ObjectNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert ObjectNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = ObjectNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestObjectCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(ObjectCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = ObjectCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = ObjectCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestObjectCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = ObjectCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = ObjectCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestObjectValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert ObjectValidationUtils.is_empty('')
        assert ObjectValidationUtils.is_empty([])
        assert not ObjectValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert ObjectValidationUtils.is_valid_json('{"key": "value"}')
        assert not ObjectValidationUtils.is_valid_json('invalid')
