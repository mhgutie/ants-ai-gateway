from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
from pathlib import Path

from app.schemas import ExecutorSmokeRequest, ExecutorSmokeResponse
from app.tool_executors import list_executor_sessions, tool_executor_config, tool_executor_status

SMOKE_PROMPT = "Reply exactly: ANTS_EXECUTOR_SMOKE_OK"
SMOKE_EXPECTED = "ANTS_EXECUTOR_SMOKE_OK"
MAX_STDIO_CHARS = 4000
MAX_TIMEOUT_SECONDS = 120
MIN_TIMEOUT_SECONDS = 5


SECRET_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)((?:access|refresh|id|api)[_-]?token['\"]?\s*[:=]\s*['\"]?)[^'\"\s,}]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"),
]


def sanitize_executor_output(value: str) -> str:
    sanitized = value[:MAX_STDIO_CHARS]
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub(lambda match: f"{match.group(1) if match.groups() else ''}[REDACTED]", sanitized)
    return sanitized


def _configured_cli_path(executor: str) -> str:
    config = tool_executor_config(executor)
    cli_path_env = config.get("cli_path_env")
    configured = os.getenv(str(cli_path_env)) if cli_path_env else None
    if configured:
        return configured
    default_by_executor = {
        "codex": "codex",
        "claude_code": "claude",
        "antigravity": "antigravity",
    }
    return default_by_executor.get(executor, executor)


def _allowed_roots(executor: str) -> list[Path]:
    config = tool_executor_config(executor)
    allowed_roots_env = config.get("allowed_roots_env")
    raw_value = os.getenv(str(allowed_roots_env), "") if allowed_roots_env else ""
    return [Path(item.strip()).expanduser().resolve() for item in raw_value.split(",") if item.strip()]


def _workspace_root(executor: str) -> Path | None:
    config = tool_executor_config(executor)
    workspace_root_env = config.get("workspace_root_env")
    raw_value = os.getenv(str(workspace_root_env), "") if workspace_root_env else ""
    return Path(raw_value).expanduser().resolve() if raw_value else None


def _path_is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def resolve_executor_cwd(executor: str, requested_cwd: str | None = None) -> tuple[Path | None, str | None]:
    workspace_root = _workspace_root(executor)
    cwd = Path(requested_cwd).expanduser().resolve() if requested_cwd else workspace_root
    if cwd is None:
        return None, "Workspace root is not configured."
    allowed_roots = _allowed_roots(executor)
    if not allowed_roots:
        return None, "Allowed roots are not configured."
    if not cwd.exists() or not cwd.is_dir():
        return None, "Requested working directory does not exist."
    if not any(_path_is_under(cwd, root) for root in allowed_roots):
        return None, "Requested working directory is outside allowed roots."
    return cwd, None


def executor_session_is_authenticated(executor: str) -> bool:
    sessions = list_executor_sessions().sessions
    return any(session.executor == executor and session.status == "authenticated" for session in sessions)


def build_executor_smoke_command(executor: str, mode: str, cli_path: str) -> list[str]:
    if mode == "version":
        return [cli_path, "--version"]
    if executor == "claude_code":
        return [
            cli_path,
            "-p",
            SMOKE_PROMPT,
            "--output-format",
            "text",
            "--max-turns",
            "1",
        ]
    if executor == "codex":
        return [
            cli_path,
            "exec",
            "--json",
            "--skip-git-repo-check",
            SMOKE_PROMPT,
        ]
    return [cli_path, "--version"]


async def _run_command(command: list[str], cwd: Path, timeout_seconds: int) -> tuple[int | None, str, str, bool]:
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        stdin=subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except TimeoutError:
        process.kill()
        await process.communicate()
        return None, "", "Executor smoke test timed out.", True
    return (
        process.returncode,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
        False,
    )


async def run_executor_smoke(request: ExecutorSmokeRequest) -> ExecutorSmokeResponse:
    executor_status = tool_executor_status(request.executor)
    if not executor_status.enabled:
        return ExecutorSmokeResponse(
            executor=request.executor,
            mode=request.mode,
            passed=False,
            command=[],
            exit_code=None,
            stdout="",
            stderr="",
            reason="Executor is disabled.",
        )
    if request.mode == "prompt" and not executor_session_is_authenticated(request.executor):
        return ExecutorSmokeResponse(
            executor=request.executor,
            mode=request.mode,
            passed=False,
            command=[],
            exit_code=None,
            stdout="",
            stderr="",
            reason="Executor session is not authenticated.",
        )

    cwd, cwd_error = resolve_executor_cwd(request.executor, request.cwd)
    if cwd_error or cwd is None:
        return ExecutorSmokeResponse(
            executor=request.executor,
            mode=request.mode,
            passed=False,
            command=[],
            exit_code=None,
            stdout="",
            stderr="",
            reason=cwd_error or "Invalid working directory.",
        )

    cli_path = _configured_cli_path(request.executor)
    resolved_cli = shutil.which(cli_path) if not Path(cli_path).is_absolute() else cli_path
    if not resolved_cli:
        return ExecutorSmokeResponse(
            executor=request.executor,
            mode=request.mode,
            passed=False,
            command=[cli_path, "--version"],
            exit_code=None,
            stdout="",
            stderr="",
            reason="Executor CLI is not available in the gateway runtime.",
        )

    timeout_seconds = min(max(request.timeout_seconds, MIN_TIMEOUT_SECONDS), MAX_TIMEOUT_SECONDS)
    command = build_executor_smoke_command(request.executor, request.mode, resolved_cli)
    exit_code, stdout, stderr, timed_out = await _run_command(command, cwd, timeout_seconds)
    sanitized_stdout = sanitize_executor_output(stdout)
    sanitized_stderr = sanitize_executor_output(stderr)
    expected_found = request.mode == "version" or SMOKE_EXPECTED in sanitized_stdout
    passed = not timed_out and exit_code == 0 and expected_found
    reason = "Smoke test passed." if passed else "Smoke test failed."
    if timed_out:
        reason = "Smoke test timed out."
    elif request.mode == "prompt" and exit_code == 0 and not expected_found:
        reason = "Smoke prompt completed but expected marker was not found."

    return ExecutorSmokeResponse(
        executor=request.executor,
        mode=request.mode,
        passed=passed,
        command=command,
        exit_code=exit_code,
        stdout=sanitized_stdout,
        stderr=sanitized_stderr,
        reason=reason,
    )
