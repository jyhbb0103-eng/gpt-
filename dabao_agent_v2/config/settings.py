"""Runtime settings and stable project paths."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STORAGE_ROOT = PROJECT_ROOT / "storage"


class Settings(BaseSettings):
    """Load secrets and model controls from the project-root .env file."""

    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")
    deepseek_temperature: float = Field(default=0.2, alias="DEEPSEEK_TEMPERATURE")
    deepseek_timeout: float = Field(default=30.0, alias="DEEPSEEK_TIMEOUT")
    deepseek_max_tokens: int = Field(default=2000, alias="DEEPSEEK_MAX_TOKENS")
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def has_api_key(self) -> bool:
        return bool(self.deepseek_api_key and self.deepseek_api_key.strip() not in {"", "xxxx"})


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()


def ensure_storage() -> None:
    """Create all runtime storage folders."""
    for name in ("skills", "memory", "logs", "reports", "uploads", "generated", "cache"):
        (STORAGE_ROOT / name).mkdir(parents=True, exist_ok=True)
