"""Tests for number utility."""

from datetime import UTC, datetime, timedelta

from app.utils.number_utils import (
    NumberCollectionUtils,
    NumberCryptoUtils,
    NumberDateUtils,
    NumberNumericUtils,
    NumberStringUtils,
    NumberValidationUtils,
)


class TestNumberStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert NumberStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert NumberStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = NumberStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert NumberStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = NumberStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestNumberDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = NumberDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = NumberDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = NumberDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestNumberNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert NumberNumericUtils.clamp(15, 0, 10) == 10
        assert NumberNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert NumberNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = NumberNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestNumberCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(NumberCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = NumberCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = NumberCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestNumberCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = NumberCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = NumberCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestNumberValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert NumberValidationUtils.is_empty('')
        assert NumberValidationUtils.is_empty([])
        assert not NumberValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert NumberValidationUtils.is_valid_json('{"key": "value"}')
        assert not NumberValidationUtils.is_valid_json('invalid')
