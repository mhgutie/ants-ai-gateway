from fastapi.testclient import TestClient

import app.main as main
from app.auth import require_gateway_api_key
from app.main import app


client = TestClient(app)


def _allow_gateway() -> None:
    app.dependency_overrides[require_gateway_api_key] = lambda: None


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_n8n_workflow_run_endpoint_logs_execution(monkeypatch):
    captured = {}

    async def fake_log_workflow_run(payload):
        captured.update(payload)
        return True

    monkeypatch.setattr(main, "log_workflow_run", fake_log_workflow_run)
    _allow_gateway()
    try:
        response = client.post(
            "/n8n/workflow-runs",
            json={
                "run_id": "run-n8n-001",
                "task_id": "ANTS-N8N-001",
                "workflow_name": "spec-intake",
                "n8n_workflow_id": "wf-123",
                "n8n_execution_id": "exec-456",
                "trigger_source": "webhook",
                "status": "success",
                "input_summary": {"source": "n8n"},
                "output_summary": {"created": "spec"},
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json() == {
        "logged": True,
        "run_id": "run-n8n-001",
        "workflow_name": "spec-intake",
    }
    assert captured["n8n_execution_id"] == "exec-456"
    assert captured["input_summary"] == {"source": "n8n"}
    assert "secret" not in str(captured).lower()


def test_n8n_artifact_endpoint_logs_drive_artifact(monkeypatch):
    captured = {}

    async def fake_log_artifact(payload):
        captured.update(payload)
        return True

    monkeypatch.setattr(main, "log_artifact", fake_log_artifact)
    _allow_gateway()
    try:
        response = client.post(
            "/n8n/artifacts",
            json={
                "task_id": "ANTS-N8N-001",
                "run_id": "run-n8n-001",
                "artifact_type": "google_drive_file",
                "name": "handoff.md",
                "uri": "https://drive.google.test/file/123",
                "storage_provider": "google_drive",
                "metadata": {"mime_type": "text/markdown"},
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["logged"] is True
    assert captured["storage_provider"] == "google_drive"
    assert captured["uri"] == "https://drive.google.test/file/123"


def test_n8n_handoff_endpoint_requires_sanitized_context(monkeypatch):
    captured = {}

    async def fake_log_agent_handoff(payload):
        captured.update(payload)
        return True

    monkeypatch.setattr(main, "log_agent_handoff", fake_log_agent_handoff)
    _allow_gateway()
    try:
        response = client.post(
            "/n8n/handoffs",
            json={
                "run_id": "run-n8n-001",
                "task_id": "ANTS-N8N-001",
                "source_agent": "designer",
                "target_agent": "codex",
                "branch": "feat/dashboard",
                "completed": ["Spec and mockup created."],
                "next_steps": ["Implement static UI from mockup."],
                "risks": ["Do not expose API keys."],
                "artifact_links": [{"name": "mockup", "uri": "https://drive.google.test/file/456"}],
                "sanitized_context": "No secrets. Build the dashboard from the approved mockup.",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["target_agent"] == "codex"
    assert captured["sanitized_context"].startswith("No secrets.")
    assert captured["artifact_links"][0]["name"] == "mockup"
