"""Tests for video utility."""

from datetime import UTC, datetime, timedelta

from app.utils.video_utils import (
    VideoCollectionUtils,
    VideoCryptoUtils,
    VideoDateUtils,
    VideoNumericUtils,
    VideoStringUtils,
    VideoValidationUtils,
)


class TestVideoStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert VideoStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert VideoStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = VideoStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert VideoStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = VideoStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestVideoDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = VideoDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = VideoDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = VideoDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestVideoNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert VideoNumericUtils.clamp(15, 0, 10) == 10
        assert VideoNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert VideoNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = VideoNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestVideoCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(VideoCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = VideoCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = VideoCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestVideoCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = VideoCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = VideoCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestVideoValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert VideoValidationUtils.is_empty('')
        assert VideoValidationUtils.is_empty([])
        assert not VideoValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert VideoValidationUtils.is_valid_json('{"key": "value"}')
        assert not VideoValidationUtils.is_valid_json('invalid')
