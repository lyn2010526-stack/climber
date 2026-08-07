"""Tests for math utility."""

from datetime import UTC, datetime, timedelta

from app.utils.math_utils import (
    MathCollectionUtils,
    MathCryptoUtils,
    MathDateUtils,
    MathNumericUtils,
    MathStringUtils,
    MathValidationUtils,
)


class TestMathStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert MathStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert MathStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = MathStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert MathStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = MathStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestMathDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = MathDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = MathDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = MathDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestMathNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert MathNumericUtils.clamp(15, 0, 10) == 10
        assert MathNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert MathNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = MathNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestMathCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(MathCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = MathCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = MathCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestMathCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = MathCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = MathCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestMathValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert MathValidationUtils.is_empty('')
        assert MathValidationUtils.is_empty([])
        assert not MathValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert MathValidationUtils.is_valid_json('{"key": "value"}')
        assert not MathValidationUtils.is_valid_json('invalid')
