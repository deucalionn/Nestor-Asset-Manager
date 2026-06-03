from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ROOT_DIR / ".env", _ROOT_DIR / ".env.example"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_model: str = "ollama:llama3.1:8b"
    llm_base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 384
    default_user_id: str = "00000000-0000-0000-0000-000000000001"
    market_timezone: str = "Europe/Paris"
    agentic_host: str = "0.0.0.0"
    agentic_port: int = 8001
    agent_workspace_dir: Path = _ROOT_DIR / "data" / "agent_workspace"


settings = Settings()
