from __future__ import annotations

from typing import Any

from app.config import get_models_config, get_routing_rules
from app.schemas import TaskType


IMPLEMENTED_PROVIDERS = {"openrouter", "qwen", "deepseek", "kimi"}


def list_models() -> dict:
    return get_models_config()


def _task_key(task_type: TaskType | str) -> str:
    return task_type.value if isinstance(task_type, TaskType) else str(task_type)


def model_config(model: str) -> dict[str, Any]:
    return get_models_config()["models"].get(model, {})


def is_model_available(model: str) -> bool:
    model_config = get_models_config()["models"].get(model)
    if not model_config:
        return False
    enabled = bool(model_config.get("enabled", model_config.get("available", False)))
    execution_enabled = bool(model_config.get("execution_enabled", True))
    provider_implemented = provider_for(model) in IMPLEMENTED_PROVIDERS
    return enabled and execution_enabled and provider_implemented


def route_for(task_type: TaskType | str) -> dict[str, str | None]:
    route = get_routing_rules()[_task_key(task_type)]
    if isinstance(route, str):
        return {"primary": route, "fallback": fallback_for(route), "validator": None}
    return {
        "primary": route.get("primary"),
        "fallback": route.get("fallback"),
        "validator": route.get("validator"),
    }


def fallback_for(model: str) -> str | None:
    model_config = get_models_config()["models"].get(model, {})
    fallback = model_config.get("fallback")
    return str(fallback) if fallback else None


def provider_for(model: str) -> str:
    model_config = get_models_config()["models"].get(model, {})
    return str(model_config.get("provider", "openrouter"))


def provider_model_id(model: str) -> str:
    model_config = get_models_config()["models"].get(model, {})
    return str(model_config.get("model_id", model_config.get("provider_model_id", model)))


def select_model(task_type: TaskType | str, requested_model: str = "auto", allow_disabled: bool = False) -> tuple[str, str | None]:
    route = route_for(task_type)
    selected = str(route["primary"]) if requested_model == "auto" else requested_model
    fallback = route["fallback"] if requested_model == "auto" else fallback_for(selected)
    if allow_disabled or is_model_available(selected):
        return selected, fallback
    if fallback and is_model_available(fallback):
        return fallback, fallback
    raise ValueError(f"Model '{selected}' is disabled and no enabled fallback is available.")
