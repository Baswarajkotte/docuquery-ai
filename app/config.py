from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DocuQuery AI"
    database_url: str = "sqlite:///./docuquery.db"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    max_upload_mb: int = 10
    chunk_size_words: int = 180
    chunk_overlap_words: int = 40
    top_k: int = 4

    # LLM answer generation is optional. Without a key the API returns an
    # extractive answer built from the best-matching passages.
    anthropic_api_key: str | None = None
    llm_model: str = "claude-opus-5-5"
    llm_max_tokens: int = 2000


@lru_cache
def get_settings() -> Settings:
    return Settings()
