from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    app_env: str = Field(default="local")
    log_level: str = Field(default="info")
    database_url: str = Field(alias="DATABASE_URL")
    llm_base_url: str = Field(alias="LLM_BASE_URL")
    llm_model: str = Field(alias="LLM_MODEL")
    app_documents_dir: str = Field(alias="APP_DOCUMENTS_DIR")
    app_artifacts_dir: str = Field(alias="APP_ARTIFACTS_DIR")
    app_temp_dir: str = Field(alias="APP_TEMP_DIR")

    @property
    def app_documents_path(self) -> Path:
        return Path(self.app_documents_dir)

    @property
    def app_artifacts_path(self) -> Path:
        return Path(self.app_artifacts_dir)

    @property
    def app_temp_path(self) -> Path:
        return Path(self.app_temp_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
