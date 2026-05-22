from __future__ import annotations

from app.providers.base import ProviderClient
from app.providers.openrouter import OpenRouterClient
from app.providers.qwen import QwenClient


def get_provider_client(provider: str) -> ProviderClient:
    if provider == "openrouter":
        return OpenRouterClient()
    if provider == "qwen":
        return QwenClient()
    raise NotImplementedError(f"Provider '{provider}' is not implemented in v0.1.")
