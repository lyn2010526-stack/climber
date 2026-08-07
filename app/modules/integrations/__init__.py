"""Integrations Module.

Third-party integrations including Slack, Discord, Telegram, GitHub, Jira, and Notion

This module provides comprehensive functionality for integrations management
including data models, API endpoints, business logic, and integration points.

Architecture:
    - models/: SQLAlchemy ORM models
    - schemas/: Pydantic request/response schemas
    - services/: Business logic and data access layer
    - api/: FastAPI route handlers
    - tests/: Unit and integration tests

Usage:
    from app.modules.integrations import models, services, api
"""
