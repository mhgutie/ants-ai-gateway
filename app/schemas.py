from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    classification = "classification"
    simple_extraction = "simple_extraction"
    high_volume_extraction = "high_volume_extraction"
    coding_debug = "coding_debug"
    workflow_debug = "workflow_debug"
    product_design = "product_design"
    architecture = "architecture"
    visual_analysis = "visual_analysis"
    long_document = "long_document"
    google_workspace_processing = "google_workspace_processing"
    complex_reasoning = "complex_reasoning"
    custom_tool_agent = "custom_tool_agent"
    realtime_voice = "realtime_voice"
    text_to_speech = "text_to_speech"
    image_generation = "image_generation"
    final_validation = "final_validation"


class ContextScope(str, Enum):
    limited = "limited"
    selected_files = "selected_files"
    full_repo = "full_repo"


Risk = Literal["low", "medium", "high", "blocked"]
ExecutionMode = Literal["direct", "direct_limited", "summarize_first", "rag_first", "blocked"]


class BudgetOverride(BaseModel):
    max_total_cost_usd: float | None = None
    max_iterations: int | None = None
    max_input_tokens_per_call: int | None = None
    max_output_tokens_per_call: int | None = None


class GatewayRequest(BaseModel):
    task_id: str
    task_type: TaskType
    user_request: str
    context: dict[str, Any] = Field(default_factory=dict)
    budget: BudgetOverride | dict[str, Any] = Field(default_factory=dict)
    requested_context_scope: ContextScope = ContextScope.limited
    explicitly_authorized: bool = False
    model: str = "auto"
    provider: str | None = None
    account_id: str | None = None
    iteration: int = 1
    same_error_count: int = 0
    no_meaningful_output_count: int = 0
    agent_name: str | None = None
    run_id: str | None = None


class EstimateRequest(GatewayRequest):
    pass


class PreflightRequest(GatewayRequest):
    pass


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(GatewayRequest):
    messages: list[ChatMessage] | None = None


class EstimateResponse(BaseModel):
    task_id: str
    task_type: TaskType
    selected_model: str
    fallback_model: str | None
    estimated_input_tokens: int
    max_output_tokens: int
    estimated_cost_usd: float


class PreflightResponse(BaseModel):
    allowed: bool
    task_id: str
    task_type: TaskType
    recommended_model: str
    fallback_model: str | None
    estimated_input_tokens: int
    max_output_tokens: int
    estimated_cost_usd: float
    risk: Risk
    execution_mode: ExecutionMode
    stop_rules: list[str]
    reason: str


class ProviderUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class ProviderResponse(BaseModel):
    provider: str
    model: str
    content: str
    raw: dict[str, Any] = Field(default_factory=dict)
    usage: ProviderUsage = Field(default_factory=ProviderUsage)


class ChatResponse(BaseModel):
    allowed: bool
    task_id: str
    run_id: str
    provider: str | None
    model: str
    fallback_model: str | None
    content: str | None
    usage: ProviderUsage | None
    estimated_cost_usd: float
    real_cost_usd: float | None
    stop_rules: list[str]
    reason: str


class UsageLogRequest(BaseModel):
    task_id: str
    run_id: str
    provider: str
    model: str
    task_type: TaskType
    input_tokens_estimated: int
    input_tokens_real: int | None = None
    output_tokens_real: int | None = None
    total_tokens_real: int | None = None
    estimated_cost_usd: float
    real_cost_usd: float | None = None
    status: str
    stop_reason: str | None = None


class UsageLogResponse(BaseModel):
    logged: bool
    run_id: str


class ToolExecutorStatus(BaseModel):
    name: str
    enabled: bool
    role: str
    execution_mode: str
    auth_mode: str
    credential_storage: str
    uses_external_auth_store: bool
    requires_spec: bool
    requires_harness: bool
    allow_shell: bool
    allow_browser: bool
    block_destructive_commands: bool
    sanitize_secrets: bool
    workspace_root_configured: bool
    allowed_roots_configured: bool
    notes: str


class ToolExecutorsResponse(BaseModel):
    policy_version: str
    executors: list[ToolExecutorStatus]


class ExecutorSessionStatus(BaseModel):
    executor: str
    session_ref: str
    label: str
    auth_mode: str
    status: Literal["pending_auth", "configured", "authenticated", "expired", "failed", "disabled"]
    credential_storage: str
    workspace_root_configured: bool
    allowed_roots_configured: bool
    last_checked_at: str | None = None
    last_status_reason: str


class ExecutorSessionsResponse(BaseModel):
    schema_version: str
    sessions: list[ExecutorSessionStatus]


class ExecutorSmokeRequest(BaseModel):
    executor: Literal["codex", "claude_code", "antigravity"]
    mode: Literal["version", "prompt"] = "version"
    cwd: str | None = None
    timeout_seconds: int = 30


class ExecutorSmokeResponse(BaseModel):
    executor: str
    mode: str
    passed: bool
    command: list[str]
    exit_code: int | None
    stdout: str
    stderr: str
    reason: str


class ExecutorCredentialPoolStatus(BaseModel):
    configured: bool
    decryptable: bool
    version: int | None = None
    active_provider: str | None = None
    providers: list[str] = Field(default_factory=list)
    credential_counts: dict[str, int] = Field(default_factory=dict)
    updated_at: str | None = None
    error: str | None = None
