from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg

from app.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def db_connection() -> AsyncIterator[asyncpg.Connection | None]:
    database_url = get_settings().supabase_db_url
    if not database_url:
        yield None
        return
    connection = await asyncpg.connect(database_url)
    try:
        yield connection
    finally:
        await connection.close()


async def db_status() -> dict[str, str | bool]:
    database_url = get_settings().supabase_db_url
    if not database_url:
        return {"configured": False, "reachable": False, "status": "not_configured"}
    try:
        async with db_connection() as connection:
            if connection is None:
                return {"configured": False, "reachable": False, "status": "not_configured"}
            await connection.fetchval("select 1")
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "status": "error",
            "error_type": exc.__class__.__name__,
        }
    return {"configured": True, "reachable": True, "status": "ok"}
