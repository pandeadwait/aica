from __future__ import annotations

from fastapi import APIRouter, Request

from app.config import get_settings
from app.services.runtime_checks import check_database, check_llm


router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    settings = get_settings()
    return {
        "service": "backend",
        "status": "phase3",
        "environment": settings.app_env,
    }


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    settings = get_settings()
    database = await check_database(settings.database_url)
    llm = await check_llm(settings.llm_base_url)

    return {
        "status": "ok" if database["ok"] and llm["ok"] else "degraded",
        "checks": {
            "database": database,
            "llm": llm,
        },
        "startup_checks": getattr(request.app.state, "startup_checks", {}),
    }
