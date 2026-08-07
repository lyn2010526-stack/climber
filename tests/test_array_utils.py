"""Tests for array utility."""

from datetime import UTC, datetime, timedelta

from app.utils.array_utils import (
    ArrayCollectionUtils,
    ArrayCryptoUtils,
    ArrayDateUtils,
    ArrayNumericUtils,
    ArrayStringUtils,
    ArrayValidationUtils,
)


class TestArrayStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert ArrayStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert ArrayStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = ArrayStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert ArrayStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = ArrayStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestArrayDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = ArrayDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = ArrayDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = ArrayDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestArrayNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert ArrayNumericUtils.clamp(15, 0, 10) == 10
        assert ArrayNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert ArrayNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = ArrayNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestArrayCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(ArrayCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = ArrayCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = ArrayCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestArrayCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = ArrayCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = ArrayCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestArrayValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert ArrayValidationUtils.is_empty('')
        assert ArrayValidationUtils.is_empty([])
        assert not ArrayValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert ArrayValidationUtils.is_valid_json('{"key": "value"}')
        assert not ArrayValidationUtils.is_valid_json('invalid')
