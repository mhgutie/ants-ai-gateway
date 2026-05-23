from __future__ import annotations

import time
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException

from app.auth import require_gateway_api_key
from app.config import get_settings
from app.cost_calculator import real_cost_usd
from app.db import db_status
from app.executor_credentials import load_executor_credential_pool_status
from app.github_repositories import GitHubRepositoryProvisioningError, create_github_repository
from app.model_router import list_models, provider_for
from app.providers import get_provider_client
from app.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    EstimateRequest,
    EstimateResponse,
    ExecutorCredentialPoolStatus,
    ExecutorSmokeRequest,
    ExecutorSmokeResponse,
    GitHubRepositoryCreateRequest,
    GitHubRepositoryCreateResponse,
    ExecutorSessionsResponse,
    PreflightRequest,
    PreflightResponse,
    ToolExecutorsResponse,
    UsageLogRequest,
    UsageLogResponse,
)
from app.services.preflight_service import run_preflight
from app.services.usage_logger import log_usage
from app.executor_smoke import run_executor_smoke
from app.tool_executors import list_executor_sessions, list_tool_executor_statuses

app = FastAPI(title="ANTS AI Gateway", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ants-ai-gateway", "env": get_settings().ants_env}


@app.get("/dependencies", dependencies=[Depends(require_gateway_api_key)])
async def dependencies() -> dict:
    return {"supabase_db": await db_status()}


@app.get("/models", dependencies=[Depends(require_gateway_api_key)])
async def models() -> dict:
    return list_models()


@app.get("/executors", response_model=ToolExecutorsResponse, dependencies=[Depends(require_gateway_api_key)])
async def executors() -> ToolExecutorsResponse:
    return list_tool_executor_statuses()


@app.get("/executors/sessions", response_model=ExecutorSessionsResponse, dependencies=[Depends(require_gateway_api_key)])
async def executor_sessions() -> ExecutorSessionsResponse:
    return list_executor_sessions()


@app.get(
    "/executors/credentials/status",
    response_model=ExecutorCredentialPoolStatus,
    dependencies=[Depends(require_gateway_api_key)],
)
async def executor_credentials_status() -> ExecutorCredentialPoolStatus:
    return load_executor_credential_pool_status()


@app.post(
    "/executors/smoke-test",
    response_model=ExecutorSmokeResponse,
    dependencies=[Depends(require_gateway_api_key)],
)
async def executor_smoke_test(request: ExecutorSmokeRequest) -> ExecutorSmokeResponse:
    return await run_executor_smoke(request)


@app.post(
    "/github/repositories",
    response_model=GitHubRepositoryCreateResponse,
    dependencies=[Depends(require_gateway_api_key)],
)
async def github_repository_create(request: GitHubRepositoryCreateRequest) -> GitHubRepositoryCreateResponse:
    try:
        return await create_github_repository(request)
    except GitHubRepositoryProvisioningError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/estimate", response_model=EstimateResponse, dependencies=[Depends(require_gateway_api_key)])
async def estimate(request: EstimateRequest) -> EstimateResponse:
    preflight = run_preflight(request)
    return EstimateResponse(
        task_id=preflight.task_id,
        task_type=preflight.task_type,
        selected_model=preflight.recommended_model,
        fallback_model=preflight.fallback_model,
        estimated_input_tokens=preflight.estimated_input_tokens,
        max_output_tokens=preflight.max_output_tokens,
        estimated_cost_usd=preflight.estimated_cost_usd,
    )


@app.post("/preflight", response_model=PreflightResponse, dependencies=[Depends(require_gateway_api_key)])
async def preflight(request: PreflightRequest) -> PreflightResponse:
    return run_preflight(request)


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_gateway_api_key)])
async def chat(request: ChatRequest) -> ChatResponse:
    preflight_result = run_preflight(request)
    run_id = request.run_id or str(uuid4())
    provider_name = request.provider or provider_for(preflight_result.recommended_model)

    if not preflight_result.allowed:
        await log_usage(
            UsageLogRequest(
                project_id=request.project_id,
                task_id=request.task_id,
                run_id=run_id,
                provider=provider_name,
                model=preflight_result.recommended_model,
                task_type=request.task_type,
                input_tokens_estimated=preflight_result.estimated_input_tokens,
                estimated_cost_usd=preflight_result.estimated_cost_usd,
                latency_ms=0,
                status="blocked",
                stop_reason=preflight_result.reason,
            )
        )
        return ChatResponse(
            allowed=False,
            task_id=request.task_id,
            run_id=run_id,
            provider=provider_name,
            model=preflight_result.recommended_model,
            fallback_model=preflight_result.fallback_model,
            content=None,
            usage=None,
            estimated_cost_usd=preflight_result.estimated_cost_usd,
            real_cost_usd=None,
            stop_rules=preflight_result.stop_rules,
            reason=preflight_result.reason,
        )

    messages = request.messages or [ChatMessage(role="user", content=request.user_request)]
    provider = get_provider_client(provider_name)
    started_at = time.perf_counter()
    try:
        provider_response = await provider.chat(
            model=preflight_result.recommended_model,
            messages=messages,
            max_tokens=preflight_result.max_output_tokens,
            account_id=request.account_id,
        )
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        await log_usage(
            UsageLogRequest(
                project_id=request.project_id,
                task_id=request.task_id,
                run_id=run_id,
                provider=provider_name,
                model=preflight_result.recommended_model,
                task_type=request.task_type,
                input_tokens_estimated=preflight_result.estimated_input_tokens,
                estimated_cost_usd=preflight_result.estimated_cost_usd,
                latency_ms=latency_ms,
                status="error",
                stop_reason=exc.__class__.__name__,
            )
        )
        raise HTTPException(status_code=502, detail="Provider call failed.") from exc

    latency_ms = int((time.perf_counter() - started_at) * 1000)
    actual_cost = real_cost_usd(
        preflight_result.recommended_model,
        provider_response.usage.input_tokens,
        provider_response.usage.output_tokens,
    )
    await log_usage(
        UsageLogRequest(
            project_id=request.project_id,
            task_id=request.task_id,
            run_id=run_id,
            provider=provider_response.provider,
            model=provider_response.model,
            task_type=request.task_type,
            input_tokens_estimated=preflight_result.estimated_input_tokens,
            input_tokens_real=provider_response.usage.input_tokens,
            output_tokens_real=provider_response.usage.output_tokens,
            total_tokens_real=provider_response.usage.total_tokens,
            estimated_cost_usd=preflight_result.estimated_cost_usd,
            real_cost_usd=actual_cost,
            latency_ms=latency_ms,
            status="success",
        )
    )
    return ChatResponse(
        allowed=True,
        task_id=request.task_id,
        run_id=run_id,
        provider=provider_response.provider,
        model=provider_response.model,
        fallback_model=preflight_result.fallback_model,
        content=provider_response.content,
        usage=provider_response.usage,
        estimated_cost_usd=preflight_result.estimated_cost_usd,
        real_cost_usd=actual_cost,
        stop_rules=preflight_result.stop_rules,
        reason=preflight_result.reason,
    )


@app.post("/usage", response_model=UsageLogResponse, dependencies=[Depends(require_gateway_api_key)])
async def usage(request: UsageLogRequest) -> UsageLogResponse:
    logged = await log_usage(request)
    return UsageLogResponse(logged=logged, run_id=request.run_id)
