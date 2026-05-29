from __future__ import annotations

import asyncio
import time
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
    AgentHandoffLogRequest,
    AgentHandoffLogResponse,
    ArtifactLogRequest,
    ArtifactLogResponse,
    ExecutorCredentialPoolStatus,
    ExecutorSmokeRequest,
    ExecutorSmokeResponse,
    GitHubRepositoryCreateRequest,
    GitHubRepositoryCreateResponse,
    ExecutorSessionsResponse,
    IngestConvertResponse,
    PreflightRequest,
    PreflightResponse,
    ToolExecutorsResponse,
    WorkflowRunLogRequest,
    WorkflowRunLogResponse,
    UsageLogRequest,
    UsageLogResponse,
    N8nClaimCandidatesRequest,
    N8nClaimCandidatesResponse,
    N8nUpdateIntakeRequest,
    N8nUpdateIntakeResponse,
    SpecBuildRequest,
    SpecBuildResponse,
    HarnessValidateRequest,
    HarnessValidateResponse,
    RagIndexRequest,
    RagIndexResponse,
    RagQueryRequest,
    RagQueryResponse,
    ProposalGenerateRequest,
    ProposalGenerateResponse,
)
from app.services.proposal_service import generate_proposal
from app.services.ingest_service import convert_bytes as ingest_convert_bytes
from app.services.ingest_service import convert_url as ingest_convert_url
from app.services.preflight_service import run_preflight
from app.services.usage_logger import log_usage
from app.services.spec_builder_service import build_spec
from app.services.harness_service import validate_output
from app.services.rag_service import index_document, query_chunks
from app.executor_smoke import run_executor_smoke
from app.tool_executors import list_executor_sessions, list_tool_executor_statuses
from app.db_queries import (
    get_projects,
    create_project,
    get_specs,
    create_spec,
    get_tasks,
    get_usage_logs,
    get_dashboard_stats,
    log_agent_handoff,
    log_artifact,
    log_workflow_run,
    claim_proposal_candidates,
    update_proposal_intake,
)


app = FastAPI(title="ANTS AI Gateway", version="0.1.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"

app.mount("/ui/assets", StaticFiles(directory=STATIC_DIR), name="ants-ui-assets")


@app.get("/ui", include_in_schema=False)
async def operator_ui() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
    )


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


@app.post(
    "/n8n/workflow-runs",
    response_model=WorkflowRunLogResponse,
    dependencies=[Depends(require_gateway_api_key)],
)
async def n8n_workflow_run(request: WorkflowRunLogRequest) -> WorkflowRunLogResponse:
    logged = await log_workflow_run(request.model_dump())
    return WorkflowRunLogResponse(logged=logged, run_id=request.run_id, workflow_name=request.workflow_name)


@app.post(
    "/n8n/artifacts",
    response_model=ArtifactLogResponse,
    dependencies=[Depends(require_gateway_api_key)],
)
async def n8n_artifact(request: ArtifactLogRequest) -> ArtifactLogResponse:
    logged = await log_artifact(request.model_dump())
    return ArtifactLogResponse(logged=logged, name=request.name, uri=request.uri)


@app.post(
    "/n8n/handoffs",
    response_model=AgentHandoffLogResponse,
    dependencies=[Depends(require_gateway_api_key)],
)
async def n8n_handoff(request: AgentHandoffLogRequest) -> AgentHandoffLogResponse:
    logged = await log_agent_handoff(request.model_dump())
    return AgentHandoffLogResponse(
        logged=logged,
        run_id=request.run_id,
        source_agent=request.source_agent,
        target_agent=request.target_agent,
    )


@app.post(
    "/n8n/claim-candidates",
    response_model=N8nClaimCandidatesResponse,
    dependencies=[Depends(require_gateway_api_key)],
)
async def n8n_claim_candidates(request: N8nClaimCandidatesRequest) -> N8nClaimCandidatesResponse:
    candidates = await claim_proposal_candidates(
        n8n_workflow_id=request.n8n_workflow_id,
        n8n_execution_id=request.n8n_execution_id,
        run_id=request.run_id,
    )
    return N8nClaimCandidatesResponse(claimed_count=len(candidates), candidates=candidates)


@app.post(
    "/n8n/update-intake",
    response_model=N8nUpdateIntakeResponse,
    dependencies=[Depends(require_gateway_api_key)],
)
async def n8n_update_intake(request: N8nUpdateIntakeRequest) -> N8nUpdateIntakeResponse:
    success = await update_proposal_intake(
        external_tender_id=request.external_tender_id,
        intake_status=request.intake_status,
        error_message=request.error_message,
        run_id=request.run_id,
        n8n_workflow_id=request.n8n_workflow_id,
        n8n_execution_id=request.n8n_execution_id,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update candidate intake status.")
    return N8nUpdateIntakeResponse(
        success=success,
        external_tender_id=request.external_tender_id,
        intake_status=request.intake_status,
    )



@app.get("/api/dashboard-stats", dependencies=[Depends(require_gateway_api_key)])
async def api_dashboard_stats() -> dict:
    return await get_dashboard_stats()


@app.get("/api/projects", dependencies=[Depends(require_gateway_api_key)])
async def api_projects() -> dict:
    return {"projects": await get_projects()}


@app.post("/api/projects", dependencies=[Depends(require_gateway_api_key)])
async def api_create_project(request: dict) -> dict:
    name = request.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required.")
    return await create_project(
        name=name,
        key=request.get("key"),
        owner=request.get("owner"),
        metadata=request.get("metadata"),
    )


@app.get("/api/specs", dependencies=[Depends(require_gateway_api_key)])
async def api_specs() -> dict:
    return {"specs": await get_specs()}


@app.post("/api/specs", dependencies=[Depends(require_gateway_api_key)])
async def api_create_spec(request: dict) -> dict:
    title = request.get("title")
    problem = request.get("problem")
    if not title or not problem:
        raise HTTPException(status_code=400, detail="Title and problem are required.")
    return await create_spec(
        project_id=request.get("project_id"),
        title=title,
        problem=problem,
        expected_result=request.get("expected_result"),
        allowed_tools=request.get("allowed_tools"),
        required_agents=request.get("required_agents"),
        acceptance_criteria=request.get("acceptance_criteria"),
        risks=request.get("risks"),
        budget=request.get("budget"),
        test_harness=request.get("test_harness"),
    )


@app.get("/api/tasks", dependencies=[Depends(require_gateway_api_key)])
async def api_tasks() -> dict:
    return {"tasks": await get_tasks()}


@app.get("/api/usage-logs", dependencies=[Depends(require_gateway_api_key)])
async def api_usage_logs() -> dict:
    return {"logs": await get_usage_logs()}


@app.post(
    "/ingest/convert",
    response_model=IngestConvertResponse,
    dependencies=[Depends(require_gateway_api_key)],
)
async def ingest_convert(
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
) -> IngestConvertResponse:
    if file is not None:
        content = await file.read()
        data = await asyncio.to_thread(
            ingest_convert_bytes, content, file.filename or "upload.bin"
        )
    elif url:
        data = await asyncio.to_thread(ingest_convert_url, url)
    else:
        raise HTTPException(status_code=422, detail="Provide either 'file' or 'url'.")
    return IngestConvertResponse(**data)


# ---------------------------------------------------------------------------
# Phase 5: Spec Builder + Harness Engine
# ---------------------------------------------------------------------------

@app.post(
    "/spec/build",
    response_model=SpecBuildResponse,
    dependencies=[Depends(require_gateway_api_key)],
)
async def spec_build(request: SpecBuildRequest) -> SpecBuildResponse:
    return await build_spec(request, db_create_spec_fn=create_spec)


@app.post(
    "/harness/validate",
    response_model=HarnessValidateResponse,
    dependencies=[Depends(require_gateway_api_key)],
)
async def harness_validate(request: HarnessValidateRequest) -> HarnessValidateResponse:
    return await validate_output(request, get_spec_fn=get_specs)


# ---------------------------------------------------------------------------
# Phase 6: RAG + Document Services
# ---------------------------------------------------------------------------

@app.post(
    "/rag/index",
    response_model=RagIndexResponse,
    dependencies=[Depends(require_gateway_api_key)],
)
async def rag_index(request: RagIndexRequest) -> RagIndexResponse:
    result = await index_document(
        document_id=request.document_id,
        content=request.content,
        title=request.title,
        project_id=request.project_id,
        metadata=request.metadata,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
    )
    return RagIndexResponse(**result)


@app.post(
    "/rag/query",
    response_model=RagQueryResponse,
    dependencies=[Depends(require_gateway_api_key)],
)
async def rag_query(request: RagQueryRequest) -> RagQueryResponse:
    result = await query_chunks(
        query=request.query,
        project_id=request.project_id,
        top_k=request.top_k,
        threshold=request.threshold,
        document_ids=request.document_ids,
    )
    return RagQueryResponse(**result)


# ---------------------------------------------------------------------------
# Phase 7: Commercial Pipeline — Proposal Generator
# ---------------------------------------------------------------------------

@app.get("/proposal/ping")
async def proposal_ping() -> dict:
    """Public health check — confirms proposal service is loaded and RAG is reachable."""
    from app.services.proposal_service import _PROPOSAL_MODEL, _PROPOSAL_TASK_TYPE
    db = await db_status()
    return {
        "status": "ok",
        "endpoint": "/proposal/generate",
        "model": _PROPOSAL_MODEL,
        "task_type": str(_PROPOSAL_TASK_TYPE),
        "rag_backend": db.get("status", "unknown"),
    }


@app.post(
    "/proposal/generate",
    response_model=ProposalGenerateResponse,
    dependencies=[Depends(require_gateway_api_key)],
)
async def proposal_generate(request: ProposalGenerateRequest) -> ProposalGenerateResponse:
    return await generate_proposal(request)
