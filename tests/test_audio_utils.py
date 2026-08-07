"""Tests for audio utility."""

from datetime import UTC, datetime, timedelta

from app.utils.audio_utils import (
    AudioCollectionUtils,
    AudioCryptoUtils,
    AudioDateUtils,
    AudioNumericUtils,
    AudioStringUtils,
    AudioValidationUtils,
)


class TestAudioStringUtils:
    """Tests for string utils."""

    def test_camel_to_snake(self):
        assert AudioStringUtils.camel_to_snake('camelCase') == 'camel_case'

    def test_snake_to_camel(self):
        assert AudioStringUtils.snake_to_camel('snake_case') == 'snakeCase'

    def test_truncate(self):
        result = AudioStringUtils.truncate('Hello World', 8)
        assert len(result) == 8

    def test_slugify(self):
        assert AudioStringUtils.slugify('Hello World!') == 'hello-world'

    def test_mask_email(self):
        result = AudioStringUtils.mask_email('test@example.com')
        assert '***' in result


class TestAudioDateUtils:
    """Tests for date utils."""

    def test_now_utc(self):
        dt = AudioDateUtils.now_utc()
        assert dt.tzinfo is not None

    def test_start_of_day(self):
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        start = AudioDateUtils.start_of_day(dt)
        assert start.hour == 0

    def test_humanize_delta(self):
        result = AudioDateUtils.humanize_delta(timedelta(hours=2))
        assert 'h ago' in result


class TestAudioNumericUtils:
    """Tests for numeric utils."""

    def test_clamp(self):
        assert AudioNumericUtils.clamp(15, 0, 10) == 10
        assert AudioNumericUtils.clamp(-5, 0, 10) == 0

    def test_percentage(self):
        assert AudioNumericUtils.percentage(25, 100) == 25.0

    def test_format_bytes(self):
        result = AudioNumericUtils.format_bytes(1024)
        assert 'KB' in result


class TestAudioCollectionUtils:
    """Tests for collection utils."""

    def test_chunk(self):
        result = list(AudioCollectionUtils.chunk([1, 2, 3, 4, 5], 2))
        assert len(result) == 3

    def test_flatten(self):
        result = AudioCollectionUtils.flatten([[1, 2], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_unique(self):
        result = AudioCollectionUtils.unique([1, 2, 2, 3, 3, 3])
        assert result == [1, 2, 3]


class TestAudioCryptoUtils:
    """Tests for crypto utils."""

    def test_generate_uuid(self):
        result = AudioCryptoUtils.generate_uuid()
        assert len(result) == 36

    def test_hash_sha256(self):
        result = AudioCryptoUtils.hash_sha256('test')
        assert len(result) == 64


class TestAudioValidationUtils:
    """Tests for validation utils."""

    def test_is_empty(self):
        assert AudioValidationUtils.is_empty('')
        assert AudioValidationUtils.is_empty([])
        assert not AudioValidationUtils.is_empty('test')

    def test_is_valid_json(self):
        assert AudioValidationUtils.is_valid_json('{"key": "value"}')
        assert not AudioValidationUtils.is_valid_json('invalid')
