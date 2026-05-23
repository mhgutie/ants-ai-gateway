from app.providers.base import ProviderClient


class NvidiaNimClient(ProviderClient):
    name = "nvidia_nim"

    async def chat(self, *, model, messages, max_tokens, account_id=None):
        raise NotImplementedError("NVIDIA NIM provider is a v0.1 stub. Use OpenRouter.")
