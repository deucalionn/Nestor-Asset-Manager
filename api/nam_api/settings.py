from pathlib import Path
from uuid import UUID

from nam_db.settings import settings as db_settings
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ROOT_DIR / ".env", _ROOT_DIR / ".env.example"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    agentic_url: str = "http://localhost:8001"
    default_user_id: UUID | None = None

    @property
    def database_url(self) -> str:
        return db_settings.database_url


settings = Settings()
