"""Tests for config utility."""

from datetime import UTC, datetime, timedelta

from app.utils.config_utils import (
    ConfigCollectionUtils,
    ConfigCryptoUtils,
    ConfigDateUtils,
    ConfigNumericUtils,
    ConfigStringUtils,
    ConfigValidationUtils,
)


class TestConfigStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert ConfigStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert ConfigStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = ConfigStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert ConfigStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = ConfigStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestConfigDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = ConfigDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = ConfigDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = ConfigDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestConfigNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert ConfigNumericUtils.clamp(15, 0, 10) == 10
        assert ConfigNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert ConfigNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = ConfigNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestConfigCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(ConfigCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = ConfigCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = ConfigCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestConfigCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = ConfigCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = ConfigCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestConfigValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert ConfigValidationUtils.is_empty('')
        assert ConfigValidationUtils.is_empty([])
        assert not ConfigValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert ConfigValidationUtils.is_valid_json('{"key": "value"}')
        assert not ConfigValidationUtils.is_valid_json('invalid')
