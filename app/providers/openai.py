from app.providers.base import ProviderClient


class OpenAIClient(ProviderClient):
    name = "openai"

    async def chat(self, *, model, messages, max_tokens, account_id=None):
        raise NotImplementedError("OpenAI provider is a v0.1 stub. Use OpenRouter.")
