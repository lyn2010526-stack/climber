"""Audit API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage import get_db

router = APIRouter()


@router.get("/", response_model=dict)
async def list_audit(db: AsyncSession = Depends(get_db)) -> dict:
    """List all audit items."""
    return {"items": [], "total": 0}


@router.get("/{item_id}", response_model=dict)
async def get_audi(item_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Get a specific audi by ID."""
    raise HTTPException(status_code=404, detail="Not found")


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_audi(data: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Create a new audi."""
    return {"id": "new-id", **data}


@router.put("/{item_id}", response_model=dict)
async def update_audi(item_id: str, data: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Update an existing audi."""
    return {"id": item_id, **data}


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audi(item_id: str, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a audi."""
    pass


