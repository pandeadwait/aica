from __future__ import annotations

import asyncio
import json

import httpx

from app.config import get_settings
from app.runtime_checks import check_database, check_llm


async def run_next_processing_job(backend_base_url: str) -> dict[str, object]:
    url = backend_base_url.rstrip("/") + "/internal/processing/run-next"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url)
        response.raise_for_status()
        return response.json()


async def run() -> None:
    settings = get_settings()
    startup_status = {
        "database": await check_database(settings.database_url),
        "llm": await check_llm(settings.llm_base_url),
        "model": settings.llm_model,
        "backend_base_url": settings.backend_base_url,
    }
    print(json.dumps({"worker": "phase4", "startup": startup_status}))

    while True:
        heartbeat = {
            "database": await check_database(settings.database_url),
            "llm": await check_llm(settings.llm_base_url),
        }
        processing = await run_next_processing_job(settings.backend_base_url)
        print(
            json.dumps(
                {
                    "worker": "phase4-heartbeat",
                    "checks": heartbeat,
                    "processing": processing,
                }
            )
        )
        await asyncio.sleep(settings.processing_poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(run())
