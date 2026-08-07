"""Billing API routes."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.database import get_db


router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


@router.get("/", response_model=dict, summary="List all plans")
async def list_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List plans with pagination."""
    return {"items": [], "total": 0, "page": page, "page_size": page_size}

@router.get("/{item_id}", response_model=dict, summary="Get a plan")
async def get_plan(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get plan by ID."""
    raise HTTPException(status_code=404, detail="Plan not found")

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict, summary="Create a plan")
async def create_plan(
    data: dict,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create new plan."""
    return {"id": "new-id", **data}

@router.put("/{item_id}", response_model=dict, summary="Update a plan")
async def update_plan(
    item_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update plan."""
    return {"id": item_id, **data}

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a plan")
async def delete_plan(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete plan."""
    pass

@router.get("/stats/summary", response_model=dict, summary="Get statistics")
async def get_stats(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Get plan statistics."""
    return {"total": 0, "active": 0, "inactive": 0}
