"""Knowledge Module.

Knowledge base and RAG system with document upload, chunking, vector search, and retrieval

This module provides comprehensive functionality for knowledge management
including data models, API endpoints, business logic, and integration points.

Architecture:
    - models/: SQLAlchemy ORM models
    - schemas/: Pydantic request/response schemas
    - services/: Business logic and data access layer
    - api/: FastAPI route handlers
    - tests/: Unit and integration tests

Usage:
    from app.modules.knowledge import models, services, api
"""
