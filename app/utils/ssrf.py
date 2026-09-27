"""SSRF protection helpers for outbound HTTP requests.

These helpers reject outbound requests targeting loopback, private,
link-local, reserved, multicast addresses, and well-known cloud metadata
endpoints. They are used where a user- or agent-supplied URL is fetched by
the server on behalf of the caller.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger(__name__)

# Well-known cloud metadata endpoints frequently abused via SSRF.
_BLOCKED_HOSTS = frozenset({
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.azure.internal",
    "metadata.aws.internal",
    "100.100.100.200",
})

_ALLOW_SCHEMES = frozenset({"http", "https"})


def blocked_reason(url: str) -> str | None:
    """Return a human-readable reason when ``url`` must not be fetched, else None."""
    try:
        parsed = urlparse(url)
    except Exception:
        return "Invalid URL"

    if parsed.scheme.lower() not in _ALLOW_SCHEMES:
        return "Only http/https URLs are allowed"
    try:
        hostname_value = parsed.hostname
    except ValueError:
        return "URL has an invalid host"
    if not hostname_value:
        return "URL has no host"
    if parsed.username is not None or parsed.password is not None:
        return "URLs with embedded credentials are not allowed"

    hostname = hostname_value.strip("[]").rstrip(".").lower()
    if hostname in _BLOCKED_HOSTS:
        return f"Host '{hostname}' is blocked"

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None

    if ip is not None:
        if _is_unsafe_ip(ip):
            return f"Address '{hostname}' is not reachable externally"
        return None

    try:
        port = parsed.port or 80
    except ValueError:
        return "URL has an invalid port"

    # Resolve the hostname and reject when any resolved address is unsafe.
    try:
        infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, OSError, ValueError):
        # A failed lookup cannot prove that the destination is public. Fail
        # closed so transient DNS failures do not become an SSRF bypass.
        return f"Host '{hostname}' could not be resolved safely"

    resolved_any = False
    for info in infos:
        try:
            resolved = ipaddress.ip_address(info[4][0])
        except (IndexError, KeyError, TypeError, ValueError):
            continue
        resolved_any = True
        if _is_unsafe_ip(resolved):
            return f"Host '{hostname}' resolves to a non-public address"
    if not resolved_any:
        return f"Host '{hostname}' could not be resolved safely"
    return None


def _is_unsafe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )
