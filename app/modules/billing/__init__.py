"""Billing Module.

Billing and subscription management including plans, usage tracking, invoicing, and payment processing

This module provides comprehensive functionality for billing management
including data models, API endpoints, business logic, and integration points.

Architecture:
    - models/: SQLAlchemy ORM models
    - schemas/: Pydantic request/response schemas
    - services/: Business logic and data access layer
    - api/: FastAPI route handlers
    - tests/: Unit and integration tests

Usage:
    from app.modules.billing import models, services, api
"""
