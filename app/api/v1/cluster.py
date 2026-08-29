"""Compatibility import for the consolidated cluster API."""

from app.api.v1.cluster_api import router

__all__ = ["router"]
