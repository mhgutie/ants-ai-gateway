from __future__ import annotations

import logging
import socket
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from urllib.parse import urlparse

import asyncpg

from app.config import get_settings

logger = logging.getLogger(__name__)


def sanitized_database_target(database_url: str | None) -> dict[str, str | int | None]:
    if not database_url:
        return {"scheme": None, "host": None, "port": None, "database": None}
    parsed = urlparse(database_url)
    try:
        port = parsed.port
    except ValueError:
        port = None
    return {
        "scheme": parsed.scheme or None,
        "host": parsed.hostname,
        "port": port,
        "database": parsed.path.lstrip("/") or None,
    }


def db_error_hint(exc: Exception) -> str:
    if isinstance(exc, socket.gaierror):
        return "Database hostname could not be resolved from the gateway runtime."
    if isinstance(exc, (ConnectionRefusedError, TimeoutError, OSError)):
        return "Database network connection failed from the gateway runtime."
    return "Database check failed."


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
    target = sanitized_database_target(database_url)
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
            "target": target,
            "hint": db_error_hint(exc),
        }
    return {"configured": True, "reachable": True, "status": "ok", "target": target}
