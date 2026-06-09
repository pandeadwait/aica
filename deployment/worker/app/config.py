from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class WorkerSettings:
    database_url: str
    llm_base_url: str
    llm_model: str
    backend_base_url: str
    processing_poll_interval_seconds: int


def _env_or_default(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


def _env_int(name: str, default: int) -> int:
    raw = _env_or_default(name, str(default))
    return int(raw)


def get_settings() -> WorkerSettings:
    return WorkerSettings(
        database_url=os.environ["DATABASE_URL"],
        llm_base_url=os.environ["LLM_BASE_URL"],
        llm_model=os.environ["LLM_MODEL"],
        backend_base_url=_env_or_default("BACKEND_BASE_URL", "http://backend:8000"),
        processing_poll_interval_seconds=_env_int("PROCESSING_POLL_INTERVAL_SECONDS", 10),
    )
