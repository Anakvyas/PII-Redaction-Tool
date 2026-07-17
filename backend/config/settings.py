"""Central configuration. All values are environment-driven so the same image
runs unmodified in local dev, Docker, and Railway."""
from __future__ import annotations

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
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

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
    SPACY_MODEL: str = "en_core_web_sm"

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
