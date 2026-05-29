from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from app.cost_calculator import real_cost_usd
from app.model_router import provider_for
from app.providers import get_provider_client
from app.schemas import (
    ChatMessage,
    ContextScope,
    GatewayRequest,
    HarnessCriterionResult,
    HarnessValidateRequest,
    HarnessValidateResponse,
    HarnessVerdict,
    TaskType,
)
from app.services.preflight_service import run_preflight

logger = logging.getLogger(__name__)

_HARNESS_MODEL = "deepseek-v4-pro"
_HARNESS_TASK_TYPE = TaskType.final_validation

_SYSTEM_PROMPT = """You are the ANTS Harness Engine. Evaluate whether the generated output satisfies every acceptance criterion in the spec. Return ONLY valid JSON — no markdown fences, no prose.

Required JSON shape:
{
  "score": <integer 0-100>,
  "verdict": "approved" | "needs_revision" | "rejected",
  "findings": "<concise audit summary, 2-4 sentences>",
  "criteria_results": [
    {"criterion": "<criterion text>", "passed": true|false, "notes": "<short note>"},
    ...
  ]
}

Rules:
- score 90-100 → approved, 60-89 → needs_revision, <60 → rejected.
- verdict must match score tier.
- criteria_results must contain one entry per criterion in the spec.
- Return raw JSON only."""


def _extract_json(text: str) -> dict[str, Any]:
    clean = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in harness response.")
    return json.loads(match.group())


async def validate_output(
    request: HarnessValidateRequest,
    get_spec_fn: Any,
) -> HarnessValidateResponse:
    """Call DeepSeek Pro to validate generated output against a spec's acceptance criteria."""
    spec: dict[str, Any] | None = None

    if request.spec_inline:
        spec = request.spec_inline
    elif request.spec_id:
        specs = await get_spec_fn()
        for s in specs:
            if s.get("id") == request.spec_id:
                spec = s
                break

    if not spec:
        return HarnessValidateResponse(
            passed=False,
            score=0,
            verdict=HarnessVerdict.rejected,
            findings="Spec not found. Cannot validate without acceptance criteria.",
            criteria_results=[],
            model_used=_HARNESS_MODEL,
            estimated_cost_usd=0.0,
            real_cost_usd=None,
            spec_id=request.spec_id,
        )

    criteria: list[str] = spec.get("acceptance_criteria") or spec.get("required_agents_models") or []
    if not criteria:
        criteria = ["Output addresses the stated problem and expected result."]

    task_id = request.task_id or f"HARNESS-{(request.spec_id or 'inline')[:6].upper()}"

    preflight_input = GatewayRequest(
        project_id=request.project_id,
        task_id=task_id,
        task_type=_HARNESS_TASK_TYPE,
        user_request=request.generated_output,
        requested_context_scope=ContextScope.limited,
        explicitly_authorized=request.explicitly_authorized,
        model=_HARNESS_MODEL,
        account_id=request.account_id,
    )
    preflight = run_preflight(preflight_input)

    if not preflight.allowed:
        return HarnessValidateResponse(
            passed=False,
            score=0,
            verdict=HarnessVerdict.rejected,
            findings=f"Preflight blocked: {preflight.reason}",
            criteria_results=[],
            model_used=_HARNESS_MODEL,
            estimated_cost_usd=preflight.estimated_cost_usd,
            real_cost_usd=None,
            spec_id=request.spec_id,
        )

    user_prompt = (
        f"SPEC TITLE: {spec.get('title', 'Untitled')}\n\n"
        f"PROBLEM: {spec.get('problem', '')}\n\n"
        f"EXPECTED RESULT: {spec.get('expected_result', '')}\n\n"
        f"ACCEPTANCE CRITERIA:\n"
        + "\n".join(f"- {c}" for c in criteria)
        + f"\n\nGENERATED OUTPUT:\n\"\"\"\n{request.generated_output}\n\"\"\""
    )

    provider_name = provider_for(_HARNESS_MODEL)
    provider = get_provider_client(provider_name)
    started = time.perf_counter()
    try:
        response = await provider.chat(
            model=_HARNESS_MODEL,
            messages=[
                ChatMessage(role="system", content=_SYSTEM_PROMPT),
                ChatMessage(role="user", content=user_prompt),
            ],
            max_tokens=preflight.max_output_tokens,
            account_id=request.account_id,
        )
    except Exception as exc:
        logger.warning("Harness provider call failed: %s — returning needs_revision fallback.", exc)
        fallback_results = [
            HarnessCriterionResult(
                criterion=c,
                passed=False,
                notes=f"Provider unavailable ({exc.__class__.__name__}). Manual review required.",
            )
            for c in criteria
        ]
        return HarnessValidateResponse(
            passed=False,
            score=60,
            verdict=HarnessVerdict.needs_revision,
            findings=f"Harness Engine provider ({_HARNESS_MODEL}) unavailable: {exc.__class__.__name__}. Configure API key for automated validation. Manual review required.",
            criteria_results=fallback_results,
            model_used=_HARNESS_MODEL,
            estimated_cost_usd=preflight.estimated_cost_usd,
            real_cost_usd=0.0,
            spec_id=request.spec_id,
        )

    actual_cost = real_cost_usd(
        _HARNESS_MODEL,
        response.usage.input_tokens or 0,
        response.usage.output_tokens or 0,
    )

    try:
        result = _extract_json(response.content)
        score = max(0, min(100, int(result.get("score", 0))))
        verdict_str = result.get("verdict", "rejected")
        verdict = HarnessVerdict(verdict_str) if verdict_str in HarnessVerdict.__members__ else HarnessVerdict.rejected
        findings = str(result.get("findings", ""))
        raw_criteria = result.get("criteria_results", [])
        criteria_results = [
            HarnessCriterionResult(
                criterion=str(c.get("criterion", "")),
                passed=bool(c.get("passed", False)),
                notes=str(c.get("notes", "")),
            )
            for c in raw_criteria
        ]
    except (ValueError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("Failed to parse harness JSON: %s", exc)
        score = 50
        verdict = HarnessVerdict.needs_revision
        findings = "Harness output could not be fully parsed. Manual review required."
        criteria_results = [
            HarnessCriterionResult(criterion=c, passed=False, notes="Parse error.")
            for c in criteria
        ]

    return HarnessValidateResponse(
        passed=score >= 90,
        score=score,
        verdict=verdict,
        findings=findings,
        criteria_results=criteria_results,
        model_used=response.model,
        estimated_cost_usd=preflight.estimated_cost_usd,
        real_cost_usd=actual_cost,
        spec_id=request.spec_id,
    )
