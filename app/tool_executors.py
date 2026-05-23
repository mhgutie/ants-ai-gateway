from __future__ import annotations

import os
from typing import Any

from app.config import get_executor_sessions_config, get_tool_executors_config
from app.executor_credentials import load_executor_credential_pool_status
from app.schemas import ExecutorSessionStatus, ExecutorSessionsResponse, ToolExecutorStatus, ToolExecutorsResponse


def tool_executor_config(executor: str) -> dict[str, Any]:
    config = get_tool_executors_config()
    defaults = config.get("defaults", {})
    executor_data = config.get("executors", {}).get(executor, {})
    return {**defaults, **executor_data}


def is_tool_executor_enabled(executor: str) -> bool:
    config = tool_executor_config(executor)
    enabled_env = config.get("enabled_env")
    if not enabled_env:
        return False
    return os.getenv(str(enabled_env), "false").strip().lower() in {"1", "true", "yes", "on"}


def executor_uses_external_auth_store(executor: str) -> bool:
    credential_storage = str(tool_executor_config(executor).get("credential_storage", ""))
    return credential_storage.startswith("external_")


def _env_is_configured(env_name: str | None) -> bool:
    return bool(env_name and os.getenv(env_name))


def tool_executor_status(executor: str) -> ToolExecutorStatus:
    config = tool_executor_config(executor)
    auth_mode_env = config.get("auth_mode_env")
    workspace_root_env = config.get("workspace_root_env")
    allowed_roots_env = config.get("allowed_roots_env")
    return ToolExecutorStatus(
        name=executor,
        enabled=is_tool_executor_enabled(executor),
        role=str(config.get("role", "")),
        execution_mode=str(config.get("execution_mode", "guarded")),
        auth_mode=os.getenv(str(auth_mode_env), str(config.get("auth_mode_default", ""))) if auth_mode_env else "",
        credential_storage=str(config.get("credential_storage", "")),
        uses_external_auth_store=executor_uses_external_auth_store(executor),
        requires_spec=bool(config.get("requires_spec", True)),
        requires_harness=bool(config.get("requires_harness", True)),
        allow_shell=bool(config.get("allow_shell", False)),
        allow_browser=bool(config.get("allow_browser", False)),
        block_destructive_commands=bool(config.get("block_destructive_commands", True)),
        sanitize_secrets=bool(config.get("sanitize_secrets", True)),
        workspace_root_configured=_env_is_configured(str(workspace_root_env) if workspace_root_env else None),
        allowed_roots_configured=_env_is_configured(str(allowed_roots_env) if allowed_roots_env else None),
        notes=str(config.get("notes", "")),
    )


def list_tool_executor_statuses() -> ToolExecutorsResponse:
    config = get_tool_executors_config()
    return ToolExecutorsResponse(
        policy_version=str(config.get("policy_version", "")),
        executors=[tool_executor_status(executor) for executor in config.get("executors", {})],
    )


def _list_value_is_configured(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


SESSION_CREDENTIAL_PROVIDERS = {
    "codex": "openai-codex",
    "claude_code": "claude-code",
}


def _status_from_env(executor: str) -> str | None:
    env_name = f"{executor.upper()}_SESSION_STATUS"
    value = os.getenv(env_name)
    if not value:
        return None
    normalized = value.strip().lower()
    return normalized if normalized in {"pending_auth", "configured", "authenticated", "expired", "failed", "disabled"} else None


def _session_status_reason(
    session: dict[str, Any],
    executor_status: ToolExecutorStatus,
    has_encrypted_credentials: bool,
) -> str:
    if not executor_status.enabled:
        return "Executor is disabled in gateway environment."
    if not executor_status.workspace_root_configured or not executor_status.allowed_roots_configured:
        return "Executor workspace root or allowed roots are not configured."
    if has_encrypted_credentials:
        return (
            "Executor enabled with configured workspace roots and encrypted credential reference. "
            "Live authentication still requires a successful CLI smoke test or explicit session status override."
        )
    return str(session.get("last_status_reason", "Pending executor authentication metadata."))


def executor_session_status(session: dict[str, Any]) -> ExecutorSessionStatus:
    executor = str(session.get("executor", ""))
    executor_status = tool_executor_status(executor)
    credential_status = load_executor_credential_pool_status()
    credential_provider = SESSION_CREDENTIAL_PROVIDERS.get(executor)
    has_encrypted_credentials = bool(
        credential_status.configured
        and credential_status.decryptable
        and credential_provider
        and credential_status.credential_counts.get(credential_provider, 0) > 0
    )
    status_override = _status_from_env(executor)
    inferred_status = (
        "configured"
        if executor_status.enabled
        and executor_status.workspace_root_configured
        and executor_status.allowed_roots_configured
        and has_encrypted_credentials
        else session.get("status", "pending_auth")
    )
    return ExecutorSessionStatus(
        executor=executor,
        session_ref=str(session.get("session_ref", "")),
        label=str(session.get("label", "")),
        auth_mode=str(session.get("auth_mode", "")),
        status=status_override or inferred_status,
        credential_storage=executor_status.credential_storage or str(session.get("credential_storage", "")),
        workspace_root_configured=executor_status.workspace_root_configured or bool(session.get("workspace_root")),
        allowed_roots_configured=executor_status.allowed_roots_configured
        or _list_value_is_configured(session.get("allowed_roots")),
        last_checked_at=session.get("last_checked_at"),
        last_status_reason=_session_status_reason(session, executor_status, has_encrypted_credentials),
    )


def list_executor_sessions() -> ExecutorSessionsResponse:
    config = get_executor_sessions_config()
    return ExecutorSessionsResponse(
        schema_version=str(config.get("schema_version", "")),
        sessions=[executor_session_status(session) for session in config.get("sessions", [])],
    )
