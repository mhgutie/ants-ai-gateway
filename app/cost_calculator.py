from __future__ import annotations

from app.config import get_models_config


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    model_config = get_models_config()["models"].get(model)
    if model_config is None:
        raise ValueError(f"Unknown model: {model}")
    input_rate = float(model_config.get("input_cost_per_1m_tokens", 0))
    output_rate = float(model_config.get("output_cost_per_1m_tokens", 0))
    cost = (input_tokens / 1_000_000 * input_rate) + (output_tokens / 1_000_000 * output_rate)
    return round(cost, 6)


def real_cost_usd(model: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None or output_tokens is None:
        return None
    return estimate_cost_usd(model, input_tokens, output_tokens)
