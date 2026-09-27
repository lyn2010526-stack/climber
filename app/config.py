"""Application configuration using pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

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


def _is_placeholder_secret(value: str) -> bool:
    """Return True when a configured secret is a known placeholder.

    Args:
        value: The configured secret.

    Returns:
        True if the value is a documented placeholder or too short to be a
        usable signing key.
    """
    candidate = (value or "").strip().lower()
    if not candidate:
        return True
    if candidate in _PLACEHOLDER_SECRETS:
        return True
    return len(candidate) < 16


class Settings(BaseSettings):
    app_env: str = Field(default="local")
    app_testing: bool = Field(default=False)
    app_debug: bool = Field(default=False)
    app_log_level: str = Field(default="INFO")
    app_secret_key: str = Field(default="")

    # Authentication settings
    enable_auth: bool = Field(default=False)
    # Password for the account bootstrapped on an empty user table. Leave it
    # empty to have a strong random password generated and logged once. Values
    # that are published in this repository are rejected.
    bootstrap_admin_password: str = Field(default="")
    auth_public_endpoints: list[str] = Field(
        default_factory=lambda: [
            "/health",
            "/health/logs",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
            "/",
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

    # Comma-separated allowlist. cors_origins_list is derived from this in a
    # validator below: it used to be a second independent field, so the
    # documented CORS_ORIGINS variable was read by nothing and setting it had
    # no effect on the running server.
    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000")
    cors_origins_list: list[str] = Field(default_factory=list)
    # Hardcoded True in main.py until now. Kept configurable so a deployment
    # that genuinely wants a public API can turn credentials off and use "*".
    cors_allow_credentials: bool = Field(default=True)

    mcp_timeout: int = Field(default=30)
    tool_timeout: int = Field(default=60)
    max_tool_retries: int = Field(default=2)

    telegram_bot_token: str = Field(default="")

    # API key rotation
    api_key_rotation_enabled: bool = Field(default=True)
    max_key_failures: int = Field(default=3)
    key_cooldown_seconds: int = Field(default=60)

    # Plugin marketplace catalog
    plugin_marketplace: list[dict] = Field(default_factory=lambda: [
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
    ])

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
    def _derive_cors_list(self) -> Settings:
        """Populate the origin list from the single documented variable.

        ``cors_origins_list`` used to be an independent field with its own
        default, so ``CORS_ORIGINS`` was read by nothing: setting it to a new
        origin had no effect on the running server.
        """
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if not origins:
            raise ValueError("CORS_ORIGINS must list at least one origin")
        if "*" in origins and self.cors_allow_credentials:
            # Starlette reflects the request Origin in this combination, so the
            # result is any site able to call the API with credentials.
            raise ValueError(
                "CORS_ORIGINS='*' cannot be combined with credentials. Set "
                "CORS_ALLOW_CREDENTIALS=false for a public API, or list the "
                "origins explicitly."
            )
        self.cors_origins_list = origins
        return self

    @model_validator(mode="after")
    def _require_stable_secret(self) -> Settings:
        environment = self.app_env.strip().lower()
        if self.app_secret_key:
            if _is_placeholder_secret(self.app_secret_key) and environment in {
                "production",
                "prod",
                "staging",
            }:
                # A truthy placeholder used to return early here, so copying
                # .env.example straight to .env satisfied every check while
                # leaving a publicly known string as the signing key.
                raise ValueError(
                    "APP_SECRET_KEY is still a placeholder value. Generate a "
                    "real secret, e.g. `python -c \"import secrets;"
                    " print(secrets.token_urlsafe(48))\"`"
                )
            return self
        if self.enable_auth:
            raise ValueError("APP_SECRET_KEY must be configured when authentication is enabled")
        if self.app_testing or environment in {"local", "development", "test", "testing"}:
            self.app_secret_key = "agent-engine-local-persistent-development-key"
            return self
        if environment in {"production", "prod", "staging"}:
            raise ValueError("APP_SECRET_KEY must be configured for authentication or production")
        raise ValueError("APP_SECRET_KEY must be configured outside local/test environments")


settings = Settings()
