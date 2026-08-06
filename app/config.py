"""Application configuration using pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    app_env: str = Field(default="local")
    app_testing: bool = Field(default=False)
    app_debug: bool = Field(default=False)
    app_log_level: str = Field(default="INFO")
    app_secret_key: str = Field(default="")

    # Authentication settings
    enable_auth: bool = Field(default=False)
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

    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000")
    cors_origins_list: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"])

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
    def _require_stable_secret(self) -> Settings:
        if self.app_secret_key:
            return self
        environment = self.app_env.strip().lower()
        if self.enable_auth:
            raise ValueError("APP_SECRET_KEY must be configured when authentication is enabled")
        if self.app_testing or environment in {"local", "development", "test", "testing"}:
            self.app_secret_key = "agent-engine-local-persistent-development-key"
            return self
        if environment in {"production", "prod", "staging"}:
            raise ValueError("APP_SECRET_KEY must be configured for authentication or production")
        raise ValueError("APP_SECRET_KEY must be configured outside local/test environments")


settings = Settings()
