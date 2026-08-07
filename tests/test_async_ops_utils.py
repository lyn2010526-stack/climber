"""Tests for async_ops utility."""

from datetime import UTC, datetime, timedelta

from app.utils.async_ops_utils import (
    AsyncOpsCollectionUtils,
    AsyncOpsCryptoUtils,
    AsyncOpsDateUtils,
    AsyncOpsNumericUtils,
    AsyncOpsStringUtils,
    AsyncOpsValidationUtils,
)


class TestAsyncOpsStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert AsyncOpsStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert AsyncOpsStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = AsyncOpsStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert AsyncOpsStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = AsyncOpsStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestAsyncOpsDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = AsyncOpsDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = AsyncOpsDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = AsyncOpsDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestAsyncOpsNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert AsyncOpsNumericUtils.clamp(15, 0, 10) == 10
        assert AsyncOpsNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert AsyncOpsNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = AsyncOpsNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestAsyncOpsCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(AsyncOpsCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = AsyncOpsCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = AsyncOpsCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestAsyncOpsCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = AsyncOpsCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = AsyncOpsCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestAsyncOpsValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert AsyncOpsValidationUtils.is_empty('')
        assert AsyncOpsValidationUtils.is_empty([])
        assert not AsyncOpsValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert AsyncOpsValidationUtils.is_valid_json('{"key": "value"}')
        assert not AsyncOpsValidationUtils.is_valid_json('invalid')
