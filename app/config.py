"""Application configuration using pydantic-settings."""

from __future__ import annotations

import secrets
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    app_testing: bool = Field(default=False)
    app_debug: bool = Field(default=False)
    app_log_level: str = Field(default="INFO")
    app_secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))

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
    def is_sqlite(self) -> bool:
        url = self.test_database_url if self.app_testing else self.database_url
        return url.startswith("sqlite")


settings = Settings()
