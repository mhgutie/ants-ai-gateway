from __future__ import annotations

from typing import Any

from app.config import get_models_config, get_routing_rules
from app.schemas import TaskType


def list_models() -> dict:
    return get_models_config()


def _task_key(task_type: TaskType | str) -> str:
    return task_type.value if isinstance(task_type, TaskType) else str(task_type)


def model_config(model: str) -> dict[str, Any]:
    return get_models_config()["models"].get(model, {})


def implemented_providers() -> set[str]:
    models = get_models_config()["models"].values()
    return {
        str(config.get("provider"))
        for config in models
        if config.get("provider") and bool(config.get("execution_enabled", True))
    }


def model_unavailability_reason(model: str) -> str | None:
    config = model_config(model)
    if not config:
        return f"Model '{model}' is not defined in models.yaml."

    enabled = bool(config.get("enabled", config.get("available", False)))
    execution_enabled = bool(config.get("execution_enabled", True))
    if not enabled and not execution_enabled:
        return f"Model '{model}' is disabled in models.yaml and has no execution adapter configured."

    if not enabled:
        return f"Model '{model}' is disabled in models.yaml."

    if not execution_enabled:
        return f"Model '{model}' is enabled in the catalog but has no execution adapter configured."

    provider = provider_for(model)
    if provider not in implemented_providers():
        return f"Provider '{provider}' has no executable models configured in models.yaml."

    return None


def is_model_available(model: str) -> bool:
    return model_unavailability_reason(model) is None


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
    reason = model_unavailability_reason(selected) or f"Model '{selected}' is unavailable."
    raise ValueError(f"{reason} No enabled fallback is available for task '{_task_key(task_type)}'.")
