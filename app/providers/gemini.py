from app.providers.base import ProviderClient


class GeminiClient(ProviderClient):
    name = "gemini"

    async def chat(self, *, model, messages, max_tokens, account_id=None):
        raise NotImplementedError("Gemini direct provider is a v0.1 stub. Use OpenRouter.")
