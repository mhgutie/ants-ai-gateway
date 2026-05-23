from __future__ import annotations

from app.schemas import ContextScope, ExecutionMode, Risk


HARD_CONTEXT_TOKEN_LIMIT = 128_000


def evaluate_stop_rules(
    *,
    estimated_input_tokens: int,
    estimated_cost_usd: float,
    max_total_cost_usd: float,
    iteration: int,
    max_iterations: int,
    requested_context_scope: ContextScope,
    explicitly_authorized: bool,
    same_error_count: int,
    no_meaningful_output_count: int,
) -> tuple[bool, list[str], Risk, ExecutionMode, str]:
    stop_rules: list[str] = []

    if estimated_input_tokens > HARD_CONTEXT_TOKEN_LIMIT:
        stop_rules.append("summarize_or_rag_first")

    if estimated_cost_usd > max_total_cost_usd:
        stop_rules.append("estimated_cost_exceeds_budget")

    if iteration > max_iterations:
        stop_rules.append("iteration_limit_exceeded")

    if same_error_count >= 2:
        stop_rules.append("switch_model_or_stop")

    if requested_context_scope == ContextScope.full_repo and not explicitly_authorized:
        stop_rules.append("full_repo_requires_explicit_authorization")

    if no_meaningful_output_count >= 2:
        stop_rules.append("no_meaningful_output_stop")

    blocking = {
        "summarize_or_rag_first",
        "estimated_cost_exceeds_budget",
        "iteration_limit_exceeded",
        "full_repo_requires_explicit_authorization",
        "no_meaningful_output_stop",
    }
    allowed = not any(rule in blocking for rule in stop_rules)

    if not allowed:
        execution_mode: ExecutionMode = "blocked"
        risk: Risk = "blocked"
        reason = "; ".join(stop_rules)
    elif estimated_input_tokens > 32_000:
        execution_mode = "direct_limited"
        risk = "medium"
        reason = "Allowed with limited direct execution due to large context."
    elif same_error_count >= 2:
        execution_mode = "direct"
        risk = "high"
        reason = "Allowed, but repeated errors recommend switching model or stopping."
    else:
        execution_mode = "direct"
        risk = "low"
        reason = "Allowed."

    return allowed, stop_rules, risk, execution_mode, reason
