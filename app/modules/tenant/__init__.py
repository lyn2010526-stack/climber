"""Tenant Module.

Multi-tenant architecture with organization, team, and member management

This module provides comprehensive functionality for tenant management
including data models, API endpoints, business logic, and integration points.

Architecture:
    - models/: SQLAlchemy ORM models
    - schemas/: Pydantic request/response schemas
    - services/: Business logic and data access layer
    - api/: FastAPI route handlers
    - tests/: Unit and integration tests

Usage:
    from app.modules.tenant import models, services, api
"""
