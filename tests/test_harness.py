"""Tests for Phase 5: Harness Engine service and endpoint."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas import HarnessValidateRequest, HarnessVerdict
from app.services.harness_service import _extract_json, validate_output


# ---------------------------------------------------------------------------
# Unit: JSON extraction
# ---------------------------------------------------------------------------

def test_extract_json_parses_harness_response():
    raw = '{"score": 92, "verdict": "approved", "findings": "All checks pass.", "criteria_results": []}'
    result = _extract_json(raw)
    assert result["score"] == 92
    assert result["verdict"] == "approved"


def test_extract_json_strips_fences_in_harness():
    raw = "```json\n{\"score\": 70, \"verdict\": \"needs_revision\", \"findings\": \"Minor issues.\", \"criteria_results\": []}\n```"
    result = _extract_json(raw)
    assert result["verdict"] == "needs_revision"


# ---------------------------------------------------------------------------
# Unit: validate_output — no spec found
# ---------------------------------------------------------------------------

def test_validate_output_returns_rejected_when_spec_not_found():
    request = HarnessValidateRequest(
        spec_id="nonexistent-id",
        generated_output="Some output.",
    )

    async def fake_get_specs():
        return []

    import asyncio
    result = asyncio.run(
        validate_output(request, get_spec_fn=fake_get_specs)
    )

    assert result.passed is False
    assert result.verdict == HarnessVerdict.rejected
    assert "not found" in result.findings.lower()


# ---------------------------------------------------------------------------
# Unit: validate_output — inline spec, approved output
# ---------------------------------------------------------------------------

def test_validate_output_approved_with_inline_spec():
    spec = {
        "title": "Test Spec",
        "problem": "Build a widget.",
        "expected_result": "Widget code.",
        "acceptance_criteria": ["Widget renders correctly", "Tests pass at 90%+"],
    }
    request = HarnessValidateRequest(
        spec_inline=spec,
        generated_output="class Widget:\n    def render(self): return '<div>OK</div>'",
        task_id="TSK-001",
    )

    harness_response = {
        "score": 95,
        "verdict": "approved",
        "findings": "Both criteria satisfied.",
        "criteria_results": [
            {"criterion": "Widget renders correctly", "passed": True, "notes": "render() returns HTML"},
            {"criterion": "Tests pass at 90%+", "passed": True, "notes": "Score 95/100"},
        ],
    }

    mock_response = MagicMock()
    mock_response.content = json.dumps(harness_response)
    mock_response.model = "deepseek-v4-pro"
    mock_response.usage = MagicMock(input_tokens=800, output_tokens=200)

    mock_provider = MagicMock()
    mock_provider.chat = AsyncMock(return_value=mock_response)

    async def fake_get_specs():
        return []

    with (
        patch("app.services.harness_service.run_preflight") as mock_pf,
        patch("app.services.harness_service.get_provider_client", return_value=mock_provider),
        patch("app.services.harness_service.provider_for", return_value="deepseek"),
        patch("app.services.harness_service.real_cost_usd", return_value=0.0008),
    ):
        mock_pf.return_value = MagicMock(
            allowed=True, reason="", estimated_cost_usd=0.001, max_output_tokens=4096
        )
        import asyncio
        result = asyncio.run(
            validate_output(request, get_spec_fn=fake_get_specs)
        )

    assert result.passed is True
    assert result.score == 95
    assert result.verdict == HarnessVerdict.approved
    assert len(result.criteria_results) == 2
    assert all(c.passed for c in result.criteria_results)
    assert result.real_cost_usd == 0.0008


def test_validate_output_rejected_when_score_below_60():
    spec = {
        "title": "Low Score Test",
        "problem": "Do something hard.",
        "expected_result": "Perfect output.",
        "acceptance_criteria": ["All tests pass", "No errors", "100% coverage"],
    }
    request = HarnessValidateRequest(spec_inline=spec, generated_output="pass")

    harness_response = {
        "score": 40,
        "verdict": "rejected",
        "findings": "Output is incomplete.",
        "criteria_results": [
            {"criterion": "All tests pass", "passed": False, "notes": "No tests found"},
            {"criterion": "No errors", "passed": False, "notes": "Missing implementation"},
            {"criterion": "100% coverage", "passed": False, "notes": "N/A"},
        ],
    }

    mock_response = MagicMock()
    mock_response.content = json.dumps(harness_response)
    mock_response.model = "deepseek-v4-pro"
    mock_response.usage = MagicMock(input_tokens=400, output_tokens=150)

    mock_provider = MagicMock()
    mock_provider.chat = AsyncMock(return_value=mock_response)

    async def fake_get_specs():
        return []

    with (
        patch("app.services.harness_service.run_preflight") as mock_pf,
        patch("app.services.harness_service.get_provider_client", return_value=mock_provider),
        patch("app.services.harness_service.provider_for", return_value="deepseek"),
        patch("app.services.harness_service.real_cost_usd", return_value=0.0003),
    ):
        mock_pf.return_value = MagicMock(
            allowed=True, reason="", estimated_cost_usd=0.001, max_output_tokens=4096
        )
        import asyncio
        result = asyncio.run(
            validate_output(request, get_spec_fn=fake_get_specs)
        )

    assert result.passed is False
    assert result.score == 40
    assert result.verdict == HarnessVerdict.rejected
    assert not any(c.passed for c in result.criteria_results)


def test_validate_output_needs_revision_when_score_between_60_and_89():
    spec = {"title": "Mid Score", "problem": "Partial.", "acceptance_criteria": ["A", "B"]}
    request = HarnessValidateRequest(spec_inline=spec, generated_output="partial implementation")

    harness_response = {
        "score": 75,
        "verdict": "needs_revision",
        "findings": "Some criteria met.",
        "criteria_results": [
            {"criterion": "A", "passed": True, "notes": "OK"},
            {"criterion": "B", "passed": False, "notes": "Missing"},
        ],
    }

    mock_response = MagicMock()
    mock_response.content = json.dumps(harness_response)
    mock_response.model = "deepseek-v4-pro"
    mock_response.usage = MagicMock(input_tokens=300, output_tokens=100)

    mock_provider = MagicMock()
    mock_provider.chat = AsyncMock(return_value=mock_response)

    async def fake_get_specs():
        return []

    with (
        patch("app.services.harness_service.run_preflight") as mock_pf,
        patch("app.services.harness_service.get_provider_client", return_value=mock_provider),
        patch("app.services.harness_service.provider_for", return_value="deepseek"),
        patch("app.services.harness_service.real_cost_usd", return_value=0.0002),
    ):
        mock_pf.return_value = MagicMock(
            allowed=True, reason="", estimated_cost_usd=0.001, max_output_tokens=4096
        )
        import asyncio
        result = asyncio.run(
            validate_output(request, get_spec_fn=fake_get_specs)
        )

    assert result.passed is False
    assert result.score == 75
    assert result.verdict == HarnessVerdict.needs_revision


def test_validate_output_preflight_block_returns_rejected():
    request = HarnessValidateRequest(
        spec_inline={"title": "T", "acceptance_criteria": ["X"]},
        generated_output="x" * 600_000,
    )

    async def fake_get_specs():
        return []

    with patch("app.services.harness_service.run_preflight") as mock_pf:
        mock_pf.return_value = MagicMock(
            allowed=False,
            reason="Token limit exceeded.",
            estimated_cost_usd=0.0,
        )
        import asyncio
        result = asyncio.run(
            validate_output(request, get_spec_fn=fake_get_specs)
        )

    assert result.passed is False
    assert result.verdict == HarnessVerdict.rejected
    assert "Preflight blocked" in result.findings

