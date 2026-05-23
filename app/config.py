from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "config"


class Settings(BaseModel):
    ants_env: str = os.getenv("ANTS_ENV", "local")
    default_provider: str = os.getenv("ANTS_DEFAULT_PROVIDER", "openrouter")
    gateway_api_key: str | None = os.getenv("ANTS_GATEWAY_API_KEY")
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    supabase_db_url: str | None = os.getenv("SUPABASE_DB_URL")
    request_timeout_seconds: float = float(os.getenv("ANTS_PROVIDER_TIMEOUT_SECONDS", "60"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


@lru_cache
def get_models_config() -> dict[str, Any]:
    return load_yaml("models.yaml")


@lru_cache
def get_budgets_config() -> dict[str, Any]:
    return load_yaml("budgets.yaml")


@lru_cache
def get_routing_rules() -> dict[str, Any]:
    return load_yaml("routing_rules.yaml")


@lru_cache
def get_provider_policies() -> dict[str, Any]:
    return load_yaml("provider_policies.yaml")


@lru_cache
def get_tool_executors_config() -> dict[str, Any]:
    return load_yaml("tool_executors.yaml")


@lru_cache
def get_executor_sessions_config() -> dict[str, Any]:
    path = CONFIG_DIR / "executor_sessions.yaml"
    if path.exists():
        return load_yaml("executor_sessions.yaml")
    return load_yaml("executor_sessions.example.yaml")
