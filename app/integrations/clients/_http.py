"""Bounded HTTP requests shared by the lightweight integration clients."""
from __future__ import annotations

import math

import httpx


class IntegrationError(RuntimeError):
    """A remote operation failed or its outcome could not be confirmed."""

    def __init__(
        self, service: str, detail: str, *, status_code: int | None = None,
        retry_after: str | None = None,
    ):
        super().__init__(f"{service}: {detail}")
        self.service = service
        self.status_code = status_code
        self.retry_after = retry_after


def require_config(service: str, **values: str) -> None:
    missing = [name for name, value in values.items()
               if not isinstance(value, str) or not value.strip()]
    if missing:
        raise NotImplementedError(
            f"{service}: unsupported configuration; provide {', '.join(missing)}"
        )


def validate_text(value: str, name: str, limit: int, *, allow_empty: bool = False) -> None:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{name} must be a {'string' if allow_empty else 'non-empty string'}")
    if len(value) > limit:
        raise ValueError(f"{name} exceeds the supported limit of {limit} characters")


def response_id(data: dict, field: str, service: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise IntegrationError(service, f"response is missing a valid {field}; outcome unknown")
    return value


async def request_json(
    service: str, method: str, url: str, *, headers: dict[str, str],
    timeout: float, payload: dict | None = None, auth: httpx.Auth | None = None,
    expected_status: int = 200,
) -> dict:
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError("timeout must be a positive finite number of seconds")
    try:
        # Redirects and ambient proxy settings must not forward explicit credentials.
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=False, trust_env=False,
        ) as client:
            response = await client.request(
                method, url, headers=headers, json=payload, auth=auth,
            )
    except httpx.TimeoutException:
        raise IntegrationError(service, "request timed out; outcome unknown") from None
    except httpx.RequestError:
        raise IntegrationError(service, "transport failure; outcome unknown") from None
    # Creation requests are deliberately never retried: they may already have succeeded.
    if response.status_code != expected_status:
        raise IntegrationError(
            service, f"unexpected HTTP status {response.status_code}",
            status_code=response.status_code,
            retry_after=response.headers.get("Retry-After"),
        )
    try:
        data = response.json()
    except ValueError:
        raise IntegrationError(service, "invalid JSON response; outcome unknown") from None
    if not isinstance(data, dict):
        raise IntegrationError(service, "expected a JSON object; outcome unknown")
    return data
