"""Tests for file utility."""

from datetime import UTC, datetime, timedelta

from app.utils.file_utils import (
    FileCollectionUtils,
    FileCryptoUtils,
    FileDateUtils,
    FileNumericUtils,
    FileStringUtils,
    FileValidationUtils,
)


class TestFileStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert FileStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert FileStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = FileStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert FileStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = FileStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestFileDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = FileDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = FileDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = FileDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestFileNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert FileNumericUtils.clamp(15, 0, 10) == 10
        assert FileNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert FileNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = FileNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestFileCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(FileCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = FileCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = FileCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestFileCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = FileCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = FileCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestFileValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert FileValidationUtils.is_empty('')
        assert FileValidationUtils.is_empty([])
        assert not FileValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert FileValidationUtils.is_valid_json('{"key": "value"}')
        assert not FileValidationUtils.is_valid_json('invalid')
