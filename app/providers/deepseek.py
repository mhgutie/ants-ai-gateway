from app.providers.base import ProviderClient


class DeepSeekClient(ProviderClient):
    name = "deepseek"

    async def chat(self, *, model, messages, max_tokens, account_id=None):
        raise NotImplementedError("DeepSeek direct provider is a v0.1 stub. Use OpenRouter.")
