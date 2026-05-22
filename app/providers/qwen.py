from app.providers.base import ProviderClient
from app.providers.openai_compatible import OpenAICompatibleChatMixin


class QwenClient(OpenAICompatibleChatMixin, ProviderClient):
    name = "qwen"
    default_base_url = "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
