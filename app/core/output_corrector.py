"""Model output correction.

"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class ModelOutputCorrector:
    """Auto-correct model invalid output.

    """

    def __init__(self, max_attempts: int = 2):
        self._max_attempts = max_attempts

    def correct(self, raw_output: str, expected_schema: dict[str, Any]) -> tuple[str, bool]:
        """Try to correct raw output to match expected schema.

        Returns (corrected_output, success).
        """
        for _ in range(self._max_attempts):
            corrected = self._try_fix(raw_output, expected_schema)
            if self._validate_schema(corrected, expected_schema):
                return corrected, True
            raw_output = corrected
        return raw_output, False

    def _try_fix(self, raw: str, schema: dict[str, Any]) -> str:
        stripped = raw.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 2:
                stripped = "\n".join(lines[1:])
            if stripped.endswith("```"):
                stripped = "\n".join(stripped.splitlines()[:-1])
            stripped = stripped.strip()
        if schema.get("type") == "object":
            try:
                parsed = json.loads(stripped)
                return json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError:
                pass
            match = re.search(r"\{.*\}", stripped, re.DOTALL)
            if match:
                return match.group(0)
        return stripped

    def _validate_schema(self, output: str, schema: dict[str, Any]) -> bool:
        if schema.get("type") != "object":
            return True
        try:
            data = json.loads(output)
            if not isinstance(data, dict):
                return False
            for prop, rules in schema.get("properties", {}).items():
                if prop in data:
                    if not self._validate_value(data[prop], rules):
                        return False
            return True
        except (json.JSONDecodeError, TypeError):
            return False

    def _validate_value(self, value: Any, rules: dict[str, Any]) -> bool:
        expected = rules.get("type")
        if expected == "string" and not isinstance(value, str):
            return False
        if expected == "array" and not isinstance(value, list):
            return False
        if expected == "object" and not isinstance(value, dict):
            return False
        if expected == "number" and not isinstance(value, (int, float)):
            return False
        return True


model_output_corrector = ModelOutputCorrector()
