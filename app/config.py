"""Application configuration using pydantic-settings."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from typing import Annotated
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _load_or_create_secret_key() -> str:
    """Resolve a stable application secret key.

    Priority: explicit APP_SECRET_KEY env var -> persisted key file ->
    ephemeral random key (fallback when the data dir is not writable).
    A stable key keeps API-key HMAC derivations valid across restarts.
    """
    env_key = os.getenv("APP_SECRET_KEY")
    if env_key and env_key not in ("change-me", "change-me-in-production"):
        return env_key
    key_file = BASE_DIR / "data" / ".secret_key"
    try:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        if key_file.exists():
            stored = key_file.read_text(encoding="utf-8").strip()
            if stored:
                return stored
        generated = secrets.token_hex(32)
        key_file.write_text(generated, encoding="utf-8")
        return generated
    except OSError:
        return secrets.token_hex(32)


class Settings(BaseSettings):
    app_testing: bool = Field(default=False)
    app_debug: bool = Field(default=False)
    app_log_level: str = Field(default="INFO")
    app_secret_key: str = Field(default_factory=_load_or_create_secret_key)

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

    cors_origins_list: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"],
        validation_alias="CORS_ORIGINS",
    )

    @field_validator("cors_origins_list", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [x.strip() for x in value.split(",") if x.strip()]
        return value

    mcp_timeout: int = Field(default=30)
    tool_timeout: int = Field(default=60)
    max_tool_retries: int = Field(default=2)

    # LLM providers
    ollama_base_url: str = Field(default="http://localhost:11434")

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
