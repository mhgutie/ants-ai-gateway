from app.schemas import ContextScope, PreflightRequest, TaskType
from app.services.preflight_service import run_preflight


def _request(**overrides):
    data = {
        "task_id": "task-1",
        "task_type": TaskType.classification,
        "user_request": "Fix this small bug.",
        "context": {},
        "requested_context_scope": ContextScope.limited,
    }
    data.update(overrides)
    return PreflightRequest(**data)


def test_blocks_when_estimated_tokens_exceed_128000():
    response = run_preflight(_request(user_request="x" * 384_004, budget={"max_input_tokens_per_call": 200_000}))
    assert response.allowed is False
    assert "summarize_or_rag_first" in response.stop_rules


def test_blocks_when_estimated_cost_exceeds_budget():
    response = run_preflight(
        _request(
            user_request="x" * 30_000,
            budget={"max_total_cost_usd": 0.0001, "max_input_tokens_per_call": 20_000},
        )
    )
    assert response.allowed is False
    assert "estimated_cost_exceeds_budget" in response.stop_rules


def test_refuses_full_repo_without_explicit_authorization():
    response = run_preflight(_request(requested_context_scope=ContextScope.full_repo, explicitly_authorized=False))
    assert response.allowed is False
    assert "full_repo_requires_explicit_authorization" in response.stop_rules


def test_allows_full_repo_with_explicit_authorization_if_other_limits_pass():
    response = run_preflight(_request(requested_context_scope=ContextScope.full_repo, explicitly_authorized=True))
    assert response.allowed is True


def test_disabled_model_route_blocks_in_preflight_without_crashing():
    response = run_preflight(_request(task_type=TaskType.text_to_speech))
    assert response.allowed is False
    assert response.recommended_model == "gemini-tts"
    assert "model_unavailable" in response.stop_rules


def test_new_task_type_is_accepted_by_preflight():
    response = run_preflight(_request(task_type=TaskType.google_workspace_processing))
    assert response.allowed is False
    assert response.recommended_model == "gemini-3.5-flash"
    assert "model_unavailable" in response.stop_rules
