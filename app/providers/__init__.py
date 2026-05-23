from __future__ import annotations

from app.providers.base import ProviderClient
from app.providers.deepseek import DeepSeekClient
from app.providers.kimi import KimiClient
from app.providers.openrouter import OpenRouterClient
from app.providers.qwen import QwenClient


def get_provider_client(provider: str) -> ProviderClient:
    if provider == "openrouter":
        return OpenRouterClient()
    if provider == "qwen":
        return QwenClient()
    if provider == "deepseek":
        return DeepSeekClient()
    if provider == "kimi":
        return KimiClient()
    raise NotImplementedError(f"Provider '{provider}' is not implemented in v0.1.")
