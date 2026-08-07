"""Plugin Market Module.

Plugin marketplace with upload, review, installation, and lifecycle management

This module provides comprehensive functionality for plugin_market management
including data models, API endpoints, business logic, and integration points.

Architecture:
    - models/: SQLAlchemy ORM models
    - schemas/: Pydantic request/response schemas
    - services/: Business logic and data access layer
    - api/: FastAPI route handlers
    - tests/: Unit and integration tests

Usage:
    from app.modules.plugin_market import models, services, api
"""
