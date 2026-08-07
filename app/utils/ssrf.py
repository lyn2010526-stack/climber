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

    if parsed.scheme not in _ALLOW_SCHEMES:
        return "Only http/https URLs are allowed"
    if not parsed.hostname:
        return "URL has no host"

    hostname = parsed.hostname.strip("[]").lower()
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

    # Resolve the hostname and reject when any resolved address is unsafe.
    try:
        infos = socket.getaddrinfo(hostname, parsed.port or 80, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, OSError, ValueError):
        return None

    for info in infos:
        try:
            resolved = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if _is_unsafe_ip(resolved):
            return f"Host '{hostname}' resolves to a non-public address"
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
