"""Tests for image utility."""

from datetime import UTC, datetime, timedelta

from app.utils.image_utils import (
    ImageCollectionUtils,
    ImageCryptoUtils,
    ImageDateUtils,
    ImageNumericUtils,
    ImageStringUtils,
    ImageValidationUtils,
)


class TestImageStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert ImageStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert ImageStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = ImageStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert ImageStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = ImageStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestImageDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = ImageDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = ImageDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = ImageDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestImageNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert ImageNumericUtils.clamp(15, 0, 10) == 10
        assert ImageNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert ImageNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = ImageNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestImageCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(ImageCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = ImageCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = ImageCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestImageCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = ImageCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = ImageCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestImageValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert ImageValidationUtils.is_empty('')
        assert ImageValidationUtils.is_empty([])
        assert not ImageValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert ImageValidationUtils.is_valid_json('{"key": "value"}')
        assert not ImageValidationUtils.is_valid_json('invalid')
