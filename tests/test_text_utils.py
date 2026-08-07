"""Tests for text utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.utils.text_utils import TextDateUtils, TextStringUtils


class TestTextStringUtils:
    """Tests for TextStringUtils."""

    def test_camel_to_snake_simple(self):
        assert TextStringUtils.camel_to_snake("camelCase") == "camel_case"

    def test_camel_to_snake_multiple(self):
        assert TextStringUtils.camel_to_snake("MyClassName") == "my_class_name"

    def test_camel_to_snake_consecutive_upper(self):
        assert TextStringUtils.camel_to_snake("HTMLParser") == "html_parser"

    def test_snake_to_camel(self):
        assert TextStringUtils.snake_to_camel("snake_case") == "snakeCase"

    def test_snake_to_camel_multiple(self):
        assert TextStringUtils.snake_to_camel("my_long_variable_name") == "myLongVariableName"

    def test_kebab_to_camel(self):
        assert TextStringUtils.kebab_to_camel("kebab-case") == "kebabCase"

    def test_truncate_short_text(self):
        assert TextStringUtils.truncate("hello", 10) == "hello"

    def test_truncate_long_text(self):
        result = TextStringUtils.truncate("hello world", 8)
        assert result == "hello..."

    def test_truncate_custom_suffix(self):
        result = TextStringUtils.truncate("hello world", 8, suffix="..")
        assert result == "hello .."

    def test_slugify(self):
        assert TextStringUtils.slugify("Hello World!") == "hello-world"

    def test_slugify_special_chars(self):
        assert TextStringUtils.slugify("Test @#$ String") == "test-string"

    def test_strip_whitespace(self):
        assert TextStringUtils.strip_whitespace("  hello   world  ") == "hello world"

    def test_mask_email_short(self):
        assert TextStringUtils.mask_email("ab@test.com") == "a***@test.com"

    def test_mask_email_long(self):
        result = TextStringUtils.mask_email("alice@test.com")
        assert result == "a***e@test.com"

    def test_mask_email_no_at(self):
        assert TextStringUtils.mask_email("invalid") == "invalid"

    def test_mask_phone_short(self):
        assert TextStringUtils.mask_phone("123") == "***"

    def test_mask_phone_long(self):
        result = TextStringUtils.mask_phone("1234567890")
        assert result == "******7890"

    def test_pluralize_singular(self):
        assert TextStringUtils.pluralize(1, "item") == "1 item"

    def test_pluralize_plural(self):
        assert TextStringUtils.pluralize(5, "item") == "5 items"

    def test_pluralize_custom_plural(self):
        assert TextStringUtils.pluralize(2, "person", "people") == "2 people"


class TestTextDateUtils:
    """Tests for TextDateUtils."""

    def test_now_utc(self):
        result = TextDateUtils.now_utc()
        assert result.tzinfo == UTC

    def test_start_of_day(self):
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC)
        result = TextDateUtils.start_of_day(dt)
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_start_of_day_default(self):
        result = TextDateUtils.start_of_day()
        assert result.hour == 0

    def test_end_of_day(self):
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC)
        result = TextDateUtils.end_of_day(dt)
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59

    def test_start_of_week(self):
        dt = datetime(2024, 6, 12, 14, 0, 0, tzinfo=UTC)
        result = TextDateUtils.start_of_week(dt)
        assert result.weekday() == 0

    def test_end_of_week(self):
        dt = datetime(2024, 6, 12, 14, 0, 0, tzinfo=UTC)
        result = TextDateUtils.end_of_week(dt)
        assert result.weekday() == 6

    def test_start_of_month(self):
        dt = datetime(2024, 6, 15, 14, 0, 0, tzinfo=UTC)
        result = TextDateUtils.start_of_month(dt)
        assert result.day == 1
        assert result.hour == 0

    def test_end_of_month_june(self):
        dt = datetime(2024, 6, 15, 14, 0, 0, tzinfo=UTC)
        result = TextDateUtils.end_of_month(dt)
        assert result.day == 30

    def test_end_of_month_january(self):
        dt = datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC)
        result = TextDateUtils.end_of_month(dt)
        assert result.day == 31

    def test_end_of_month_february_leap(self):
        dt = datetime(2024, 2, 15, 14, 0, 0, tzinfo=UTC)
        result = TextDateUtils.end_of_month(dt)
        assert result.day == 29

    def test_humanize_delta_seconds(self):
        delta = timedelta(seconds=30)
        assert TextDateUtils.humanize_delta(delta) == "30s ago"

    def test_humanize_delta_minutes(self):
        delta = timedelta(minutes=5)
        assert TextDateUtils.humanize_delta(delta) == "5m ago"

    def test_humanize_delta_hours(self):
        delta = timedelta(hours=3)
        assert TextDateUtils.humanize_delta(delta) == "3h ago"

    def test_humanize_delta_days(self):
        delta = timedelta(days=2)
        assert TextDateUtils.humanize_delta(delta) == "2d ago"

    def test_parse_iso(self):
        result = TextDateUtils.parse_iso("2024-06-15T14:30:00")
        assert result is not None
        assert result.year == 2024

    def test_parse_iso_with_z(self):
        result = TextDateUtils.parse_iso("2024-06-15T14:30:00Z")
        assert result is not None

    def test_parse_iso_invalid(self):
        result = TextDateUtils.parse_iso("invalid")
        assert result is None
