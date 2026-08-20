"""Local-user identity shared by API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.websockets import WebSocket

LOCAL_USER_ID = "default-user"


def get_current_user() -> str:
    """Return the single local user used by this local-first application."""
    return LOCAL_USER_ID


def extract_ws_token(websocket: WebSocket) -> str:
    """Extract a bearer token from query params or WebSocket headers.

    Lookup order: `token` query param -> `Authorization: Bearer <t>` header
    -> first value of `Sec-WebSocket-Protocol` header.
    """
    token = websocket.query_params.get("token")
    if token:
        return token
    auth_header = websocket.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    proto = websocket.headers.get("sec-websocket-protocol", "")
    if proto:
        return proto.split(",")[0].strip()
    return ""


async def authenticate_websocket(websocket: WebSocket) -> str | None:
    """Authenticate a WebSocket connection before accept.

    Local-first: any non-empty token grants access and maps to the local
    user identity (same principal as get_current_user). Missing/invalid
    token closes the socket with 4401 and returns None.
    """
    token = extract_ws_token(websocket)
    if not token:
        await websocket.close(code=4401, reason="unauthorized")
        return None
    return get_current_user()
