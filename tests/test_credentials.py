from app.credentials import (
    account_resolution_order,
    credential_env_names,
    get_provider_credentials,
    get_provider_secret,
    normalize_account_id,
)
from app.schemas import ChatRequest, TaskType


def test_account_id_is_normalized_for_environment_names():
    assert normalize_account_id("1") == "1"
    assert normalize_account_id("mi familia") == "MI_FAMILIA"
    assert normalize_account_id("señora") == "SENORA"
    assert normalize_account_id(None) == "DEFAULT"


def clean_qwen_env(monkeypatch):
    import os
    for key in list(os.environ.keys()):
        if key.startswith("QWEN__") or key == "QWEN_API_KEY":
            monkeypatch.delenv(key, raising=False)


def test_provider_secret_prefers_account_specific_key(monkeypatch):
    clean_qwen_env(monkeypatch)
    monkeypatch.setenv("QWEN__DEFAULT__API_KEY", "default-key")
    monkeypatch.setenv("QWEN__1__API_KEY", "profile-1-key")

    assert get_provider_secret("qwen", "1", "api_key") == "profile-1-key"
    assert get_provider_secret("qwen", "2", "api_key") == "profile-1-key"


def test_default_profile_pool_uses_profiles_before_default(monkeypatch):
    clean_qwen_env(monkeypatch)
    monkeypatch.setenv("QWEN__DEFAULT__API_KEY", "default-key")
    monkeypatch.setenv("QWEN__2__API_KEY", "profile-2-key")

    credentials = get_provider_credentials("qwen", None)

    assert [item.account_id for item in credentials] == ["2", "DEFAULT"]
    assert get_provider_secret("qwen", None, "api_key") == "profile-2-key"


def test_explicit_profile_is_tried_before_remaining_pool(monkeypatch):
    clean_qwen_env(monkeypatch)
    monkeypatch.setenv("QWEN__1__API_KEY", "profile-1-key")
    monkeypatch.setenv("QWEN__3__API_KEY", "profile-3-key")

    credentials = get_provider_credentials("qwen", "3")

    assert [item.account_id for item in credentials] == ["3", "1"]
    assert get_provider_secret("qwen", "3", "api_key") == "profile-3-key"


def test_account_resolution_order_defaults_to_family_token_pool():
    assert account_resolution_order(None) == ["1", "2", "3", "4", "DEFAULT"]
    assert account_resolution_order("3") == ["3", "1", "2", "4", "DEFAULT"]


def test_legacy_provider_secret_name_remains_supported(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "legacy-key")

    assert get_provider_secret("openrouter", "missing", "api_key") == "legacy-key"


def test_credential_env_name_lookup_order():
    assert credential_env_names("qwen", "1", "api_key") == [
        "QWEN__1__API_KEY",
        "QWEN__DEFAULT__API_KEY",
        "QWEN_API_KEY",
    ]


def test_chat_request_accepts_account_id_without_secret_payload():
    request = ChatRequest(
        task_id="task-1",
        task_type=TaskType.classification,
        user_request="Clasifica esto.",
        account_id="1",
    )

    assert request.account_id == "1"
