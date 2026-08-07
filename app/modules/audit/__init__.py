"""Audit Module.

Comprehensive audit logging for tracking user actions, API calls, and system events

This module provides comprehensive functionality for audit management
including data models, API endpoints, business logic, and integration points.

Architecture:
    - models/: SQLAlchemy ORM models
    - schemas/: Pydantic request/response schemas
    - services/: Business logic and data access layer
    - api/: FastAPI route handlers
    - tests/: Unit and integration tests

Usage:
    from app.modules.audit import models, services, api
"""
