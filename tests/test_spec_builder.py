"""Tests for Phase 5: Spec Builder service and endpoint."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas import ContextScope, SpecBuildRequest, TaskType
from app.services.spec_builder_service import _extract_json, build_spec


# ---------------------------------------------------------------------------
# Unit: JSON extraction
# ---------------------------------------------------------------------------

def test_extract_json_from_plain_text():
    raw = '{"title": "Test", "score": 95}'
    result = _extract_json(raw)
    assert result["title"] == "Test"
    assert result["score"] == 95


def test_extract_json_strips_markdown_fences():
    raw = "```json\n{\"title\": \"Spec\"}\n```"
    result = _extract_json(raw)
    assert result["title"] == "Spec"


def test_extract_json_raises_on_missing_json():
    with pytest.raises(ValueError, match="No JSON object found"):
        _extract_json("This is plain text with no JSON.")


# ---------------------------------------------------------------------------
# Unit: build_spec — blocked preflight
# ---------------------------------------------------------------------------

def test_build_spec_returns_not_allowed_when_preflight_blocks():
    """build_spec propagates preflight block without calling the provider."""
    request = SpecBuildRequest(
        project_name="Test Project",
        user_request="x" * 500_000,  # triggers token limit
        task_type=TaskType.product_design,
    )

    async def fake_create_spec(**kwargs):
        return {"id": "spec-1", **kwargs}

    with patch("app.services.spec_builder_service.run_preflight") as mock_pf:
        mock_pf.return_value = MagicMock(
            allowed=False,
            reason="Estimated input tokens exceed limit.",
            estimated_cost_usd=0.0,
        )
        import asyncio
        result = asyncio.run(
            build_spec(request, db_create_spec_fn=fake_create_spec)
        )

    assert result.allowed is False
    assert "tokens" in result.reason.lower() or result.reason


# ---------------------------------------------------------------------------
# Unit: build_spec — successful spec generation
# ---------------------------------------------------------------------------

def test_build_spec_parses_and_persists_valid_json():
    request = SpecBuildRequest(
        project_name="ANTS Scout",
        user_request="Build a workflow scout for Mercado Público tenders.",
        task_type=TaskType.product_design,
    )

    spec_json = {
        "title": "WF Scout for MP",
        "problem": "Need automated tender discovery.",
        "expected_result": "Workflow catalog with scored matches.",
        "allowed_tools": ["run_command"],
        "required_agents": ["kimi-k2.6"],
        "acceptance_criteria": ["Tenders are fetched", "Scores are computed"],
        "risks": ["API rate limits"],
        "budget": {"max_total_cost_usd": 0.50, "max_iterations": 5},
        "test_harness": {"type": "pytest", "required_score": 90},
    }

    mock_response = MagicMock()
    mock_response.content = json.dumps(spec_json)
    mock_response.model = "kimi-k2.6"
    mock_response.usage = MagicMock(input_tokens=500, output_tokens=300)

    mock_provider = MagicMock()
    mock_provider.chat = AsyncMock(return_value=mock_response)

    saved_spec = {"id": "abc-123", **spec_json}

    async def fake_create_spec(**kwargs):
        return saved_spec

    with (
        patch("app.services.spec_builder_service.run_preflight") as mock_pf,
        patch("app.services.spec_builder_service.get_provider_client", return_value=mock_provider),
        patch("app.services.spec_builder_service.provider_for", return_value="kimi"),
        patch("app.services.spec_builder_service.real_cost_usd", return_value=0.00123),
    ):
        mock_pf.return_value = MagicMock(
            allowed=True,
            reason="",
            estimated_cost_usd=0.001,
            max_output_tokens=4096,
        )
        import asyncio
        result = asyncio.run(
            build_spec(request, db_create_spec_fn=fake_create_spec)
        )

    assert result.allowed is True
    assert result.spec_id == "abc-123"
    assert result.spec["title"] == "WF Scout for MP"
    assert result.real_cost_usd == 0.00123


def test_build_spec_falls_back_to_stub_when_json_parse_fails():
    """When model returns unparseable output, a stub spec is saved."""
    request = SpecBuildRequest(
        project_name="Fallback Test",
        user_request="Some complex request.",
    )

    mock_response = MagicMock()
    mock_response.content = "Sorry, I cannot generate a spec right now."
    mock_response.model = "kimi-k2.6"
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=20)

    mock_provider = MagicMock()
    mock_provider.chat = AsyncMock(return_value=mock_response)

    captured = {}

    async def fake_create_spec(**kwargs):
        captured.update(kwargs)
        return {"id": "stub-1", **kwargs}

    with (
        patch("app.services.spec_builder_service.run_preflight") as mock_pf,
        patch("app.services.spec_builder_service.get_provider_client", return_value=mock_provider),
        patch("app.services.spec_builder_service.provider_for", return_value="kimi"),
        patch("app.services.spec_builder_service.real_cost_usd", return_value=0.0),
    ):
        mock_pf.return_value = MagicMock(
            allowed=True, reason="", estimated_cost_usd=0.001, max_output_tokens=4096
        )
        import asyncio
        result = asyncio.run(
            build_spec(request, db_create_spec_fn=fake_create_spec)
        )

    assert result.allowed is True
    assert result.spec_id == "stub-1"
    assert "risks" in captured
    assert any("parsed" in r.lower() for r in captured["risks"])

