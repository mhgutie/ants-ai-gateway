from __future__ import annotations

import logging
from typing import Any

from app.db import db_connection
from app.schemas import UsageLogRequest

logger = logging.getLogger(__name__)


def sanitize_log_payload(payload: dict[str, Any]) -> dict[str, Any]:
    blocked = {"authorization", "api_key", "token", "password", "secret"}
    return {key: ("[REDACTED]" if key.lower() in blocked else value) for key, value in payload.items()}


async def log_usage(payload: UsageLogRequest) -> bool:
    data = sanitize_log_payload(payload.model_dump())
    try:
        async with db_connection() as connection:
            if connection is None:
                logger.info("model_usage", extra={"model_usage": data})
                return False
            await connection.execute(
                """
                insert into model_usage (
                    task_id, run_id, provider, model, task_type,
                    input_tokens_estimated, input_tokens_real, output_tokens_real,
                    total_tokens_real, estimated_cost_usd, real_cost_usd, status, stop_reason
                )
                values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                """,
                payload.task_id,
                payload.run_id,
                payload.provider,
                payload.model,
                payload.task_type.value,
                payload.input_tokens_estimated,
                payload.input_tokens_real,
                payload.output_tokens_real,
                payload.total_tokens_real,
                payload.estimated_cost_usd,
                payload.real_cost_usd,
                payload.status,
                payload.stop_reason,
            )
    except Exception:
        logger.exception("model_usage_log_failed", extra={"model_usage": data})
        return False
    return True
