from app.providers.base import ProviderClient


class KimiClient(ProviderClient):
    name = "kimi"

    async def chat(self, *, model, messages, max_tokens, account_id=None):
        raise NotImplementedError("Kimi direct provider is a v0.1 stub. Use OpenRouter.")
