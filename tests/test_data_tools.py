"""Tests for data processing tools."""

import pytest

from app.tools.data_tools import DataTools


@pytest.fixture
def data_tools() -> DataTools:
    return DataTools()


class TestCSVParse:
    """Tests for CSV parsing."""

    def test_parse_simple_csv(self, data_tools):
        result = data_tools.parse_csv("a,b,c\n1,2,3\n4,5,6")
        assert len(result["data"]) == 2
        assert result["columns"] == ["a", "b", "c"]

    def test_parse_csv_no_header(self, data_tools):
        result = data_tools.parse_csv("1,2,3\n4,5,6", has_header=False)
        assert result["columns"] == ["col_0", "col_1", "col_2"]

    def test_parse_csv_custom_delimiter(self, data_tools):
        result = data_tools.parse_csv("a;b|c\n1;2;3", delimiter=";")
        assert result["columns"] == ["a", "b|c"]

    def test_parse_empty_csv(self, data_tools):
        result = data_tools.parse_csv("")
        assert result["total_rows"] == 0


class TestCSVGenerate:
    """Tests for CSV generation."""

    def test_generate_simple_csv(self, data_tools):
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        result = data_tools.generate_csv(data, columns=["name", "age"])
        assert "Alice" in result["csv"]
        assert result["total_rows"] == 2

    def test_generate_csv_auto_columns(self, data_tools):
        data = [{"a": 1, "b": 2}]
        result = data_tools.generate_csv(data)
        assert "a" in result["csv"]
        assert "b" in result["csv"]

    def test_generate_empty_csv(self, data_tools):
        result = data_tools.generate_csv([])
        assert result["total_rows"] == 0


class TestDataAnalysis:
    """Tests for statistical analysis."""

    def test_mean(self, data_tools):
        result = data_tools.analyze_data([1, 2, 3, 4, 5], ["mean"])
        assert result["mean"] == 3.0

    def test_median(self, data_tools):
        result = data_tools.analyze_data([1, 2, 3, 4, 5], ["median"])
        assert result["median"] == 3

    def test_std_deviation(self, data_tools):
        result = data_tools.analyze_data([1, 2, 3, 4, 5], ["std"])
        assert result["std"] > 0

    def test_min_max(self, data_tools):
        result = data_tools.analyze_data([1, 2, 3, 4, 5], ["min", "max"])
        assert result["min"] == 1
        assert result["max"] == 5

    def test_empty_data(self, data_tools):
        result = data_tools.analyze_data([])
        assert "error" in result

    def test_percentiles(self, data_tools):
        data = list(range(1, 101))
        result = data_tools.analyze_data(data, ["percentiles"])
        assert "p50" in result["percentiles"]
        assert "p95" in result["percentiles"]


class TestDataAggregation:
    """Tests for data aggregation."""

    def test_aggregate_by_group(self, data_tools):
        data = [
            {"dept": "eng", "salary": 100},
            {"dept": "eng", "salary": 150},
            {"dept": "sales", "salary": 80},
        ]
        result = data_tools.aggregate_data(data, "dept", {"salary": "sum"})
        assert len(result["groups"]) == 2

    def test_aggregate_empty_data(self, data_tools):
        result = data_tools.aggregate_data([], "key")
        assert result["total"] == 0


class TestDataFilter:
    """Tests for data filtering."""

    def test_filter_by_equality(self, data_tools):
        data = [{"status": "active"}, {"status": "inactive"}]
        result = data_tools.filter_data(data, {"status": "active"})
        assert result["total"] == 1

    def test_filter_by_comparison(self, data_tools):
        data = [{"age": 25}, {"age": 35}, {"age": 45}]
        result = data_tools.filter_data(data, {"age": {"gt": 30}})
        assert result["total"] == 2

    def test_filter_by_contains(self, data_tools):
        data = [{"name": "Alice"}, {"name": "Bob"}]
        result = data_tools.filter_data(data, {"name": {"contains": "li"}})
        assert result["total"] == 1


class TestDataSort:
    """Tests for data sorting."""

    def test_sort_ascending(self, data_tools):
        data = [{"val": 3}, {"val": 1}, {"val": 2}]
        result = data_tools.sort_data(data, ["val"], "asc")
        assert result["data"][0]["val"] == 1

    def test_sort_descending(self, data_tools):
        data = [{"val": 3}, {"val": 1}, {"val": 2}]
        result = data_tools.sort_data(data, ["val"], "desc")
        assert result["data"][0]["val"] == 3


class TestDataMerge:
    """Tests for data merging."""

    def test_inner_join(self, data_tools):
        left = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        right = [{"id": 1, "score": 100}, {"id": 3, "score": 50}]
        result = data_tools.merge_data(left, right, "id", "inner")
        assert result["total"] == 1

    def test_left_join(self, data_tools):
        left = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        right = [{"id": 1, "score": 100}]
        result = data_tools.merge_data(left, right, "id", "left")
        assert result["total"] == 2


class TestSchemaValidation:
    """Tests for JSON schema validation."""

    def test_valid_object(self, data_tools):
        schema = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}
        result = data_tools.validate_schema({"name": "test"}, schema)
        assert result["valid"] is True

    def test_missing_required_field(self, data_tools):
        schema = {"type": "object", "required": ["name"]}
        result = data_tools.validate_schema({}, schema)
        assert result["valid"] is False

    def test_wrong_type(self, data_tools):
        schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
        result = data_tools.validate_schema({"age": "not-a-number"}, schema)
        assert result["valid"] is False
