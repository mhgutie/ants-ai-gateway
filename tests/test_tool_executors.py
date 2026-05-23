from app.config import get_tool_executors_config
from app.executor_credentials import encrypt_credential_pool, generate_executor_credentials_key
from app.tool_executors import (
    executor_uses_external_auth_store,
    is_tool_executor_enabled,
    list_tool_executor_statuses,
    list_executor_sessions,
    tool_executor_config,
    tool_executor_status,
)


def test_codex_executor_policy_uses_external_auth_store():
    codex = tool_executor_config("codex")

    assert codex["role"] == "repository_executor"
    assert codex["auth_mode_default"] == "chatgpt"
    assert executor_uses_external_auth_store("codex") is True
    assert "access_token" not in codex
    assert "refresh_token" not in codex
    assert "id_token" not in codex
    assert "do not store" in codex["notes"].lower()


def test_executor_enabled_reads_environment(monkeypatch):
    monkeypatch.setenv("CODEX_EXECUTOR_ENABLED", "true")
    monkeypatch.setenv("ANTIGRAVITY_EXECUTOR_ENABLED", "false")

    assert is_tool_executor_enabled("codex") is True
    assert is_tool_executor_enabled("antigravity") is False


def test_tool_executor_config_includes_expected_executors():
    executors = get_tool_executors_config()["executors"]

    assert {"codex", "claude_code", "antigravity"} <= set(executors)


def test_live_executor_requires_explicit_approval():
    antigravity = tool_executor_config("antigravity")

    assert antigravity["requires_approval_for_shell"] is True
    assert antigravity["requires_approval_for_browser"] is True


def test_claude_code_executor_is_configured_as_external_auth_executor():
    claude_code = tool_executor_config("claude_code")

    assert claude_code["role"] == "coding_subprocess_executor"
    assert executor_uses_external_auth_store("claude_code") is True
    assert claude_code["requires_spec"] is True
    assert claude_code["requires_harness"] is True


def test_tool_executor_status_is_safe_and_serializable(monkeypatch):
    monkeypatch.setenv("CODEX_EXECUTOR_ENABLED", "true")
    monkeypatch.setenv("CODEX_AUTH_MODE", "chatgpt")

    status = tool_executor_status("codex")

    assert status.enabled is True
    assert status.auth_mode == "chatgpt"
    assert status.uses_external_auth_store is True
    assert "token" not in status.model_dump()


def test_list_tool_executor_statuses_includes_all_executors():
    response = list_tool_executor_statuses()
    names = {executor.name for executor in response.executors}

    assert {"codex", "claude_code", "antigravity"} <= names


def test_executor_sessions_list_safe_metadata_only():
    response = list_executor_sessions()
    session_refs = {session.session_ref for session in response.sessions}
    serialized = response.model_dump()

    assert {"codex-local-default", "claude-code-local-default", "antigravity-local-default"} <= session_refs
    assert "access_token" not in str(serialized).lower()
    assert "refresh_token" not in str(serialized).lower()
    assert "id_token" not in str(serialized).lower()


def test_executor_sessions_start_pending_auth():
    response = list_executor_sessions()

    assert {session.status for session in response.sessions} == {"pending_auth"}
    assert all(session.credential_storage.startswith("external_") for session in response.sessions)


def test_executor_sessions_infer_configured_when_credentials_and_roots_are_configured(monkeypatch):
    payload = {
        "version": 1,
        "active_provider": "openai-codex",
        "credential_pool": {
            "openai-codex": [{"label": "device_code", "access_token": "secret"}],
            "claude-code": [{"label": "claude_ai_oauth", "access_token": "secret"}],
        },
    }
    key = generate_executor_credentials_key()
    monkeypatch.setenv("ANTS_EXECUTOR_CREDENTIALS_KEY", key)
    monkeypatch.setenv("ANTS_EXECUTOR_CREDENTIAL_POOL_ENC", encrypt_credential_pool(payload, key))
    monkeypatch.setenv("CODEX_EXECUTOR_ENABLED", "true")
    monkeypatch.setenv("CODEX_WORKSPACE_ROOT", "/root/ants-workspaces")
    monkeypatch.setenv("CODEX_ALLOWED_ROOTS", "/root/ants-workspaces,/root/ants-apps")
    monkeypatch.setenv("CLAUDE_CODE_EXECUTOR_ENABLED", "true")
    monkeypatch.setenv("CLAUDE_CODE_WORKSPACE_ROOT", "/root/ants-workspaces")
    monkeypatch.setenv("CLAUDE_CODE_ALLOWED_ROOTS", "/root/ants-workspaces,/root/ants-apps")

    response = list_executor_sessions()
    sessions_by_executor = {session.executor: session for session in response.sessions}

    assert sessions_by_executor["codex"].status == "configured"
    assert sessions_by_executor["claude_code"].status == "configured"
    assert "live authentication still requires" in sessions_by_executor["codex"].last_status_reason.lower()
    assert sessions_by_executor["codex"].workspace_root_configured is True
    assert sessions_by_executor["claude_code"].allowed_roots_configured is True
    assert sessions_by_executor["antigravity"].status == "pending_auth"


def test_executor_session_status_can_be_marked_authenticated_after_external_smoke(monkeypatch):
    monkeypatch.setenv("CODEX_SESSION_STATUS", "authenticated")

    response = list_executor_sessions()
    codex_session = next(session for session in response.sessions if session.executor == "codex")

    assert codex_session.status == "authenticated"


def test_executor_session_status_can_be_overridden_by_environment(monkeypatch):
    monkeypatch.setenv("CODEX_SESSION_STATUS", "expired")

    response = list_executor_sessions()
    codex_session = next(session for session in response.sessions if session.executor == "codex")

    assert codex_session.status == "expired"
