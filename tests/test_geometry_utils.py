"""Tests for geometry utility."""

from datetime import UTC, datetime, timedelta

from app.utils.geometry_utils import (
    GeometryCollectionUtils,
    GeometryCryptoUtils,
    GeometryDateUtils,
    GeometryNumericUtils,
    GeometryStringUtils,
    GeometryValidationUtils,
)


class TestGeometryStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert GeometryStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert GeometryStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = GeometryStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert GeometryStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = GeometryStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestGeometryDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = GeometryDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = GeometryDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = GeometryDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestGeometryNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert GeometryNumericUtils.clamp(15, 0, 10) == 10
        assert GeometryNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert GeometryNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = GeometryNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestGeometryCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(GeometryCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = GeometryCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = GeometryCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestGeometryCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = GeometryCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = GeometryCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestGeometryValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert GeometryValidationUtils.is_empty('')
        assert GeometryValidationUtils.is_empty([])
        assert not GeometryValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert GeometryValidationUtils.is_valid_json('{"key": "value"}')
        assert not GeometryValidationUtils.is_valid_json('invalid')
