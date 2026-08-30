"""Management API for external channel DM pairings."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user
from app.core.channel_gateway import (
    ChannelPairing,
    PairingError,
    PairingStatus,
    get_channel_gateway,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _pairing_to_dict(pairing: ChannelPairing) -> dict[str, Any]:
    return {
        "id": pairing.id,
        "channel": pairing.channel,
        "external_user_id": pairing.external_user_id,
        "conversation_id": pairing.conversation_id,
        "capability": pairing.capability,
        "status": pairing.status.value,
        "created_at": pairing.created_at,
        "expires_at": pairing.expires_at,
        "approved_at": pairing.approved_at,
        "revoked_at": pairing.revoked_at,
    }


def _raise_pairing_error(exc: PairingError) -> None:
    status_codes = {
        "PAIRING_NOT_FOUND": 404,
        "PAIRING_EXPIRED": 410,
        "PAIRING_STATE_CONFLICT": 409,
    }
    raise HTTPException(
        status_code=status_codes.get(exc.code, 409),
        detail={"code": exc.code},
    ) from exc


@router.get("/pairings")
async def list_pairings(
    status: PairingStatus | None = Query(default=None),
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    pairings = await get_channel_gateway().list_pairings(
        owner_user_id=user_id,
        status=status,
    )
    return {
        "pairings": [_pairing_to_dict(pairing) for pairing in pairings],
        "total": len(pairings),
    }


@router.post("/pairings/{pairing_id}/approve")
async def approve_pairing(
    pairing_id: str,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        pairing = await get_channel_gateway().approve(pairing_id, owner_user_id=user_id)
    except PairingError as exc:
        _raise_pairing_error(exc)
    return {"ok": True, "pairing": _pairing_to_dict(pairing)}


@router.post("/pairings/{pairing_id}/revoke")
async def revoke_pairing(
    pairing_id: str,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        pairing = await get_channel_gateway().revoke(pairing_id, owner_user_id=user_id)
    except PairingError as exc:
        _raise_pairing_error(exc)
    return {"ok": True, "pairing": _pairing_to_dict(pairing)}
