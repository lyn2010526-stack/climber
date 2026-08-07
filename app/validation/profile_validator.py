"""Validation: profile."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

T = TypeVar('T')


@dataclass
class ProfileValidationError:
    """Validation error."""
    field: str
    message: str
    code: str = 'invalid'


@dataclass
class ProfileValidationResult:
    """Validation result."""
    valid: bool = True
    errors: list[ProfileValidationError] = field(default_factory=list)

    def add_error(self, field: str, message: str, code: str = 'invalid') -> None:
        self.valid = False
        self.errors.append(ProfileValidationError(field=field, message=message, code=code))


class ProfileValidator:
    """Validator."""

    def __init__(self):
        self._rules: dict[str, list[Callable]] = {}
        self._custom_validators: list[Callable] = []

    def add_rule(self, field: str, rule: Callable) -> None:
        """Add rule."""
        if field not in self._rules:
            self._rules[field] = []
        self._rules[field].append(rule)

    def add_custom(self, validator: Callable) -> None:
        """Add custom validator."""
        self._custom_validators.append(validator)

    def validate(self, data: dict[str, Any]) -> ProfileValidationResult:
        """Validate data."""
        result = ProfileValidationResult()
        for field, rules in self._rules.items():
            value = data.get(field)
            for rule in rules:
                error = rule(field, value)
                if error:
                    result.add_error(field, error)
                    break
        for validator in self._custom_validators:
            validator(data, result)
        return result


class ProfileFieldValidator:
    """Field validator."""

    @staticmethod
    def required(field: str, value: Any) -> str | None:
        """Check required."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return f'{field} is required'
        return None

    @staticmethod
    def min_length(min_len: int) -> Callable:
        """Min length check."""
        def check(field: str, value: Any) -> str | None:
            if value is not None and isinstance(value, str) and len(value) < min_len:
                return f'{field} must be at least {min_len} characters'
            return None
        return check

    @staticmethod
    def max_length(max_len: int) -> Callable:
        """Max length check."""
        def check(field: str, value: Any) -> str | None:
            if value is not None and isinstance(value, str) and len(value) > max_len:
                return f'{field} must be at most {max_len} characters'
            return None
        return check

    @staticmethod
    def pattern(regex: str, message: str = 'Invalid format') -> Callable:
        """Pattern check."""
        compiled = re.compile(regex)
        def check(field: str, value: Any) -> str | None:
            if value is not None and isinstance(value, str) and not compiled.match(value):
                return f'{field} {message}'
            return None
        return check

    @staticmethod
    def email(field: str, value: Any) -> str | None:
        """Email check."""
        if value is None:
            return None
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, value):
            return f'{field} must be a valid email'
        return None

    @staticmethod
    def range(min_val: float, max_val: float) -> Callable:
        """Range check."""
        def check(field: str, value: Any) -> str | None:
            if value is not None and isinstance(value, (int, float)):
                if value < min_val or value > max_val:
                    return f'{field} must be between {min_val} and {max_val}'
            return None
        return check
