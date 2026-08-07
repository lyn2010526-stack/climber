"""Tests for networking utility."""

from datetime import UTC, datetime, timedelta

from app.utils.networking_utils import (
    NetworkingCollectionUtils,
    NetworkingCryptoUtils,
    NetworkingDateUtils,
    NetworkingNumericUtils,
    NetworkingStringUtils,
    NetworkingValidationUtils,
)


class TestNetworkingStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert NetworkingStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert NetworkingStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = NetworkingStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert NetworkingStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = NetworkingStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestNetworkingDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = NetworkingDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = NetworkingDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = NetworkingDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestNetworkingNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert NetworkingNumericUtils.clamp(15, 0, 10) == 10
        assert NetworkingNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert NetworkingNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = NetworkingNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestNetworkingCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(NetworkingCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = NetworkingCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = NetworkingCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestNetworkingCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = NetworkingCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = NetworkingCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestNetworkingValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert NetworkingValidationUtils.is_empty('')
        assert NetworkingValidationUtils.is_empty([])
        assert not NetworkingValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert NetworkingValidationUtils.is_valid_json('{"key": "value"}')
        assert not NetworkingValidationUtils.is_valid_json('invalid')
