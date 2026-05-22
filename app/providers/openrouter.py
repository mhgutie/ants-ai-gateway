from app.config import get_settings
from app.providers.base import ProviderClient
from app.providers.openai_compatible import OpenAICompatibleChatMixin


class OpenRouterClient(OpenAICompatibleChatMixin, ProviderClient):
    name = "openrouter"

    @property
    def default_base_url(self) -> str:
        return get_settings().openrouter_base_url
