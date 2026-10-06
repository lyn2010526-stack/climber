"""Engine bootstrap: sandbox, reasoning, debug-loop and permission wiring.

Extracted from ``app.core.agent_engine`` so the facade stays thin. Every
function mutates the engine instance passed in; override points stay on the
``AgentEngine`` facade so tests and subclasses can intercept them.
"""

from __future__ import annotations

from typing import Any


def init_debug_loop(engine: Any) -> None:
    """Debug loop extension point; wired when a debug engine is installed.

    Args:
        engine: The AgentEngine instance.
    """
    engine.debug_loop = None
    from app.core.engine.dual_loop_hooks import install_metacognition_scope

    install_metacognition_scope(engine)


def init_reasoning(engine: Any) -> None:
    """Initialize the multi-strategy reasoning service so /reason API works.

    Args:
        engine: The AgentEngine instance to attach ``reasoning`` to.
    """
    try:
        from app.core.reasoning.service import ReasoningService

        engine.reasoning = ReasoningService(model_registry=engine.model_registry)
    except Exception:
        engine.reasoning = None


def init_sandbox(engine: Any) -> None:
    """Initialize the security sandbox, degrading to no sandbox on failure.

    Args:
        engine: The AgentEngine instance to attach sandbox attributes to.
    """
    try:
        import os

        from app.core.security_sandbox import (
            AgentMode,
            PermissionOverlay,
            SandboxConfig,
            SecuritySandbox,
        )

        workdir = os.environ.get("CLIMBER_SANDBOX_WORKDIR") or os.getcwd()
        engine.sandbox = SecuritySandbox(SandboxConfig(workdir=workdir))
        engine.permission_overlay = PermissionOverlay()
        engine._setup_default_permissions()
        engine.agent_mode = AgentMode.ACT
    except Exception:
        engine.sandbox = None
        engine.permission_overlay = None
        engine.agent_mode = None


def init_permissions(engine: Any) -> None:
    """Initialize default permission configuration, reloading persisted config.

    Args:
        engine: The AgentEngine instance to attach ``_default_permission_config`` to.
    """
    try:
        from app.core.permission_rules import get_default_config

        persisted = engine._load_permission_config()
        engine._default_permission_config = persisted or get_default_config()
    except Exception:
        try:
            from app.core.permission_rules import get_default_config

            engine._default_permission_config = get_default_config()
        except Exception:
            engine._default_permission_config = None


def permission_config_path() -> str:
    """Return the filesystem path of the persisted permission config.

    Returns:
        The path string under CLIMBER_DATA_DIR (default "data").
    """
    import os

    data_dir = os.environ.get("CLIMBER_DATA_DIR", "data")
    return os.path.join(data_dir, "permission_config.json")


def load_permission_config() -> Any:
    """Load the persisted default permission config, if any.

    Returns:
        A PermissionConfig instance, or None when missing or invalid.
    """
    import json
    import os

    path = permission_config_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        from app.core.permission_rules import PermissionConfig

        return PermissionConfig.from_dict(data)
    except Exception:
        return None


def save_permission_config(config: Any) -> None:
    """Persist the default permission config so it survives restarts.

    Args:
        config: The PermissionConfig to serialize.
    """
    import json
    import os

    path = permission_config_path()
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def setup_default_permissions(engine: Any) -> None:
    """Setup default permission overlay, mirroring permission_rules DEFAULT mode.

    Args:
        engine: The AgentEngine instance with a ``permission_overlay`` attribute.
    """
    from app.core.security_sandbox import PermissionLevel, PermissionRule

    defaults = [
        PermissionRule(
            action="read",
            resource_pattern="*",
            level=PermissionLevel.ALLOW,
            description="Read any file",
        ),
        PermissionRule(
            action="write",
            resource_pattern="*",
            level=PermissionLevel.ASK,
            description="Write requires approval",
        ),
        PermissionRule(
            action="execute",
            resource_pattern="*",
            level=PermissionLevel.ASK,
            description="Execute requires approval",
        ),
        PermissionRule(
            action="delete",
            resource_pattern="*",
            level=PermissionLevel.DENY,
            description="Delete forbidden",
        ),
    ]
    engine.permission_overlay.set_defaults(defaults)
