"""Channel abstractions for StateGraph.

"""

from __future__ import annotations

from typing import Any


class Channel:
    """Base channel for state graph."""

    def __init__(self, key: str, default: Any = None):
        self.key = key
        self.default = default
        self._value = default

    def get(self) -> Any:
        return self._value

    def set(self, value: Any) -> None:
        self._value = value

    def update(self, value: Any) -> Any:
        raise NotImplementedError

    def reset(self) -> None:
        self._value = self.default


class LastValue(Channel):
    """Channel that keeps the latest value (default behavior)."""

    def update(self, value: Any) -> Any:
        self._value = value
        return value


class BinaryOperator(Channel):
    """Channel that aggregates values using a binary operator."""

    def __init__(self, key: str, default: Any = None, operator: Any = None):
        super().__init__(key, default)
        self.operator = operator or (lambda a, b: b)

    def update(self, value: Any) -> Any:
        if self._value is None:
            self._value = value
        else:
            self._value = self.operator(self._value, value)
        return self._value


class DeltaChannel(Channel):
    """Channel that accumulates deltas (incremental updates).

    """

    def __init__(self, key: str, default: Any = None):
        super().__init__(key, default if default is not None else [])

    def update(self, value: Any) -> Any:
        if isinstance(self._value, list):
            if isinstance(value, list):
                self._value.extend(value)
            else:
                self._value.append(value)
        elif isinstance(self._value, dict) and isinstance(value, dict):
            self._value = {**self._value, **value}
        else:
            self._value = value
        return self._value

    def get(self) -> Any:
        return self._value
