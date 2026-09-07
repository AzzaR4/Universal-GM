"""Application configuration via Pydantic settings."""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "Universal AI Game Master"
    debug: bool = True

    # Database (async SQLite). File lives under ./data by default.
    database_url: str = "sqlite+aiosqlite:///./data/universal_gm.db"

    # CORS
    cors_origins: str = "*"

    # Encryption key for API keys stored in DB. Any string; it is hashed to 32 bytes.
    secret_key: str = "change-me-in-production-please-set-a-real-secret"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def fernet_key(self) -> bytes:
        """Derive a stable 32-byte urlsafe base64 key from secret_key for Fernet."""
        digest = hashlib.sha256(self.secret_key.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
