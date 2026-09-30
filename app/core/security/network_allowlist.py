"""Network Allowlist.

Deny-by-default outbound network access with domain allowlist.
Supports wildcard domains and DNS resolution validation.

Outbound destinations are judged in two layers:

1. Destination safety runs first and is never bypassable. Loopback, private,
   link-local, reserved and cloud metadata destinations are always rejected,
   including hostnames that resolve to one of them. The address rules live in
   :mod:`app.utils.ssrf` and are reused here so every outbound HTTP call in
   the system shares a single policy.
2. Domain scoping applies to the public destinations that survive layer 1.
   They are reachable by default, while ``strict_domain_mode`` narrows egress
   to allowlisted domains and their wildcard matches.
"""

from __future__ import annotations

from urllib.parse import urlparse

import structlog

from app.utils import ssrf

logger = structlog.get_logger()


class NetworkAllowlist:
    """Manages outbound network allowlist.

    ``DEFAULT_ALLOWED_DOMAINS`` lists public provider hosts only. Loopback and
    private entries are intentionally absent: layer 1 rejects them regardless
    of the allowlist, so allowlisting them would grant nothing.
    """

    DEFAULT_ALLOWED_DOMAINS = [
        "api.openai.com",
        "api.anthropic.com",
    ]

    def __init__(
        self,
        allowed_domains: list[str] | None = None,
        strict_domain_mode: bool = False,
    ):
        domains = allowed_domains or self.DEFAULT_ALLOWED_DOMAINS
        self._allowed: set[str] = set(d.strip().lower() for d in domains)
        self.strict_domain_mode = strict_domain_mode
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
        """Check if a domain is in the allowlist."""
        domain = domain.strip().lower()

        if domain in self._allowed:
            return True

        for wildcard in self._wildcards:
            pattern = wildcard[1:]
            if domain.endswith(pattern):
                return True

        return False

    def check_url(self, url: str) -> tuple[bool, str]:
        """Check if a URL may be requested. Returns (ok, reason)."""
        try:
            parsed = urlparse(url)
        except Exception as e:
            return False, f"Invalid URL: {e}"

        if not parsed.hostname:
            return False, "No hostname in URL"

        unsafe = ssrf.blocked_reason(url)
        if unsafe:
            logger.warning("network_destination_blocked", url=url, reason=unsafe)
            return False, unsafe

        hostname = parsed.hostname.lower()

        if not self.strict_domain_mode or self.is_allowed(hostname):
            return True, ""

        logger.warning("network_domain_not_allowlisted", domain=hostname)
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
