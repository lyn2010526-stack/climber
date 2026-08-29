"""Compatibility import for the consolidated tasks API."""

from app.api.v1.tasks_api import router

__all__ = ["router"]
