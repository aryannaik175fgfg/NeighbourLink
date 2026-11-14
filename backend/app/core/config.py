from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ROOT / ".env", _ROOT / ".env.example"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NeighbourLink"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://neighbourlink:neighbourlink_dev@127.0.0.1:5432/neighbourlink"

    secret_key: str = "dev-secret-change-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    jwt_algorithm: str = "HS256"

    api_host: str = "127.0.0.1"
    api_port: int = 8742
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    payment_hold_minutes: int = 24 * 60
    payment_webhook_secret: str = "nl-sandbox-webhook-secret"
    payments_provider: str = "sandbox"

    storage_path: str = "storage"
    max_upload_bytes: int = 5 * 1024 * 1024

    smtp_host: str | None = None
    smtp_from: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
