"""Tests for cache utility."""

from datetime import UTC, datetime, timedelta

from app.utils.cache_utils import (
    CacheCollectionUtils,
    CacheCryptoUtils,
    CacheDateUtils,
    CacheNumericUtils,
    CacheStringUtils,
    CacheValidationUtils,
)


class TestCacheStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert CacheStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert CacheStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = CacheStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert CacheStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = CacheStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestCacheDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = CacheDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = CacheDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = CacheDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestCacheNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert CacheNumericUtils.clamp(15, 0, 10) == 10
        assert CacheNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert CacheNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = CacheNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestCacheCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(CacheCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = CacheCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = CacheCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestCacheCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = CacheCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = CacheCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestCacheValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert CacheValidationUtils.is_empty('')
        assert CacheValidationUtils.is_empty([])
        assert not CacheValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert CacheValidationUtils.is_valid_json('{"key": "value"}')
        assert not CacheValidationUtils.is_valid_json('invalid')
