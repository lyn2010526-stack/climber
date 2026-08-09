"""Dependency injection container and service locator.

This module provides a lightweight DI mechanism to break circular imports
and enable testability. All global singletons should be registered here
instead of being instantiated at module level.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

import structlog

logger = structlog.get_logger()

T = TypeVar("T")

# Global service locator instance
_container: dict[type[Any] | str, tuple[Callable[[], Any] | Any, bool]] = {}
_factories: dict[type[Any] | str, Callable[[], Any]] = {}
_scoped: dict[str, dict[type[Any] | str, Any]] = {}


def register(service_type: type[T] | str, factory: Callable[[], T] | T, singleton: bool = True) -> None:
    _container[service_type] = (factory, singleton)


def factory(service_type: type[T] | str, creator: Callable[[], T]) -> None:
    _factories[service_type] = creator


def resolve(service_type: type[T] | str) -> T:
    if service_type in _container:
        factory_or_instance, is_singleton = _container[service_type]
        if callable(factory_or_instance) and not is_singleton:
            return cast(T, factory_or_instance())
        if not callable(factory_or_instance):
            return cast(T, factory_or_instance)
        instance = factory_or_instance()
        if is_singleton:
            _container[service_type] = (instance, True)
        return cast(T, instance)
    if service_type in _factories:
        instance = _factories[service_type]()
        _container[service_type] = (instance, True)
        return cast(T, instance)
    raise KeyError(f"Service not registered: {service_type}")


def clear() -> None:
    _container.clear()
    _factories.clear()
    _scoped.clear()


def create_scope(scope_name: str) -> ScopeContext:
    return ScopeContext(scope_name)


class ScopeContext:
    def __init__(self, name: str) -> None:
        self.name = name
        self._saved: dict[type[Any] | str, tuple[Callable[[], Any] | Any, bool]] = {}

    def __enter__(self) -> ScopeContext:
        _scoped[self.name] = {}
        self._saved = dict(_container)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        _scoped.pop(self.name, None)
        _container.clear()
        _container.update(self._saved)


def get_scoped(scope_name: str, service_type: type[T] | str) -> T | None:
    scope = _scoped.get(scope_name)
    if scope is None:
        return None
    instance = scope.get(service_type)
    if instance is None:
        return None
    if callable(instance):
        return cast(T, instance())
    return cast(T, instance)


def set_scoped(scope_name: str, service_type: type[T] | str, instance: T) -> None:
    _scoped.setdefault(scope_name, {})[service_type] = instance
