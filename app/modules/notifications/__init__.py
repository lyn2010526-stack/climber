"""Notifications Module.

Multi-channel notification system supporting email, SMS, push notifications, and webhooks

This module provides comprehensive functionality for notifications management
including data models, API endpoints, business logic, and integration points.

Architecture:
    - models/: SQLAlchemy ORM models
    - schemas/: Pydantic request/response schemas
    - services/: Business logic and data access layer
    - api/: FastAPI route handlers
    - tests/: Unit and integration tests

Usage:
    from app.modules.notifications import models, services, api
"""
