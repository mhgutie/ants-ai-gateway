from __future__ import annotations

import logging
import time

from app.cost_calculator import real_cost_usd
from app.model_router import provider_for
from app.providers import get_provider_client
from app.schemas import (
    ChatMessage,
    GatewayRequest,
    ProposalGenerateRequest,
    ProposalGenerateResponse,
    ProposalRagMatch,
    TaskType,
)
from app.services.preflight_service import run_preflight
from app.services.rag_service import query_chunks

logger = logging.getLogger(__name__)

_PROPOSAL_MODEL = "kimi-k2.6"
_PROPOSAL_TASK_TYPE = TaskType.product_design

_SYSTEM_PROMPT = """Eres el arquitecto de propuestas comerciales de ANTS, empresa especializada en automatización de procesos con agentes de IA y workflows n8n.

Tu tarea es redactar una propuesta técnica y comercial profesional para una licitación pública de Mercado Público Chile.

La propuesta debe incluir las siguientes secciones en markdown:

## 1. Resumen Ejecutivo
Descripción concisa (2-3 párrafos) de la solución propuesta y su valor para la organización licitante.

## 2. Entendimiento del Requerimiento
Análisis de las necesidades identificadas en las bases de licitación.

## 3. Solución Técnica Propuesta
Descripción detallada de los workflows, automatizaciones e integraciones a implementar.
Referencia los workflows del catálogo ANTS más relevantes como base de la solución.

## 4. Metodología de Implementación
Fases del proyecto con hitos claros, entregables y cronograma estimado.

## 5. Propuesta de Valor
Beneficios concretos y cuantificables: ahorro de tiempo, reducción de errores, eficiencia operacional.

## 6. Equipo y Experiencia
Perfiles del equipo propuesto y experiencia relevante en proyectos similares.

Reglas:
- Responde siempre en español
- Sé específico, técnico y profesional
- Usa los workflows del catálogo como evidencia concreta de capacidad técnica
- Mantén un tono formal apropiado para licitaciones públicas chilenas
- No incluyas precios ni valores monetarios (se definen en documento separado)"""


async def generate_proposal(request: ProposalGenerateRequest) -> ProposalGenerateResponse:
    """Query RAG for relevant workflows then generate a full proposal using LLM."""
    task_id = f"PROP-{request.licitacion_id[:8].upper()}"

    # 1. Query RAG for relevant workflows
    rag_result = await query_chunks(
        query=f"{request.title}\n\n{request.description}",
        top_k=request.top_k,
        threshold=request.rag_threshold,
    )
    rag_matches = [
        ProposalRagMatch(
            document_id=r["document_id"],
            title=r.get("title"),
            score=r["score"],
            content=r["content"],
            metadata=r.get("metadata", {}),
        )
        for r in rag_result.get("results", [])
    ]

    # 2. Build context block from RAG matches
    context_sections = []
    for i, m in enumerate(rag_matches, 1):
        context_sections.append(
            f"**Workflow {i}: {m.title or m.document_id}** (relevancia: {m.score:.0%})\n{m.content[:600]}"
        )
    rag_context = "\n\n---\n\n".join(context_sections) if context_sections else (
        "No se encontraron workflows relevantes en el catálogo ANTS."
    )

    # 3. Preflight check
    preflight = run_preflight(GatewayRequest(
        project_id=request.project_id,
        task_id=task_id,
        task_type=_PROPOSAL_TASK_TYPE,
        user_request=f"Generar propuesta para licitación: {request.title}",
        explicitly_authorized=request.explicitly_authorized,
        model=_PROPOSAL_MODEL,
        account_id=request.account_id,
    ))

    if not preflight.allowed:
        return ProposalGenerateResponse(
            licitacion_id=request.licitacion_id,
            spec_id="",
            proposal_text="",
            rag_matches=rag_matches,
            rag_total=len(rag_matches),
            model_used=_PROPOSAL_MODEL,
            estimated_cost_usd=preflight.estimated_cost_usd,
            real_cost_usd=None,
            allowed=False,
            reason=preflight.reason,
        )

    # 4. Compose LLM prompt
    user_prompt = (
        f"# Licitación: {request.title}\n\n"
        f"## Descripción del requerimiento\n\n{request.description}\n\n"
        f"---\n\n"
        f"## Workflows relevantes del catálogo ANTS\n\n{rag_context}\n\n"
        f"---\n\n"
        f"Redacta la propuesta técnica y comercial completa en español, siguiendo las secciones indicadas."
    )

    provider_name = provider_for(_PROPOSAL_MODEL)
    provider = get_provider_client(provider_name)
    started = time.perf_counter()
    try:
        response = await provider.chat(
            model=_PROPOSAL_MODEL,
            messages=[
                ChatMessage(role="system", content=_SYSTEM_PROMPT),
                ChatMessage(role="user", content=user_prompt),
            ],
            max_tokens=preflight.max_output_tokens,
            account_id=request.account_id,
        )
        proposal_text = response.content
        model_used = response.model
        actual_cost = real_cost_usd(
            _PROPOSAL_MODEL,
            response.usage.input_tokens or 0,
            response.usage.output_tokens or 0,
        )
        reason = "Propuesta generada exitosamente."
    except Exception as exc:
        logger.warning("Proposal provider call failed (%s) — returning RAG context only.", exc)
        proposal_text = (
            f"# Propuesta para: {request.title}\n\n"
            f"*Generación automática no disponible ({exc.__class__.__name__}). "
            f"Configure el proveedor {_PROPOSAL_MODEL} para habilitar esta función.*\n\n"
            f"## Workflows Relevantes Identificados\n\n{rag_context}"
        )
        model_used = _PROPOSAL_MODEL
        actual_cost = 0.0
        reason = f"Provider unavailable — RAG context returned ({exc.__class__.__name__})."

    return ProposalGenerateResponse(
        licitacion_id=request.licitacion_id,
        spec_id="",
        proposal_text=proposal_text,
        rag_matches=rag_matches,
        rag_total=len(rag_matches),
        model_used=model_used,
        estimated_cost_usd=preflight.estimated_cost_usd,
        real_cost_usd=actual_cost,
        allowed=True,
        reason=reason,
    )
