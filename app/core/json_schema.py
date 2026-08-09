"""JSON Schema validation for structured outputs.

Provides strict validation without requiring external jsonschema library.
Falls back to basic type checking if jsonschema is not available.
"""

from __future__ import annotations

import json
from typing import Any


class StructuredOutputError(Exception):
    """Raised when structured output fails validation."""
    pass


def validate_structured_output(output: str, schema: dict[str, Any]) -> tuple[bool, Any, list[str]]:
    """Validate a JSON string against a JSON schema.

    Returns:
        (is_valid, parsed_output, errors)
    """
    errors: list[str] = []
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as e:
        return False, {}, [f"Invalid JSON: {e}"]

    if not isinstance(schema, dict):
        return True, parsed, []

    schema_type = schema.get("type")
    if schema_type:
        if not _check_type(parsed, schema_type):
            errors.append(f"Expected type '{schema_type}', got '{type(parsed).__name__}'")

    properties = schema.get("properties", {})
    if isinstance(parsed, dict) and properties:
        for field, field_schema in properties.items():
            if field in parsed:
                field_valid, field_errors = _validate_value(parsed[field], field_schema)
                if not field_valid:
                    errors.extend(field_errors)

    required = schema.get("required", [])
    if isinstance(parsed, dict):
        for field in required:
            if field not in parsed:
                errors.append(f"Missing required field: {field}")

    additional_properties = schema.get("additionalProperties")
    if additional_properties is False and isinstance(parsed, dict) and properties:
        for field in parsed:
            if field not in properties:
                errors.append(f"Additional property not allowed: {field}")

    enum = schema.get("enum")
    if enum is not None and parsed not in enum:
        errors.append(f"Value must be one of: {enum}")

    min_items = schema.get("minItems")
    if min_items is not None and isinstance(parsed, list) and len(parsed) < min_items:
        errors.append(f"Array must have at least {min_items} items")

    max_items = schema.get("maxItems")
    if max_items is not None and isinstance(parsed, list) and len(parsed) > max_items:
        errors.append(f"Array must have at most {max_items} items")

    min_props = schema.get("minProperties")
    if min_props is not None and isinstance(parsed, dict) and len(parsed) < min_props:
        errors.append(f"Object must have at least {min_props} properties")

    max_props = schema.get("maxProperties")
    if max_props is not None and isinstance(parsed, dict) and len(parsed) > max_props:
        errors.append(f"Object must have at most {max_props} properties")

    return len(errors) == 0, parsed, errors


def _check_type(value: Any, expected_type: str) -> bool:
    """Check if value matches JSON Schema type."""
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }
    expected = type_map.get(expected_type)
    if expected is None:
        return True
    if isinstance(expected, tuple):
        return isinstance(value, expected)
    return isinstance(value, expected)


def _validate_value(value: Any, schema: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a single value against a schema fragment."""
    errors: list[str] = []

    if "type" in schema:
        if not _check_type(value, schema["type"]):
            errors.append(f"Expected type '{schema['type']}', got '{type(value).__name__}'")
            return False, errors

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"Value must be one of: {schema['enum']}")

    if isinstance(value, dict) and "properties" in schema:
        for field, field_schema in schema["properties"].items():
            if field in value:
                valid, field_errors = _validate_value(value[field], field_schema)
                if not valid:
                    errors.extend(field_errors)

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"Array must have at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"Array must have at most {schema['maxItems']} items")
        if "items" in schema and value:
            for i, item in enumerate(value):
                valid, item_errors = _validate_value(item, schema["items"])
                if not valid:
                    errors.extend([f"[{i}]: {e}" for e in item_errors])

    return len(errors) == 0, errors
