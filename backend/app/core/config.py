from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Governance Proxy API"
    api_prefix: str = "/api"

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    auth_token: str = "demo-token-for-hackathon"
    jwt_secret: str = "change-me-jwt-secret"
    jwt_exp_minutes: int = 60
    cors_origins: str = "http://localhost:4200"

    # Database
    database_url: str = "postgresql+asyncpg://aigp:aigp_password@postgres:5432/aigp_db"
    redis_url: str = "redis://redis:6379"

    # ChromaDB
    chroma_host: str = "chromadb"
    chroma_port: int = 8000
    chroma_collection: str = "aigp_regulations"

    # ── Ollama (local open-source LLM) ──────────────────────────────────
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:3b"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4000
    llm_max_retries: int = 2
    llm_request_timeout_seconds: int = 120

    # ── Embedding / Classification model ────────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"
    rag_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_top_k: int = 5
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 50

    # Proxy
    proxy_port: int = 8080
    proxy_host: str = "0.0.0.0"

    data_dir: Path = Path(__file__).resolve().parents[2] / "data"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
