from __future__ import annotations

from typing import Any

from app.config import get_provider_policies


def canonical_provider(provider: str) -> str:
    policies = get_provider_policies()
    if provider in policies.get("providers", {}):
        return provider
    for provider_name, provider_data in policies.get("providers", {}).items():
        if provider in provider_data.get("aliases", []):
            return str(provider_name)
    return provider


def provider_policy(provider: str) -> dict[str, Any]:
    policies = get_provider_policies()
    defaults = policies.get("defaults", {})
    provider_data = policies.get("providers", {}).get(canonical_provider(provider), {})
    return {**defaults, **provider_data}


def rate_limit_statuses(provider: str) -> set[int]:
    return {int(status) for status in provider_policy(provider).get("rate_limit_statuses", [])}


def profile_fallback_statuses(provider: str) -> set[int]:
    return {int(status) for status in provider_policy(provider).get("profile_fallback_statuses", [])}


def balance_or_spend_exhausted_statuses(provider: str) -> set[int]:
    return {int(status) for status in provider_policy(provider).get("balance_or_spend_exhausted_statuses", [])}


def allow_profile_rotation_on_rate_limit(provider: str) -> bool:
    return bool(provider_policy(provider).get("allow_profile_rotation_on_rate_limit", False))


def should_try_next_profile(provider: str, status_code: int) -> bool:
    if status_code in rate_limit_statuses(provider):
        return allow_profile_rotation_on_rate_limit(provider)
    return status_code in profile_fallback_statuses(provider)
