import pytest
from fastapi import HTTPException

import app.auth as auth


class _Settings:
    def __init__(self, gateway_api_key):
        self.gateway_api_key = gateway_api_key


def test_gateway_api_key_dependency_requires_configured_key(monkeypatch):
    monkeypatch.setattr(auth, "get_settings", lambda: _Settings(None))

    with pytest.raises(HTTPException) as exc_info:
        auth.require_gateway_api_key(None)
    assert exc_info.value.status_code == 503


def test_gateway_api_key_dependency_rejects_invalid_key(monkeypatch):
    monkeypatch.setattr(auth, "get_settings", lambda: _Settings("valid-key"))

    with pytest.raises(HTTPException) as exc_info:
        auth.require_gateway_api_key("wrong-key")
    assert exc_info.value.status_code == 401


def test_gateway_api_key_dependency_accepts_valid_key(monkeypatch):
    monkeypatch.setattr(auth, "get_settings", lambda: _Settings("valid-key"))

    assert auth.require_gateway_api_key("valid-key") is None
