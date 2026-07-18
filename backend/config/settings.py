"""Central configuration. All values are environment-driven so the same image
runs unmodified in local dev, Docker, and Railway."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # -- App --
    APP_NAME: str = "PII Redaction API"
    ENVIRONMENT: str = "development"  # development | production | test
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    # -- Security --
    API_KEY: str = ""  # empty disables auth, for local dev only
    SECRET_KEY: str = "dev-only-insecure-secret-change-me"  # signs download tokens
    # Plain str, not list[str]: pydantic-settings runs json.loads() on any env
    # var mapped to a list field, so a plain comma-separated value (the natural
    # thing to type into Render's dashboard) crashes at import time with a
    # JSONDecodeError before the app even starts. Parsed manually below to
    # accept either a JSON array (`["a","b"]`) or a comma-separated string.
    CORS_ORIGINS_RAW: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    @property
    def CORS_ORIGINS(self) -> list[str]:  # noqa: N802 - keeps the env var name stable
        raw = self.CORS_ORIGINS_RAW.strip()
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return [str(origin).strip() for origin in parsed if str(origin).strip()]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    # -- Database --
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'storage' / 'pii_redactor.db'}"

    # -- File storage --
    STORAGE_BACKEND: str = "local"  # local | s3
    LOCAL_STORAGE_DIR: str = str(BASE_DIR / "storage" / "files")
    SIGNED_URL_TTL_SECONDS: int = 900

    # S3 / S3-compatible (used only when STORAGE_BACKEND=s3)
    S3_BUCKET: str = ""
    S3_REGION: str = "us-east-1"
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None

    # -- Upload limits --
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    ALLOWED_EXTENSIONS: tuple[str, ...] = (".docx", ".pdf")

    # -- Detection defaults --
    DEFAULT_CONFIDENCE_FLOOR: float = 0.75
    SPACY_MODEL: str = "en_core_web_md"

    @field_validator("LOCAL_STORAGE_DIR")
    @classmethod
    def _ensure_storage_dir(cls, value: str) -> str:
        Path(value).mkdir(parents=True, exist_ok=True)
        return value

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    Path(settings.LOCAL_STORAGE_DIR).mkdir(parents=True, exist_ok=True)
    if settings.DATABASE_URL.startswith("sqlite:///"):
        db_path = Path(settings.DATABASE_URL.replace("sqlite:///", "", 1))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
