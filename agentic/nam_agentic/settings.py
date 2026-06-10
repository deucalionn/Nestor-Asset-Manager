"""Environment-backed settings for the nam-agentic process."""

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
    llm_num_predict: int = 2048
    llm_num_ctx: int = 32768
    llm_reasoning: bool = False
    embedding_model: str = "nomic-embed-text"
    # nomic-embed-text outputs 768; we store vector(384) via Matryoshka truncation.
    embedding_dim: int = 384
    default_user_id: str = "00000000-0000-0000-0000-000000000001"
    database_url: str = "postgresql+asyncpg://nam:nam@localhost:5432/nam"
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


settings = Settings()
