from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ROOT_DIR / ".env", _ROOT_DIR / ".env.example"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_model: str = "ollama:gemma4"
    llm_base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 384
    default_user_id: str = "00000000-0000-0000-0000-000000000001"
    market_timezone: str = "Europe/Paris"
    agentic_host: str = "0.0.0.0"
    agentic_port: int = 8001
    agent_workspace_dir: Path = _ROOT_DIR / "data" / "agent_workspace"
    news_ingest_enabled: bool = True
    boursorama_min_delay_seconds: float = 1.5
    boursorama_max_delay_seconds: float = 4.0
    boursorama_max_requests_per_minute: int = 12
    boursorama_max_requests_per_hour: int = 120
    boursorama_user_agent: str = ""
    boursorama_send_referer: bool = True
    news_format_max_chars: int = 12_000
    news_format_llm_enabled: bool = True
    yahoo_resolve_prefer_suffix: str = ".PA"
    yahoo_request_timeout_sec: int = 30


settings = Settings()
