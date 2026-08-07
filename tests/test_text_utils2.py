"""Tests for text utilities - part 2."""

from __future__ import annotations

from app.utils.text_utils import TextCollectionUtils, TextNumericUtils


class TestTextNumericUtils:
    """Tests for TextNumericUtils."""

    def test_clamp_within_range(self):
        assert TextNumericUtils.clamp(5, 0, 10) == 5

    def test_clamp_below_min(self):
        assert TextNumericUtils.clamp(-5, 0, 10) == 0

    def test_clamp_above_max(self):
        assert TextNumericUtils.clamp(15, 0, 10) == 10

    def test_lerp_start(self):
        assert TextNumericUtils.lerp(0, 10, 0) == 0

    def test_lerp_end(self):
        assert TextNumericUtils.lerp(0, 10, 1) == 10

    def test_lerp_mid(self):
        assert TextNumericUtils.lerp(0, 10, 0.5) == 5

    def test_percentage_normal(self):
        assert TextNumericUtils.percentage(25, 100) == 25.0

    def test_percentage_zero_total(self):
        assert TextNumericUtils.percentage(25, 0) == 0.0

    def test_percentage_over_100(self):
        assert TextNumericUtils.percentage(150, 100) == 150.0

    def test_round_decimal(self):
        result = TextNumericUtils.round_decimal(3.14159, 2)
        assert str(result) == "3.142"

    def test_round_decimal_up(self):
        result = TextNumericUtils.round_decimal(3.145, 2)
        assert str(result) == "3.145"

    def test_format_bytes_bytes(self):
        assert TextNumericUtils.format_bytes(500) == "500.0 B"

    def test_format_bytes_kb(self):
        assert "KB" in TextNumericUtils.format_bytes(1024)

    def test_format_bytes_mb(self):
        assert "MB" in TextNumericUtils.format_bytes(1024 * 1024)

    def test_format_bytes_gb(self):
        assert "GB" in TextNumericUtils.format_bytes(1024 * 1024 * 1024)

    def test_format_currency_usd(self):
        assert TextNumericUtils.format_currency(1234.56) == "$1,234.56"

    def test_format_currency_eur(self):
        result = TextNumericUtils.format_currency(100, "EUR")
        assert "100" in result

    def test_format_currency_gbp(self):
        result = TextNumericUtils.format_currency(100, "GBP")
        assert "100" in result

    def test_moving_average_basic(self):
        result = TextNumericUtils.moving_average([1, 2, 3, 4, 5], 3)
        assert result == [2, 3, 4]

    def test_moving_average_window_too_large(self):
        result = TextNumericUtils.moving_average([1, 2], 5)
        assert result == [1, 2]

    def test_moving_average_zero_window(self):
        result = TextNumericUtils.moving_average([1, 2, 3], 0)
        assert result == [1, 2, 3]


class TestTextCollectionUtils:
    """Tests for TextCollectionUtils."""

    def test_chunk_even(self):
        result = list(TextCollectionUtils.chunk([1, 2, 3, 4], 2))
        assert result == [[1, 2], [3, 4]]

    def test_chunk_odd(self):
        result = list(TextCollectionUtils.chunk([1, 2, 3], 2))
        assert result == [[1, 2], [3]]

    def test_chunk_single(self):
        result = list(TextCollectionUtils.chunk([1, 2, 3], 5))
        assert result == [[1, 2, 3]]

    def test_flatten(self):
        assert TextCollectionUtils.flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]

    def test_flatten_empty(self):
        assert TextCollectionUtils.flatten([]) == []

    def test_unique_no_key(self):
        assert TextCollectionUtils.unique([1, 2, 2, 3, 1]) == [1, 2, 3]

    def test_unique_with_key(self):
        items = [{"a": 1}, {"a": 2}, {"a": 1}]
        result = TextCollectionUtils.unique(items, key=lambda x: x["a"])
        assert result == [{"a": 1}, {"a": 2}]

    def test_unique_empty(self):
        assert TextCollectionUtils.unique([]) == []

    def test_group_by(self):
        items = [{"type": "a"}, {"type": "b"}, {"type": "a"}]
        result = TextCollectionUtils.group_by(items, key=lambda x: x["type"])
        assert result == {"a": [{"type": "a"}, {"type": "a"}], "b": [{"type": "b"}]}

    def test_group_by_empty(self):
        assert TextCollectionUtils.group_by([], key=lambda x: x) == {}

    def test_find_first_match(self):
        result = TextCollectionUtils.find_first([1, 2, 3, 4], lambda x: x > 2)
        assert result == 3

    def test_find_first_no_match(self):
        result = TextCollectionUtils.find_first([1, 2, 3], lambda x: x > 10)
        assert result is None

    def test_find_first_empty(self):
        result = TextCollectionUtils.find_first([], lambda x: True)
        assert result is None
