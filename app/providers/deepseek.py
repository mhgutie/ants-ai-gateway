from app.providers.base import ProviderClient
from app.providers.openai_compatible import OpenAICompatibleChatMixin


class DeepSeekClient(OpenAICompatibleChatMixin, ProviderClient):
    name = "deepseek"
    default_base_url = "https://api.deepseek.com"
