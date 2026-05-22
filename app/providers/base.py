from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas import ChatMessage, ProviderResponse


class ProviderClient(ABC):
    name: str

    @abstractmethod
    async def chat(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        max_tokens: int,
        account_id: str | None = None,
    ) -> ProviderResponse:
        raise NotImplementedError
