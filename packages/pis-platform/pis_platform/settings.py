from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class CommonSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    auth_jwt_secret: str = "dev_only_change_me_not_for_production"
    auth_jwt_algorithm: str = "HS256"
    auth_username: str = "admin"
    auth_password: str = "admin_dev_only"
    internal_service_token: str = "dev_internal_token"
    broker_sqlite_path: str = "data/broker.db"
    airport_cache_ttl_seconds: int = 300
    api_colombia_base_url: str = "https://api-colombia.com"
    api_colombia_timeout_seconds: float = 5.0
    airport_service_url: str = "http://127.0.0.1:8001"
    itinerary_service_url: str = "http://127.0.0.1:8002"
    notification_service_url: str = "http://127.0.0.1:8003"
    report_function_url: str = "http://127.0.0.1:8004"
    airport_database_url: str = "sqlite+aiosqlite:///data/airport.db"
    itinerary_database_url: str = "sqlite+aiosqlite:///data/itinerary.db"
    notification_database_url: str = "sqlite+aiosqlite:///data/notification.db"
    otel_console: bool = False

