import asyncio
import sys

import app.executor_smoke as executor_smoke
from app.executor_credentials import encrypt_credential_pool, generate_executor_credentials_key
from app.executor_smoke import (
    SMOKE_EXPECTED,
    build_executor_smoke_command,
    resolve_executor_cwd,
    run_executor_smoke,
    sanitize_executor_output,
)
from app.schemas import ExecutorSmokeRequest


def test_sanitize_executor_output_redacts_token_like_values():
    output = "Authorization: Bearer abc.def.ghi\naccess_token=super-secret\nsk-testsecret123456"

    sanitized = sanitize_executor_output(output)

    assert "super-secret" not in sanitized
    assert "sk-testsecret" not in sanitized
    assert "[REDACTED]" in sanitized


def test_resolve_executor_cwd_rejects_path_outside_allowed_roots(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    monkeypatch.setenv("CODEX_WORKSPACE_ROOT", str(allowed))
    monkeypatch.setenv("CODEX_ALLOWED_ROOTS", str(allowed))

    cwd, error = resolve_executor_cwd("codex", str(outside))

    assert cwd is None
    assert error == "Requested working directory is outside allowed roots."


def test_build_codex_prompt_smoke_uses_noninteractive_exec():
    command = build_executor_smoke_command("codex", "prompt", "codex")

    assert command[:2] == ["codex", "exec"]
    assert "--json" in command
    assert "--skip-git-repo-check" in command
    assert command[-1] == "Reply exactly: ANTS_EXECUTOR_SMOKE_OK"


def test_run_executor_smoke_version_passes_with_available_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_EXECUTOR_ENABLED", "true")
    monkeypatch.setenv("CODEX_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("CODEX_ALLOWED_ROOTS", str(tmp_path))
    monkeypatch.setenv("CODEX_CLI_PATH", sys.executable)

    response = asyncio.run(run_executor_smoke(ExecutorSmokeRequest(executor="codex", mode="version")))

    assert response.passed is True
    assert response.exit_code == 0
    assert "Python" in response.stdout or "Python" in response.stderr


def test_run_executor_smoke_prompt_requires_authenticated_session(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_EXECUTOR_ENABLED", "true")
    monkeypatch.setenv("CLAUDE_CODE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CODE_ALLOWED_ROOTS", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CODE_CLI_PATH", sys.executable)

    response = asyncio.run(run_executor_smoke(ExecutorSmokeRequest(executor="claude_code", mode="prompt")))

    assert response.passed is False
    assert response.reason == "Executor session is not authenticated."


def test_run_executor_smoke_prompt_passes_when_marker_is_returned(tmp_path, monkeypatch):
    payload = {
        "version": 1,
        "credential_pool": {"claude-code": [{"label": "claude_ai_oauth", "access_token": "secret"}]},
    }
    key = generate_executor_credentials_key()
    monkeypatch.setenv("ANTS_EXECUTOR_CREDENTIALS_KEY", key)
    monkeypatch.setenv("ANTS_EXECUTOR_CREDENTIAL_POOL_ENC", encrypt_credential_pool(payload, key))
    monkeypatch.setenv("CLAUDE_CODE_EXECUTOR_ENABLED", "true")
    monkeypatch.setenv("CLAUDE_CODE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CODE_ALLOWED_ROOTS", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CODE_CLI_PATH", sys.executable)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_STATUS", "authenticated")

    async def fake_run_command(command, cwd, timeout_seconds):
        return 0, SMOKE_EXPECTED, "", False

    monkeypatch.setattr(executor_smoke, "_run_command", fake_run_command)

    response = asyncio.run(run_executor_smoke(ExecutorSmokeRequest(executor="claude_code", mode="prompt")))

    assert response.passed is True
    assert response.reason == "Smoke test passed."
