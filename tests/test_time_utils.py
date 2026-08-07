"""Tests for time utility."""

from datetime import UTC, datetime, timedelta

from app.utils.time_utils import (
    TimeCollectionUtils,
    TimeCryptoUtils,
    TimeDateUtils,
    TimeNumericUtils,
    TimeStringUtils,
    TimeValidationUtils,
)


class TestTimeStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert TimeStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert TimeStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = TimeStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert TimeStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = TimeStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestTimeDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = TimeDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = TimeDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = TimeDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestTimeNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert TimeNumericUtils.clamp(15, 0, 10) == 10
        assert TimeNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert TimeNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = TimeNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestTimeCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(TimeCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = TimeCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = TimeCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestTimeCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = TimeCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = TimeCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestTimeValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert TimeValidationUtils.is_empty('')
        assert TimeValidationUtils.is_empty([])
        assert not TimeValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert TimeValidationUtils.is_valid_json('{"key": "value"}')
        assert not TimeValidationUtils.is_valid_json('invalid')
