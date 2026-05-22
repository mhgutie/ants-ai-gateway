import asyncio

import pytest

pytest.importorskip("asyncpg")

import app.services.usage_logger as usage_logger
from app.schemas import TaskType, UsageLogRequest


def _usage_payload():
    return UsageLogRequest(
        task_id="task-1",
        run_id="run-1",
        provider="qwen",
        model="qwen3-coder",
        task_type=TaskType.coding_debug,
        input_tokens_estimated=10,
        estimated_cost_usd=0.001,
        status="error",
        stop_reason="HTTPStatusError",
    )


def test_usage_logger_returns_false_when_db_logging_fails(monkeypatch):
    class _BrokenContext:
        async def __aenter__(self):
            raise OSError("db unavailable")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(usage_logger, "db_connection", lambda: _BrokenContext())

    assert asyncio.run(usage_logger.log_usage(_usage_payload())) is False
