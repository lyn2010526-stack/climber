"""Notifications API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage import get_db

router = APIRouter()


@router.get("/", response_model=dict)
async def list_notifications(db: AsyncSession = Depends(get_db)) -> dict:
    """List all notifications items."""
    return {"items": [], "total": 0}


@router.get("/{item_id}", response_model=dict)
async def get_notification(item_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Get a specific notification by ID."""
    raise HTTPException(status_code=404, detail="Not found")


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_notification(data: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Create a new notification."""
    return {"id": "new-id", **data}


@router.put("/{item_id}", response_model=dict)
async def update_notification(item_id: str, data: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Update an existing notification."""
    return {"id": item_id, **data}


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(item_id: str, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a notification."""
    pass


