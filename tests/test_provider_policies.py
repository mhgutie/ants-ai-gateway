from app.config import get_provider_policies
from app.provider_policies import (
    balance_or_spend_exhausted_statuses,
    canonical_provider,
    provider_policy,
    should_try_next_profile,
)


def test_all_configured_providers_forbid_profile_rotation_on_rate_limit():
    providers = get_provider_policies()["providers"]

    for provider in providers:
        assert should_try_next_profile(provider, 429) is False
        assert provider_policy(provider)["allow_profile_rotation_on_rate_limit"] is False


def test_all_configured_providers_have_sources_and_safe_action():
    providers = get_provider_policies()["providers"]

    for provider, policy in providers.items():
        assert policy["source"], provider
        assert policy["safe_rate_limit_action"], provider


def test_unknown_provider_uses_safe_defaults():
    assert should_try_next_profile("unknown-provider", 401) is True
    assert should_try_next_profile("unknown-provider", 403) is True
    assert should_try_next_profile("unknown-provider", 429) is False


def test_required_family_providers_are_configured():
    providers = get_provider_policies()["providers"]

    for provider in ["qwen", "google", "openai", "anthropic", "deepseek", "kimi", "ollama_cloud"]:
        assert provider in providers


def test_provider_aliases_resolve_to_canonical_policy():
    assert canonical_provider("claude") == "anthropic"
    assert canonical_provider("moonshot") == "kimi"
    assert canonical_provider("ollama") == "ollama_cloud"
    assert should_try_next_profile("claude", 429) is False


def test_balance_exhausted_statuses_are_explicit_where_known():
    assert balance_or_spend_exhausted_statuses("openrouter") == {402}
    assert balance_or_spend_exhausted_statuses("deepseek") == {402}
    assert balance_or_spend_exhausted_statuses("openai") == {402}
