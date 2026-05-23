from __future__ import annotations

from typing import Any

from app.config import get_budgets_config
from app.cost_calculator import estimate_cost_usd
from app.model_router import route_for, select_model
from app.schemas import BudgetOverride, GatewayRequest, PreflightResponse
from app.services.stop_rules import evaluate_stop_rules
from app.token_budget import estimate_input_tokens


def _budget_for(task_type: str, override: BudgetOverride | dict[str, Any]) -> dict[str, Any]:
    budgets = get_budgets_config()
    budget = dict(budgets.get("default", {}))
    budget.update(budgets.get(task_type, {}))
    override_data = override.model_dump(exclude_none=True) if isinstance(override, BudgetOverride) else dict(override or {})
    budget.update({key: value for key, value in override_data.items() if value is not None})
    return budget


def run_preflight(request: GatewayRequest) -> PreflightResponse:
    budget = _budget_for(request.task_type.value, request.budget)
    estimated_input = estimate_input_tokens(request.user_request, request.context)
    max_output = int(budget["max_output_tokens_per_call"])

    try:
        selected_model, fallback_model = select_model(request.task_type, request.model)
    except ValueError as exc:
        route = route_for(request.task_type)
        selected_model = str(route["primary"])
        fallback_model = route["fallback"]
        return PreflightResponse(
            allowed=False,
            task_id=request.task_id,
            task_type=request.task_type,
            recommended_model=selected_model,
            fallback_model=fallback_model,
            estimated_input_tokens=estimated_input,
            max_output_tokens=max_output,
            estimated_cost_usd=0,
            risk="blocked",
            execution_mode="blocked",
            stop_rules=["model_unavailable"],
            reason=str(exc),
        )

    estimated_cost = estimate_cost_usd(selected_model, estimated_input, max_output)

    allowed, stop_rules, risk, execution_mode, reason = evaluate_stop_rules(
        estimated_input_tokens=estimated_input,
        estimated_cost_usd=estimated_cost,
        max_total_cost_usd=float(budget["max_total_cost_usd"]),
        iteration=request.iteration,
        max_iterations=int(budget["max_iterations"]),
        requested_context_scope=request.requested_context_scope,
        explicitly_authorized=request.explicitly_authorized,
        same_error_count=request.same_error_count,
        no_meaningful_output_count=request.no_meaningful_output_count,
    )

    if estimated_input > int(budget["max_input_tokens_per_call"]) and allowed:
        stop_rules.append("input_tokens_exceed_task_limit")
        allowed = False
        risk = "blocked"
        execution_mode = "blocked"
        reason = "input_tokens_exceed_task_limit"

    return PreflightResponse(
        allowed=allowed,
        task_id=request.task_id,
        task_type=request.task_type,
        recommended_model=selected_model,
        fallback_model=fallback_model,
        estimated_input_tokens=estimated_input,
        max_output_tokens=max_output,
        estimated_cost_usd=estimated_cost,
        risk=risk,
        execution_mode=execution_mode,
        stop_rules=stop_rules,
        reason=reason,
    )
