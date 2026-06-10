from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ROOT_DIR / ".env", _ROOT_DIR / ".env.example"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    yahoo_resolve_prefer_suffix: str = ".PA"
    yahoo_request_timeout_sec: int = 30


settings = Settings()
