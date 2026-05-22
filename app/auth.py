from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import get_settings


def require_gateway_api_key(x_ants_api_key: str | None = Header(default=None)) -> None:
    configured_key = get_settings().gateway_api_key
    if not configured_key:
        raise HTTPException(status_code=503, detail="ANTS_GATEWAY_API_KEY is not configured.")
    if x_ants_api_key != configured_key:
        raise HTTPException(status_code=401, detail="Invalid ANTS gateway API key.")
