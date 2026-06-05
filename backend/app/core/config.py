from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Plum OPD Claim Adjudication"
    environment: str = "local"
    database_url: str = Field(
        default="postgresql+psycopg://plum:plum@localhost:5432/plum",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    jwt_secret: str = Field(default="change-this-in-production", validation_alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    max_upload_mb: int = 10
    upload_dir: Path = BACKEND_DIR / "uploads"
    policy_config_path: Path = BACKEND_DIR / "config" / "opd_policy.json"
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", validation_alias="OPENAI_MODEL")
    cors_origins: str = Field(default="http://localhost:3000", validation_alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
