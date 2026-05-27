from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class WorkerSettings:
    database_url: str
    llm_base_url: str
    llm_model: str


def get_settings() -> WorkerSettings:
    return WorkerSettings(
        database_url=os.environ["DATABASE_URL"],
        llm_base_url=os.environ["LLM_BASE_URL"],
        llm_model=os.environ["LLM_MODEL"],
    )

