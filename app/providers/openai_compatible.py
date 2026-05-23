from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.credentials import get_provider_credentials
from app.model_router import provider_model_id
from app.provider_policies import should_try_next_profile
from app.schemas import ChatMessage, ProviderResponse, ProviderUsage


def sanitize_provider_response(payload: dict[str, Any]) -> dict[str, Any]:
    safe = dict(payload)
    safe.pop("authorization", None)
    safe.pop("Authorization", None)
    return safe


class OpenAICompatibleChatMixin:
    name: str
    default_base_url: str

    async def chat(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        max_tokens: int,
        account_id: str | None = None,
    ) -> ProviderResponse:
        settings = get_settings()
        credential_candidates = get_provider_credentials(self.name, account_id)
        if not any(credentials.api_key for credentials in credential_candidates):
            raise RuntimeError(f"{self.name} API key is not configured for the requested profile pool.")

        payload = {
            "model": provider_model_id(model),
            "messages": [message.model_dump() for message in messages],
            "max_tokens": max_tokens,
        }
        last_error: httpx.HTTPStatusError | None = None
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            for credentials in credential_candidates:
                if not credentials.api_key:
                    continue
                base_url = (credentials.base_url or self.default_base_url).rstrip("/")
                headers = {
                    "Authorization": f"Bearer {credentials.api_key}",
                    "Content-Type": "application/json",
                }
                response = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                    if should_try_next_profile(self.name, response.status_code):
                        continue
                    raise
                data = sanitize_provider_response(response.json())
                data.setdefault("ants", {})["profile_id"] = credentials.account_id
                break
            else:
                if last_error:
                    raise last_error
                raise RuntimeError(f"No {self.name} API key is configured for the requested profile pool.")

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage_data = data.get("usage") or {}
        return ProviderResponse(
            provider=self.name,
            model=model,
            content=str(message.get("content") or ""),
            raw=data,
            usage=ProviderUsage(
                input_tokens=usage_data.get("prompt_tokens"),
                output_tokens=usage_data.get("completion_tokens"),
                total_tokens=usage_data.get("total_tokens"),
            ),
        )
