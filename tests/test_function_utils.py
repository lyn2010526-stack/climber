"""Tests for function utility."""

from datetime import UTC, datetime, timedelta

from app.utils.function_utils import (
    FunctionCollectionUtils,
    FunctionCryptoUtils,
    FunctionDateUtils,
    FunctionNumericUtils,
    FunctionStringUtils,
    FunctionValidationUtils,
)


class TestFunctionStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert FunctionStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert FunctionStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = FunctionStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert FunctionStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = FunctionStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestFunctionDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = FunctionDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = FunctionDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = FunctionDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestFunctionNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert FunctionNumericUtils.clamp(15, 0, 10) == 10
        assert FunctionNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert FunctionNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = FunctionNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestFunctionCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(FunctionCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = FunctionCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = FunctionCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestFunctionCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = FunctionCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = FunctionCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestFunctionValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert FunctionValidationUtils.is_empty('')
        assert FunctionValidationUtils.is_empty([])
        assert not FunctionValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert FunctionValidationUtils.is_valid_json('{"key": "value"}')
        assert not FunctionValidationUtils.is_valid_json('invalid')
