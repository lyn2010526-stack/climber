"""Tests for map utility."""

from datetime import UTC, datetime, timedelta

from app.utils.map_utils import (
    MapCollectionUtils,
    MapCryptoUtils,
    MapDateUtils,
    MapNumericUtils,
    MapStringUtils,
    MapValidationUtils,
)


class TestMapStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert MapStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert MapStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = MapStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert MapStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = MapStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestMapDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = MapDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = MapDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = MapDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestMapNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert MapNumericUtils.clamp(15, 0, 10) == 10
        assert MapNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert MapNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = MapNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestMapCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(MapCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = MapCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = MapCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestMapCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = MapCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = MapCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestMapValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert MapValidationUtils.is_empty('')
        assert MapValidationUtils.is_empty([])
        assert not MapValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert MapValidationUtils.is_valid_json('{"key": "value"}')
        assert not MapValidationUtils.is_valid_json('invalid')
