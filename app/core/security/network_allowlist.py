"""Network Allowlist.

Deny-by-default outbound network access with domain allowlist.
Supports wildcard domains and DNS resolution validation.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger()


class NetworkAllowlist:
    """Manages outbound network allowlist (deny-by-default)."""

    DEFAULT_ALLOWED_DOMAINS = [
        "api.openai.com",
        "api.anthropic.com",
        "localhost",
        "127.0.0.1",
    ]

    def __init__(self, allowed_domains: list[str] | None = None):
        domains = allowed_domains or self.DEFAULT_ALLOWED_DOMAINS
        self._allowed: set[str] = set(d.strip().lower() for d in domains)
        self._wildcards: list[str] = []
        self._rebuild_wildcards()

    def add_allowed_domain(self, domain: str) -> None:
        """Add a domain to the allowlist."""
        domain = domain.strip().lower()
        if domain.startswith("*."):
            if domain not in self._wildcards:
                self._wildcards.append(domain)
                self._allowed.add(domain)
        else:
            self._allowed.add(domain)
        logger.info("domain_allowed", domain=domain)

    def remove_allowed_domain(self, domain: str) -> None:
        """Remove a domain from the allowlist."""
        domain = domain.strip().lower()
        self._allowed.discard(domain)
        if domain in self._wildcards:
            self._wildcards.remove(domain)
        logger.info("domain_removed", domain=domain)

    def is_allowed(self, domain: str) -> bool:
        """Check if a domain is allowed."""
        domain = domain.strip().lower()

        if domain in self._allowed:
            return True

        for wildcard in self._wildcards:
            pattern = wildcard[1:]
            if domain.endswith(pattern):
                return True

        return False

    def check_url(self, url: str) -> tuple[bool, str]:
        """Check if a URL is allowed. Returns (ok, reason)."""
        try:
            parsed = urlparse(url)
        except Exception as e:
            return False, f"Invalid URL: {e}"

        if not parsed.hostname:
            return False, "No hostname in URL"

        hostname = parsed.hostname.lower()

        if self.is_allowed(hostname):
            return True, ""

        return False, f"Domain '{hostname}' is not in the network allowlist"

    def get_allowed_domains(self) -> list[str]:
        """Get list of all allowed domains."""
        return sorted(self._allowed)

    def validate_dns(self, domain: str) -> tuple[bool, str]:
        """Validate domain via DNS resolution."""
        import socket
        try:
            socket.getaddrinfo(domain, None)
            return True, ""
        except socket.gaierror as e:
            return False, f"DNS resolution failed for '{domain}': {e}"

    def _rebuild_wildcards(self) -> None:
        """Rebuild wildcard list from allowed set."""
        self._wildcards = [d for d in self._allowed if d.startswith("*.")]


network_allowlist = NetworkAllowlist()
