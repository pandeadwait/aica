from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def check_database(database_url: str) -> dict[str, Any]:
    async_database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_async_engine(async_database_url, future=True)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            return {"ok": bool(result.scalar())}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        await engine.dispose()


async def check_llm(llm_base_url: str) -> dict[str, Any]:
    url = llm_base_url.rstrip("/") + "/api/tags"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

