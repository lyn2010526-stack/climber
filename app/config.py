"""Application configuration using pydantic-settings."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import structlog
from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = structlog.get_logger()

# Values that look like a secret but are published in this repository, in
# .env.example, or in setup guides. Accepting one of these leaves the signing
# key publicly known, so they are treated as "no key configured".
_PLACEHOLDER_SECRETS = frozenset(
    {
        "change-me-in-production",
        "change_me_in_production",
        "changeme",
        "change-me",
        "changethis",
        "change_this",
        "your-secret-key",
        "your_secret_key",
        "your-secret-key-here",
        "your_secret_key_here",
        "secret",
        "secret-key",
        "secretkey",
        "replace-me",
        "replaceme",
        "todo",
        "xxx",
        "placeholder",
        "example",
    }
)
MIN_SECRET_LENGTH = 16

# Agent subtask concurrency. The default is the tuned single-node value; the
# ceiling is the hard bound one node may ever run, whatever an operator sets.
DEFAULT_MAX_CONCURRENT_SUBTASKS = 3
MAX_CONCURRENT_SUBTASKS_CEILING = 18

SECRET_GENERATION_HINT = (
    'Generate a real secret, e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`'
)


def is_placeholder_secret(value: str) -> bool:
    """Return True when a configured secret is unusable as a signing key.

    A truthy placeholder used to short-circuit the boot checks, so copying
    `.env.example` straight to `.env` passed validation while leaving a
    publicly known string in charge of signing tokens and of the Fernet key
    that encrypts stored third-party provider credentials.
    """
    candidate = (value or "").strip().lower()
    if not candidate:
        return True
    if candidate in _PLACEHOLDER_SECRETS:
        return True
    return len(candidate) < MIN_SECRET_LENGTH


class Settings(BaseSettings):
    app_env: str = Field(default="local")
    app_testing: bool = Field(default=False)
    app_debug: bool = Field(default=False)
    app_log_level: str = Field(default="INFO")
    app_secret_key: str = Field(default="")

    # Authentication settings
    # Authentication settings. Leave unset to auto-derive from APP_ENV:
    # dev/test default to disabled, production and staging default to enabled
    # and refuse to boot with auth off.
    enable_auth: bool | None = Field(default=None)
    initial_admin_password: str = Field(default="")
    auth_public_endpoints: list[str] = Field(
        default_factory=lambda: [
            "/health",
            "/health/logs",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
            "/",
            "/api/v1/integrations/domestic/qqbot/webhook",
        ]
    )

    websocket_paths: list[str] = Field(
        default_factory=lambda: [
            "/api/v1/ws/{session_id}",
            "/api/v1/ws/groups/{group_id}",
            "/api/v1/ws/agents/{agent_id}",
        ]
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=1440)

    # Local-first: SQLite by default. Point database_url at PostgreSQL only if
    # you actually need multi-user concurrency.
    database_url: str = Field(default="sqlite+aiosqlite:///./data/climber.db")
    test_database_url: str = Field(default="sqlite+aiosqlite:///./data/test.db")
    redis_url: str = Field(default="redis://localhost:6379/0")
    vector_store_path: str = Field(default="./data/chroma")

    @field_validator("database_url", "test_database_url", mode="before")
    @classmethod
    def _abs_sqlite(cls, value: str) -> str:
        if value.startswith("sqlite+aiosqlite:///./"):
            rel = value.replace("sqlite+aiosqlite:///./", "", 1)
            return "sqlite+aiosqlite:///" + str(BASE_DIR / rel)
        return value

    # SQLite tuning (ignored for other backends)
    sqlite_wal: bool = Field(default=True)
    sqlite_busy_timeout_ms: int = Field(default=5000)
    db_pool_size: int = Field(default=5)
    db_max_overflow: int = Field(default=10)
    db_pool_recycle: int = Field(default=1800)

    # Operational
    log_dir: str = Field(default=str(BASE_DIR / "logs"))
    workspace_dir: str = Field(default=str(BASE_DIR / "workspace"))
    memory_limit_mb: int = Field(default=2048)
    memory_check_interval: int = Field(default=60)

    # Local network access: 0.0.0.0 lets phones on the LAN reach the UI
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    enable_lan_access: bool = Field(default=False)
    trusted_proxies: str = Field(default="127.0.0.1,::1")

    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000")
    cors_origins_list: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )

    mcp_timeout: int = Field(default=30)
    tool_timeout: int = Field(default=60)
    max_tool_retries: int = Field(default=2)

    # Parallel subtasks a single run may execute. Default 3, hard ceiling 18.
    max_concurrent_subtasks: int = Field(default=DEFAULT_MAX_CONCURRENT_SUBTASKS)

    telegram_bot_token: str = Field(default="")

    # Domestic adapters stay disabled until an operator supplies a provider-specific secret.
    domestic_provider_mode: Literal["disabled", "local"] = Field(default="disabled")
    domestic_integrations_enabled: bool = Field(default=False)
    domestic_webhook_secret: str = Field(default="")
    domestic_qr_ttl_seconds: int = Field(default=300, ge=1, le=900)
    domestic_webhook_max_skew_seconds: int = Field(default=300, ge=1, le=3600)

    # User-provided LLM for L0/L1 summarization and session memory extraction.
    # Leave unset to degrade to deterministic rule-based generation; the
    # summarizer never reads Agent environment credentials.
    user_llm_api_key: str = Field(default="")
    user_llm_base_url: str = Field(default="")
    user_llm_model: str = Field(default="gpt-4o-mini")

    # API key rotation
    api_key_rotation_enabled: bool = Field(default=True)
    max_key_failures: int = Field(default=3)
    key_cooldown_seconds: int = Field(default=60)

    # Plugin marketplace catalog
    plugin_marketplace: list[dict] = Field(
        default_factory=lambda: [
            {
                "plugin_key": "web-scraper",
                "name": "网页抓取器",
                "description": "抓取并解析网页内容为结构化数据",
                "category": "data",
                "version": "1.0.0",
                "author": "climber",
            },
            {
                "plugin_key": "code-runner",
                "name": "代码执行器",
                "description": "在本地沙箱中执行 Python 代码片段",
                "category": "dev",
                "version": "1.0.0",
                "author": "climber",
            },
            {
                "plugin_key": "file-watcher",
                "name": "文件监听器",
                "description": "监听本地目录变化并触发工作流",
                "category": "automation",
                "version": "1.0.0",
                "author": "climber",
            },
        ]
    )

    @field_validator("max_concurrent_subtasks", mode="after")
    @classmethod
    def _clamp_max_concurrent_subtasks(cls, value: int) -> int:
        """Clamp into [1, ceiling] instead of failing, logging what was applied."""
        applied = min(max(value, 1), MAX_CONCURRENT_SUBTASKS_CEILING)
        if applied != value:
            logger.warning(
                "max_concurrent_subtasks_clamped",
                requested=value,
                applied=applied,
                ceiling=MAX_CONCURRENT_SUBTASKS_CEILING,
            )
        return applied

    @property
    def auth_public_endpoints_set(self) -> set[str]:
        return set(self.auth_public_endpoints)

    @property
    def is_sqlite(self) -> bool:
        url = self.test_database_url if self.app_testing else self.database_url
        return url.startswith("sqlite")

    @property
    def trusted_proxies_list(self) -> list[str]:
        return [proxy.strip() for proxy in self.trusted_proxies.split(",") if proxy.strip()]

    @model_validator(mode="after")
    def _require_stable_secret(self) -> Settings:
        environment = self.app_env.strip().lower()
        is_deployed = environment in {"production", "prod", "staging"}
        if self.enable_auth is None:
            self.enable_auth = is_deployed
        if is_deployed and not self.enable_auth:
            raise ValueError("ENABLE_AUTH must be true in production and staging environments")
        if self.app_secret_key:
            if is_placeholder_secret(self.app_secret_key) and is_deployed:
                raise ValueError(
                    f"APP_SECRET_KEY is still a placeholder value. {SECRET_GENERATION_HINT}"
                )
            return self
        if self.app_testing or environment in {"local", "development", "test", "testing"}:
            self.app_secret_key = "agent-engine-local-persistent-development-key"
            return self
        if self.enable_auth:
            raise ValueError("APP_SECRET_KEY must be configured when authentication is enabled")
        if environment in {"production", "prod", "staging"}:
            raise ValueError("APP_SECRET_KEY must be configured for authentication or production")
        raise ValueError("APP_SECRET_KEY must be configured outside local/test environments")


settings = Settings()
