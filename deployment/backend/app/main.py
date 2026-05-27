from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import documents
from app.api.routes import filings
from app.api.routes import health
from app.config import get_settings
from app.services.runtime_checks import check_database, check_llm
from app.services.storage import ensure_storage_directories


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    ensure_storage_directories()
    app.state.startup_checks = {
        "database": await check_database(settings.database_url),
        "llm": await check_llm(settings.llm_base_url),
    }
    yield


app = FastAPI(
    title="Tax Assistant Backend",
    version="0.1.0-phase0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(filings.router)
app.include_router(documents.router)
