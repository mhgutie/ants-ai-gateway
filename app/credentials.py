from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass


_SAFE_ENV_CHARS = re.compile(r"[^A-Z0-9_]+")


@dataclass(frozen=True)
class ProviderCredentials:
    account_id: str
    api_key: str | None
    base_url: str | None


def normalize_account_id(account_id: str | None) -> str:
    raw_account = (account_id or "default").strip()
    normalized = unicodedata.normalize("NFKD", raw_account)
    account = normalized.encode("ascii", "ignore").decode("ascii").upper()
    account = _SAFE_ENV_CHARS.sub("_", account)
    return account.strip("_") or "DEFAULT"


def profile_sequence() -> list[str]:
    raw_profiles = os.getenv("ANTS_PROFILE_SEQUENCE", "1,2,3,4").split(",")
    profiles = [normalize_account_id(profile) for profile in raw_profiles if profile.strip()]
    return profiles or ["1", "2", "3", "4"]


def account_resolution_order(account_id: str | None) -> list[str]:
    requested = normalize_account_id(account_id)
    sequence = profile_sequence()
    ordered = []
    if requested != "DEFAULT":
        ordered.append(requested)
    ordered.extend(profile for profile in sequence if profile not in ordered)
    ordered.append("DEFAULT")
    return ordered


def credential_env_names(provider: str, account_id: str | None, suffix: str) -> list[str]:
    provider_key = provider.strip().upper()
    account_key = normalize_account_id(account_id)
    suffix_key = suffix.strip().upper()
    names = [f"{provider_key}__{account_key}__{suffix_key}"]
    if account_key != "DEFAULT":
        names.append(f"{provider_key}__DEFAULT__{suffix_key}")
    names.append(f"{provider_key}_{suffix_key}")
    return names


def _direct_provider_secret(provider: str, account_id: str, suffix: str, *, include_legacy: bool = False) -> str | None:
    provider_key = provider.strip().upper()
    account_key = normalize_account_id(account_id)
    suffix_key = suffix.strip().upper()
    env_names = [f"{provider_key}__{account_key}__{suffix_key}"]
    if include_legacy:
        env_names.append(f"{provider_key}_{suffix_key}")
    for env_name in env_names:
        value = os.getenv(env_name)
        if value:
            return value
    return None


def get_provider_credentials(provider: str, account_id: str | None) -> list[ProviderCredentials]:
    credentials = []
    default_base_url = _direct_provider_secret(provider, "DEFAULT", "base_url", include_legacy=True)
    for resolved_account_id in account_resolution_order(account_id):
        api_key = _direct_provider_secret(
            provider,
            resolved_account_id,
            "api_key",
            include_legacy=resolved_account_id == "DEFAULT",
        )
        base_url = _direct_provider_secret(
            provider,
            resolved_account_id,
            "base_url",
            include_legacy=resolved_account_id == "DEFAULT",
        )
        base_url = base_url or default_base_url
        if api_key or base_url:
            credentials.append(
                ProviderCredentials(
                    account_id=resolved_account_id,
                    api_key=api_key,
                    base_url=base_url,
                )
            )
    return credentials


def get_provider_secret(provider: str, account_id: str | None, suffix: str) -> str | None:
    for credentials in get_provider_credentials(provider, account_id):
        value = credentials.api_key if suffix.strip().lower() == "api_key" else credentials.base_url
        if value:
            return value
    return None
