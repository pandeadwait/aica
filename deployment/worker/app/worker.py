from __future__ import annotations

import asyncio
import json

from app.config import get_settings
from app.runtime_checks import check_database, check_llm


async def run() -> None:
    settings = get_settings()
    startup_status = {
        "database": await check_database(settings.database_url),
        "llm": await check_llm(settings.llm_base_url),
        "model": settings.llm_model,
    }
    print(json.dumps({"worker": "phase0", "startup": startup_status}))

    while True:
        heartbeat = {
            "database": await check_database(settings.database_url),
            "llm": await check_llm(settings.llm_base_url),
        }
        print(json.dumps({"worker": "phase0-heartbeat", "checks": heartbeat}))
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run())
