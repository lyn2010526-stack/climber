"""Data processing and analysis tools."""

from __future__ import annotations

import csv
import io
import statistics
from typing import Any

import structlog

from app.tools import ToolRegistry

logger = structlog.get_logger()


class DataTools:
    """Data processing, transformation, and analysis tools."""

    def register(self, registry: ToolRegistry) -> None:
        """Register all data tools."""
        registry.register(
            name="data_parse_csv",
            description="Parse CSV data into structured format",
            parameters={
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "CSV data string"},
                    "delimiter": {"type": "string", "description": "Column delimiter (default: comma)"},
                    "has_header": {"type": "boolean", "description": "First row is header"},
                },
                "required": ["data"],
            },
            func=self.parse_csv,
        )
        registry.register(
            name="data_generate_csv",
            description="Generate CSV from structured data",
            parameters={
                "type": "object",
                "properties": {
                    "data": {"type": "array", "items": {"type": "object"}, "description": "Array of objects"},
                    "columns": {"type": "array", "items": {"type": "string"}, "description": "Column names"},
                    "delimiter": {"type": "string", "description": "Column delimiter"},
                },
                "required": ["data"],
            },
            func=self.generate_csv,
        )
        registry.register(
            name="data_transform_json",
            description="Transform JSON data with mapping rules",
            parameters={
                "type": "object",
                "properties": {
                    "data": {"type": "object", "description": "Input JSON data"},
                    "mapping": {"type": "object", "description": "Field mapping rules"},
                    "filter": {"type": "string", "description": "Optional filter expression"},
                },
                "required": ["data", "mapping"],
            },
            func=self.transform_json,
        )
        registry.register(
            name="data_analyze",
            description="Perform statistical analysis on numeric data",
            parameters={
                "type": "object",
                "properties": {
                    "data": {"type": "array", "items": {"type": "number"}, "description": "Numeric data array"},
                    "operations": {"type": "array", "items": {"type": "string"}, "description": "Analysis operations to perform"},
                },
                "required": ["data"],
            },
            func=self.analyze_data,
        )
        registry.register(
            name="data_aggregate",
            description="Aggregate data by groups",
            parameters={
                "type": "object",
                "properties": {
                    "data": {"type": "array", "items": {"type": "object"}},
                    "group_by": {"type": "string", "description": "Field to group by"},
                    "aggregations": {"type": "object", "description": "Aggregation functions per field"},
                },
                "required": ["data", "group_by"],
            },
            func=self.aggregate_data,
        )
        registry.register(
            name="data_filter",
            description="Filter data by conditions",
            parameters={
                "type": "object",
                "properties": {
                    "data": {"type": "array", "items": {"type": "object"}},
                    "conditions": {"type": "object", "description": "Filter conditions"},
                    "operator": {"type": "string", "description": "AND or OR"},
                },
                "required": ["data", "conditions"],
            },
            func=self.filter_data,
        )
        registry.register(
            name="data_sort",
            description="Sort data by fields",
            parameters={
                "type": "object",
                "properties": {
                    "data": {"type": "array", "items": {"type": "object"}},
                    "fields": {"type": "array", "items": {"type": "string"}, "description": "Fields to sort by"},
                    "direction": {"type": "string", "description": "asc or desc"},
                },
                "required": ["data", "fields"],
            },
            func=self.sort_data,
        )
        registry.register(
            name="data_merge",
            description="Merge two datasets",
            parameters={
                "type": "object",
                "properties": {
                    "left": {"type": "array", "items": {"type": "object"}},
                    "right": {"type": "array", "items": {"type": "object"}},
                    "join_key": {"type": "string", "description": "Key to join on"},
                    "join_type": {"type": "string", "description": "inner, left, right, outer"},
                },
                "required": ["left", "right", "join_key"],
            },
            func=self.merge_data,
        )
        registry.register(
            name="data_validate_schema",
            description="Validate data against a JSON schema",
            parameters={
                "type": "object",
                "properties": {
                    "data": {"type": "object", "description": "Data to validate"},
                    "schema": {"type": "object", "description": "JSON schema"},
                    "strict": {"type": "boolean", "description": "Strict validation mode"},
                },
                "required": ["data", "schema"],
            },
            func=self.validate_schema,
        )

    def parse_csv(self, data: str, delimiter: str = ",", has_header: bool = True) -> dict:
        """Parse CSV data into list of dicts."""
        reader = csv.reader(io.StringIO(data), delimiter=delimiter)
        rows = list(reader)

        if not rows:
            return {"data": [], "columns": [], "total_rows": 0}

        if has_header:
            columns = rows[0]
            data_rows = [dict(zip(columns, row, strict=False)) for row in rows[1:]]
        else:
            columns = [f"col_{i}" for i in range(len(rows[0]))]
            data_rows = [dict(zip(columns, row, strict=False)) for row in rows]

        return {
            "data": data_rows,
            "columns": columns,
            "total_rows": len(data_rows),
        }

    def generate_csv(self, data: list[dict], columns: list[str] | None = None, delimiter: str = ",") -> dict:
        """Generate CSV from structured data."""
        if not data:
            return {"csv": "", "columns": [], "total_rows": 0}

        if not columns:
            columns = list(data[0].keys())

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns, delimiter=delimiter, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)

        return {
            "csv": output.getvalue(),
            "columns": columns,
            "total_rows": len(data),
        }

    def transform_json(self, data: Any, mapping: dict[str, str], filter_expr: str | None = None) -> dict:
        """Transform JSON data using field mapping."""
        if isinstance(data, list):
            return {"result": [self._transform_item(item, mapping) for item in data]}
        return {"result": self._transform_item(data, mapping)}

    def _transform_item(self, item: dict, mapping: dict[str, str]) -> dict:
        """Apply field mapping to a single item."""
        result = {}
        for new_key, old_key in mapping.items():
            if old_key in item:
                result[new_key] = item[old_key]
        return result

    def analyze_data(self, data: list[float], operations: list[str] | None = None) -> dict:
        """Perform statistical analysis on numeric data."""
        if not data:
            return {"error": "Empty data"}

        operations = operations or ["mean", "median", "std", "min", "max", "count"]
        result = {"count": len(data)}

        if "mean" in operations:
            result["mean"] = statistics.mean(data)
        if "median" in operations:
            result["median"] = statistics.median(data)
        if "std" in operations:
            result["std"] = statistics.stdev(data) if len(data) > 1 else 0
        if "min" in operations:
            result["min"] = min(data)
        if "max" in operations:
            result["max"] = max(data)
        if "sum" in operations:
            result["sum"] = sum(data)
        if "variance" in operations:
            result["variance"] = statistics.variance(data) if len(data) > 1 else 0
        if "percentiles" in operations:
            sorted_data = sorted(data)
            n = len(sorted_data)
            result["percentiles"] = {
                "p25": sorted_data[n // 4],
                "p50": sorted_data[n // 2],
                "p75": sorted_data[3 * n // 4],
                "p90": sorted_data[int(n * 0.9)],
                "p95": sorted_data[int(n * 0.95)],
            }
        if "mode" in operations:
            result["mode"] = statistics.mode(data) if len(set(data)) < len(data) else None
        if "histogram" in operations:
            bins = 10
            min_val, max_val = min(data), max(data)
            if min_val == max_val:
                result["histogram"] = {"bins": [min_val], "counts": [len(data)]}
            else:
                bin_width = (max_val - min_val) / bins
                histogram_counts = [0] * bins
                for val in data:
                    idx = min(int((val - min_val) / bin_width), bins - 1)
                    histogram_counts[idx] += 1
                result["histogram"] = {
                    "bins": [min_val + i * bin_width for i in range(bins + 1)],
                    "counts": histogram_counts,
                }

        return result

    def aggregate_data(self, data: list[dict], group_by: str, aggregations: dict[str, str] | None = None) -> dict:
        """Aggregate data by groups."""
        if not data:
            return {"groups": [], "total": 0}

        groups: dict[str, list[dict]] = {}
        for item in data:
            key = str(item.get(group_by, "unknown"))
            groups.setdefault(key, []).append(item)

        result = []
        for key, items in sorted(groups.items()):
            group_result = {group_by: key, "count": len(items)}

            if aggregations:
                for field, func in aggregations.items():
                    values = [item.get(field, 0) for item in items if isinstance(item.get(field), (int, float))]
                    if values:
                        if func == "sum":
                            group_result[f"{field}_sum"] = sum(values)
                        elif func == "avg":
                            group_result[f"{field}_avg"] = sum(values) / len(values)
                        elif func == "min":
                            group_result[f"{field}_min"] = min(values)
                        elif func == "max":
                            group_result[f"{field}_max"] = max(values)
                        elif func == "count":
                            group_result[f"{field}_count"] = len(values)

            result.append(group_result)

        return {"groups": result, "total": len(data)}

    def filter_data(self, data: list[dict], conditions: dict[str, Any], operator: str = "AND") -> dict:
        """Filter data by conditions."""
        def matches(item: dict) -> bool:
            results = []
            for key, value in conditions.items():
                item_val = item.get(key)
                if isinstance(value, dict):
                    if "eq" in value:
                        results.append(item_val == value["eq"])
                    elif "ne" in value:
                        results.append(item_val != value["ne"])
                    elif "gt" in value:
                        results.append(item_val is not None and item_val > value["gt"])
                    elif "lt" in value:
                        results.append(item_val is not None and item_val < value["lt"])
                    elif "gte" in value:
                        results.append(item_val is not None and item_val >= value["gte"])
                    elif "lte" in value:
                        results.append(item_val is not None and item_val <= value["lte"])
                    elif "in" in value:
                        results.append(item_val in value["in"])
                    elif "contains" in value:
                        results.append(item_val is not None and str(value["contains"]) in str(item_val))
                else:
                    results.append(item_val == value)

            return all(results) if operator == "AND" else any(results)

        filtered = [item for item in data if matches(item)]
        return {"data": filtered, "total": len(filtered), "filtered_from": len(data)}

    def sort_data(self, data: list[dict], fields: list[str], direction: str = "asc") -> dict:
        """Sort data by fields."""
        reverse = direction == "desc"

        def sort_key(item: dict):
            return tuple(item.get(f) for f in fields)

        sorted_data = sorted(data, key=sort_key, reverse=reverse)
        return {"data": sorted_data, "total": len(sorted_data)}

    def merge_data(self, left: list[dict], right: list[dict], join_key: str, join_type: str = "inner") -> dict:
        """Merge two datasets."""
        right_index = {}
        for item in right:
            key = item.get(join_key)
            if key is not None:
                right_index.setdefault(key, []).append(item)

        result = []
        for left_item in left:
            key = left_item.get(join_key)
            right_matches = right_index.get(key, [])

            if right_matches:
                for right_item in right_matches:
                    merged = {**left_item, **right_item}
                    result.append(merged)
            elif join_type in ("left", "outer"):
                result.append(left_item)

        if join_type == "outer":
            left_keys = {item.get(join_key) for item in left}
            for right_item in right:
                if right_item.get(join_key) not in left_keys:
                    result.append(right_item)

        return {"data": result, "total": len(result)}

    def validate_schema(self, data: Any, schema: dict, strict: bool = False) -> dict:
        """Validate data against JSON schema."""
        errors = []

        def validate(value: Any, expected_type: str, path: str = "$") -> None:
            type_map = {
                "string": str,
                "number": (int, float),
                "integer": int,
                "boolean": bool,
                "array": list,
                "object": dict,
                "null": type(None),
            }
            python_type = type_map.get(expected_type)
            if python_type and not isinstance(value, python_type):
                errors.append(f"{path}: expected {expected_type}, got {type(value).__name__}")

        if "type" in schema:
            validate(data, schema["type"])

        if schema.get("type") == "object" and isinstance(data, dict):
            if "required" in schema:
                for field in schema["required"]:
                    if field not in data:
                        errors.append(f"$.{field}: required field missing")
            if "properties" in schema and isinstance(schema["properties"], dict):
                for prop, prop_schema in schema["properties"].items():
                    if prop in data:
                        validate(data[prop], prop_schema.get("type", "any"), f"$.{prop}")
                    elif strict and "default" not in prop_schema:
                        errors.append(f"$.{prop}: missing in strict mode")

        if schema.get("type") == "array" and isinstance(data, list):
            if "minItems" in schema and len(data) < schema["minItems"]:
                errors.append(f"$: array too short (min {schema['minItems']})")
            if "maxItems" in schema and len(data) > schema["maxItems"]:
                errors.append(f"$: array too long (max {schema['maxItems']})")
            if "items" in schema:
                for i, item in enumerate(data):
                    validate(item, schema["items"].get("type", "any"), f"$[{i}]")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
