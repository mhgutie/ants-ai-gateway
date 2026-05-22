from __future__ import annotations

from math import ceil
from typing import Any


def estimate_tokens_from_text(text: str) -> int:
    return ceil(len(text) / 3)


def _stringify_context(context: dict[str, Any]) -> str:
    return str(context) if context else ""


def estimate_input_tokens(user_request: str, context: dict[str, Any] | None = None) -> int:
    context_text = _stringify_context(context or {})
    return estimate_tokens_from_text(f"{user_request}\n{context_text}")
