from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_path: Path = Field(default=Path("./data/agentic.db"))

    llm_gateway_base_url: str = "https://api.openai.com/v1"
    llm_gateway_api_key: str = ""
    llm_default_model: str = "claude-sonnet-4-6"

    agents_dir: Path = Field(default=Path("./agents"))

    log_level: str = "INFO"
    log_format: str = "json"

    max_steps_per_run: int = 50
    loop_detect_threshold: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
