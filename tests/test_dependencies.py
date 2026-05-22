import asyncio
import socket

import pytest

pytest.importorskip("asyncpg")

import app.db as db


class _Settings:
    def __init__(self, supabase_db_url):
        self.supabase_db_url = supabase_db_url


def test_db_status_reports_not_configured(monkeypatch):
    monkeypatch.setattr(db, "get_settings", lambda: _Settings(None))

    status = asyncio.run(db.db_status())

    assert status == {"configured": False, "reachable": False, "status": "not_configured"}


def test_db_status_reports_connection_error(monkeypatch):
    class _BrokenContext:
        async def __aenter__(self):
            raise OSError("db unavailable")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(db, "get_settings", lambda: _Settings("postgresql://example"))
    monkeypatch.setattr(db, "db_connection", lambda: _BrokenContext())

    status = asyncio.run(db.db_status())

    assert status["configured"] is True
    assert status["reachable"] is False
    assert status["status"] == "error"
    assert status["error_type"] == "OSError"
    assert status["target"]["host"] == "example"
    assert "Database network connection failed" in status["hint"]


def test_db_status_reports_dns_error_without_leaking_credentials(monkeypatch):
    class _BrokenContext:
        async def __aenter__(self):
            raise socket.gaierror("temporary failure")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(db, "get_settings", lambda: _Settings("postgresql://user:secret@example.local:5432/postgres"))
    monkeypatch.setattr(db, "db_connection", lambda: _BrokenContext())

    status = asyncio.run(db.db_status())

    assert status["error_type"] == "gaierror"
    assert status["target"] == {
        "scheme": "postgresql",
        "host": "example.local",
        "port": 5432,
        "database": "postgres",
    }
    assert "secret" not in str(status)
    assert "could not be resolved" in status["hint"]
