import asyncio

import pytest

from app.providers.deepseek import DeepSeekClient
from app.schemas import ChatMessage


def test_deepseek_provider_uses_direct_openai_compatible_endpoint(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "ANTS_DEEPSEEK_OK"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
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

    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-test-key")
    monkeypatch.setattr("app.providers.openai_compatible.httpx.AsyncClient", FakeClient)

    response = asyncio.run(
        DeepSeekClient().chat(
            model="deepseek-v4-flash",
            messages=[ChatMessage(role="user", content="ping")],
            max_tokens=16,
        )
    )

    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["json"]["model"] == "deepseek-v4-flash"
    assert captured["headers"]["Authorization"] == "Bearer deepseek-test-key"
    assert response.provider == "deepseek"
    assert response.content == "ANTS_DEEPSEEK_OK"
    assert response.usage.total_tokens == 8


def test_deepseek_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK__DEFAULT__API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="deepseek API key is not configured"):
        asyncio.run(
            DeepSeekClient().chat(
                model="deepseek-v4-flash",
                messages=[ChatMessage(role="user", content="ping")],
                max_tokens=16,
            )
        )
