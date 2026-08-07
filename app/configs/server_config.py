"""Configuration: server - App configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum


class ServerEnvironment(StrEnum):
    """Environment enum."""
    DEVELOPMENT = 'development'
    STAGING = 'staging'
    PRODUCTION = 'production'
    TESTING = 'testing'


@dataclass
class ServerDatabaseConfig:
    """Database configuration."""
    host: str = 'localhost'
    port: int = 5432
    name: str = 'agent_engine'
    user: str = 'postgres'
    password: str = ''
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    echo: bool = False


@dataclass
class ServerCacheConfig:
    """Cache configuration."""
    backend: str = 'redis'
    host: str = 'localhost'
    port: int = 6379
    password: str = ''
    db: int = 0
    default_ttl: int = 300
    key_prefix: str = 'ae:'


@dataclass
class ServerAuthConfig:
    """Auth configuration."""
    secret_key: str = 'change-me-in-production'
    algorithm: str = 'HS256'
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30


@dataclass
class ServerLoggingConfig:
    """Logging configuration."""
    level: str = 'INFO'
    format: str = 'json'
    output: str = 'stdout'
    file_path: str | None = None
    max_file_size: int = 10485760
    backup_count: int = 5


@dataclass
class ServerServerConfig:
    """Server configuration."""
    host: str = '0.0.0.0'
    port: int = 8000
    workers: int = 4
    reload: bool = False
    cors_origins: list[str] = field(default_factory=lambda: ['*'])
    trusted_hosts: list[str] = field(default_factory=list)


@dataclass
class ServerEmailConfig:
    """Email configuration."""
    smtp_host: str = 'localhost'
    smtp_port: int = 587
    smtp_user: str = ''
    smtp_password: str = ''
    use_tls: bool = True
    from_email: str = 'noreply@example.com'
    from_name: str = 'Agent Engine'


@dataclass
class ServerStorageConfig:
    """Storage configuration."""
    backend: str = 'local'
    local_path: str = './uploads'
    max_file_size: int = 10485760
    allowed_extensions: list[str] = field(default_factory=lambda: ['.pdf', '.doc', '.txt'])


@dataclass
class ServerFeatureFlags:
    """Feature flags."""
    enable_beta_features: bool = False
    enable_experimental: bool = False
    enable_maintenance_mode: bool = False
    enable_rate_limiting: bool = True
    enable_caching: bool = True
    enable_webhooks: bool = True
    enable_notifications: bool = True


@dataclass
class ServerAppConfig:
    """Main application configuration."""

    environment: str = 'development'
    debug: bool = False
    app_name: str = 'Agent Engine'
    app_version: str = '1.0.0'
    api_prefix: str = '/api/v1'

    database: ServerDatabaseConfig = field(default_factory=ServerDatabaseConfig)
    cache: ServerCacheConfig = field(default_factory=ServerCacheConfig)
    auth: ServerAuthConfig = field(default_factory=ServerAuthConfig)
    logging: ServerLoggingConfig = field(default_factory=ServerLoggingConfig)
    server: ServerServerConfig = field(default_factory=ServerServerConfig)
    email: ServerEmailConfig = field(default_factory=ServerEmailConfig)
    storage: ServerStorageConfig = field(default_factory=ServerStorageConfig)
    features: ServerFeatureFlags = field(default_factory=ServerFeatureFlags)

    @classmethod
    def from_env(cls) -> ServerAppConfig:
        """Load configuration from environment variables."""
        config = cls()
        config.environment = os.getenv('APP_ENV', 'development')
        config.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        config.database.host = os.getenv('DB_HOST', 'localhost')
        config.database.port = int(os.getenv('DB_PORT', '5432'))
        config.database.name = os.getenv('DB_NAME', 'agent_engine')
        config.database.user = os.getenv('DB_USER', 'postgres')
        config.database.password = os.getenv('DB_PASSWORD', '')
        config.cache.host = os.getenv('REDIS_HOST', 'localhost')
        config.cache.port = int(os.getenv('REDIS_PORT', '6379'))
        config.auth.secret_key = os.getenv('SECRET_KEY', 'change-me')
        config.server.port = int(os.getenv('PORT', '8000'))
        return config

    def validate(self) -> list[str]:
        """Validate configuration."""
        errors = []
        if self.environment == 'production':
            if self.auth.secret_key == 'change-me-in-production':
                errors.append('Secret key must be changed in production')
            if self.debug:
                errors.append('Debug mode should be disabled in production')
        return errors
