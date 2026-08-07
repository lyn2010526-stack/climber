"""Tests for http utility."""

from datetime import UTC, datetime, timedelta

from app.utils.http_utils import (
    HttpCollectionUtils,
    HttpCryptoUtils,
    HttpDateUtils,
    HttpNumericUtils,
    HttpStringUtils,
    HttpValidationUtils,
)


class TestHttpStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert HttpStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert HttpStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = HttpStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert HttpStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = HttpStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestHttpDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = HttpDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = HttpDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = HttpDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestHttpNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert HttpNumericUtils.clamp(15, 0, 10) == 10
        assert HttpNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert HttpNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = HttpNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestHttpCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(HttpCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = HttpCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = HttpCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestHttpCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = HttpCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = HttpCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestHttpValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert HttpValidationUtils.is_empty('')
        assert HttpValidationUtils.is_empty([])
        assert not HttpValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert HttpValidationUtils.is_valid_json('{"key": "value"}')
        assert not HttpValidationUtils.is_valid_json('invalid')
