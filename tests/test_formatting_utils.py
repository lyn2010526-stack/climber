"""Tests for formatting utility."""

from datetime import UTC, datetime, timedelta

from app.utils.formatting_utils import (
    FormattingCollectionUtils,
    FormattingCryptoUtils,
    FormattingDateUtils,
    FormattingNumericUtils,
    FormattingStringUtils,
    FormattingValidationUtils,
)


class TestFormattingStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert FormattingStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert FormattingStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = FormattingStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert FormattingStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = FormattingStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestFormattingDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = FormattingDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = FormattingDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = FormattingDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestFormattingNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert FormattingNumericUtils.clamp(15, 0, 10) == 10
        assert FormattingNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert FormattingNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = FormattingNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestFormattingCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(FormattingCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = FormattingCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = FormattingCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestFormattingCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = FormattingCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = FormattingCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestFormattingValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert FormattingValidationUtils.is_empty('')
        assert FormattingValidationUtils.is_empty([])
        assert not FormattingValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert FormattingValidationUtils.is_valid_json('{"key": "value"}')
        assert not FormattingValidationUtils.is_valid_json('invalid')
