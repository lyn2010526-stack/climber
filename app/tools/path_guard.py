"""Path containment for the tool layer.

The file tools in ``builtins.py`` do not each own a containment rule; they
delegate to ``app.core.security_sandbox.SecuritySandbox.validate_file_access``,
which is also what ``app.core.engine.validation._check_sandbox`` calls at
dispatch time. New retrieval tools reuse that same rule so a search cannot
reach a path the surrounding file tools would refuse.

The module-level ``security_sandbox`` singleton in ``app/core/security_sandbox.py``
is built with ``SandboxConfig(workdir="/tmp/sandbox")``, so it denies everything
outside ``/tmp/sandbox``. ``AgentEngine._init_sandbox`` builds its own instance
from ``CLIMBER_SANDBOX_WORKDIR`` or the process cwd. This module follows the
engine so retrieval works against the real project tree, and callers can
override the root (tests, multi-tenant hosts) via :func:`set_workspace_root`.
"""

from __future__ import annotations

import os

from app.core.security_sandbox import SandboxConfig, SecuritySandbox

_OVERRIDE_ROOT: str | None = None
_SANDBOX: SecuritySandbox | None = None


def workspace_root() -> str:
    """Return the directory tools are allowed to read and search."""
    if _OVERRIDE_ROOT is not None:
        return os.path.abspath(_OVERRIDE_ROOT)
    return os.environ.get("CLIMBER_SANDBOX_WORKDIR") or os.getcwd()


def set_workspace_root(root: str | None) -> None:
    """Pin the search/read root, or pass ``None`` to follow the environment."""
    global _OVERRIDE_ROOT, _SANDBOX
    _OVERRIDE_ROOT = root
    _SANDBOX = None


def sandbox() -> SecuritySandbox:
    """Return a sandbox configured against :func:`workspace_root`."""
    global _SANDBOX
    if _SANDBOX is None:
        _SANDBOX = SecuritySandbox(SandboxConfig(workdir=workspace_root()))
    return _SANDBOX


def resolve_search_path(path: str) -> tuple[str, str]:
    """Resolve ``path`` for a read-only search.

    Relative paths are taken as relative to :func:`workspace_root`, so a
    tool call means the same thing regardless of the process cwd.

    Returns ``(absolute_path, "")`` when the path is searchable, otherwise
    ``("", reason)``. Rejects ``..`` traversal outright, then applies
    ``SecuritySandbox.validate_file_access`` and a realpath containment check
    so a sibling directory sharing a name prefix (``/repo`` vs ``/repo-secrets``)
    or a symlink cannot slip past the sandbox's prefix comparison.
    """
    if not isinstance(path, str) or not path.strip():
        return "", "Empty path: provide a directory to search."
    if ".." in path.split("/"):
        return "", f"Access denied: path '{path}' contains a '..' traversal segment."

    root = workspace_root()
    absolute = os.path.abspath(path if os.path.isabs(path) else os.path.join(root, path))

    ok, reason = sandbox().validate_file_access(absolute, "read")
    if not ok:
        return "", f"{reason} (root: {workspace_root()})"

    real = os.path.realpath(absolute)
    real_root = os.path.realpath(workspace_root())
    if real != real_root and not real.startswith(real_root + os.sep):
        return "", f"Access denied: path '{absolute}' resolves outside the workspace root."

    if not os.path.exists(absolute):
        return "", f"Path not found: {absolute}"

    return absolute, ""


__all__ = [
    "resolve_search_path",
    "sandbox",
    "set_workspace_root",
    "workspace_root",
]
