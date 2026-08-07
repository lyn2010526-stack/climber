"""Tests for statistics utility."""

from datetime import UTC, datetime, timedelta

from app.utils.statistics_utils import (
    StatisticsCollectionUtils,
    StatisticsCryptoUtils,
    StatisticsDateUtils,
    StatisticsNumericUtils,
    StatisticsStringUtils,
    StatisticsValidationUtils,
)


class TestStatisticsStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert StatisticsStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert StatisticsStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = StatisticsStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert StatisticsStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = StatisticsStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestStatisticsDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = StatisticsDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = StatisticsDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = StatisticsDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestStatisticsNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert StatisticsNumericUtils.clamp(15, 0, 10) == 10
        assert StatisticsNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert StatisticsNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = StatisticsNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestStatisticsCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(StatisticsCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = StatisticsCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = StatisticsCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestStatisticsCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = StatisticsCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = StatisticsCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestStatisticsValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert StatisticsValidationUtils.is_empty('')
        assert StatisticsValidationUtils.is_empty([])
        assert not StatisticsValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert StatisticsValidationUtils.is_valid_json('{"key": "value"}')
        assert not StatisticsValidationUtils.is_valid_json('invalid')
