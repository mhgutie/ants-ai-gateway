from app.providers.base import ProviderClient
from app.providers.openai_compatible import OpenAICompatibleChatMixin


class KimiClient(OpenAICompatibleChatMixin, ProviderClient):
    name = "kimi"
    default_base_url = "https://api.moonshot.ai/v1"
