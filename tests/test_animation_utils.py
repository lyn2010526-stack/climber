"""Tests for animation utility."""

from datetime import UTC, datetime, timedelta

from app.utils.animation_utils import (
    AnimationCollectionUtils,
    AnimationCryptoUtils,
    AnimationDateUtils,
    AnimationNumericUtils,
    AnimationStringUtils,
    AnimationValidationUtils,
)


class TestAnimationStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert AnimationStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert AnimationStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = AnimationStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert AnimationStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = AnimationStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestAnimationDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = AnimationDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = AnimationDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = AnimationDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestAnimationNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert AnimationNumericUtils.clamp(15, 0, 10) == 10
        assert AnimationNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert AnimationNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = AnimationNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestAnimationCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(AnimationCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = AnimationCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = AnimationCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestAnimationCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = AnimationCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = AnimationCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestAnimationValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert AnimationValidationUtils.is_empty('')
        assert AnimationValidationUtils.is_empty([])
        assert not AnimationValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert AnimationValidationUtils.is_valid_json('{"key": "value"}')
        assert not AnimationValidationUtils.is_valid_json('invalid')
