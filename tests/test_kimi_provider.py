import asyncio

import pytest

from app.providers.kimi import KimiClient
from app.schemas import ChatMessage


def test_kimi_provider_uses_direct_openai_compatible_endpoint(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "ANTS_KIMI_OK"}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 4, "total_tokens": 11},
            }

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setenv("KIMI_API_KEY", "kimi-test-key")
    monkeypatch.setattr("app.providers.openai_compatible.httpx.AsyncClient", FakeClient)

    response = asyncio.run(
        KimiClient().chat(
            model="kimi-k2.6",
            messages=[ChatMessage(role="user", content="ping")],
            max_tokens=16,
        )
    )

    assert captured["url"] == "https://api.moonshot.ai/v1/chat/completions"
    assert captured["json"]["model"] == "kimi-k2.6"
    assert captured["headers"]["Authorization"] == "Bearer kimi-test-key"
    assert response.provider == "kimi"
    assert response.content == "ANTS_KIMI_OK"
    assert response.usage.total_tokens == 11


def test_kimi_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    monkeypatch.delenv("KIMI__DEFAULT__API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="kimi API key is not configured"):
        asyncio.run(
            KimiClient().chat(
                model="kimi-k2.6",
                messages=[ChatMessage(role="user", content="ping")],
                max_tokens=16,
            )
        )
