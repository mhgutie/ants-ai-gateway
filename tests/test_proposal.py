"""Tests for Phase 7: Commercial Pipeline — Proposal Generator."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas import ProposalGenerateRequest, ProposalGenerateResponse


# ---------------------------------------------------------------------------
# Unit: ProposalGenerateRequest schema
# ---------------------------------------------------------------------------

def test_proposal_request_defaults():
    req = ProposalGenerateRequest(
        licitacion_id="LIC-001",
        title="Sistema de gestión documental",
        description="Requiere automatización de flujo de documentos",
    )
    assert req.licitacion_id == "LIC-001"
    assert req.top_k == 5
    assert req.rag_threshold == 0.45
    assert req.explicitly_authorized is False
    assert req.project_id is None


def test_proposal_request_top_k_bounds():
    req = ProposalGenerateRequest(
        licitacion_id="X",
        title="T",
        description="D",
        top_k=10,
        rag_threshold=0.7,
    )
    assert req.top_k == 10
    assert req.rag_threshold == 0.7


# ---------------------------------------------------------------------------
# Unit: generate_proposal service (mocked RAG + provider)
# ---------------------------------------------------------------------------

def test_generate_proposal_returns_rag_matches():
    mock_rag = AsyncMock(return_value={
        "results": [
            {
                "document_id": "wf_12345",
                "title": "Document workflow automation",
                "score": 0.82,
                "content": "Automates document processing using n8n.",
                "metadata": {"domain": "documents"},
            }
        ],
        "total": 1,
        "source": "supabase",
        "embedding_model": "text-embedding-3-small",
    })

    mock_provider = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "## 1. Resumen Ejecutivo\n\nPropuesta generada."
    mock_response.model = "kimi-k2.6"
    mock_response.usage = MagicMock(input_tokens=500, output_tokens=800)
    mock_provider.chat = AsyncMock(return_value=mock_response)

    with (
        patch("app.services.proposal_service.query_chunks", mock_rag),
        patch("app.services.proposal_service.get_provider_client", return_value=mock_provider),
        patch("app.services.proposal_service.provider_for", return_value="openrouter"),
    ):
        from app.services.proposal_service import generate_proposal

        result = asyncio.run(generate_proposal(ProposalGenerateRequest(
            licitacion_id="LIC-2026-001",
            title="Sistema de gestión documental",
            description="Necesitamos automatizar el flujo de documentos internos.",
        )))

    assert isinstance(result, ProposalGenerateResponse)
    assert result.allowed is True
    assert result.licitacion_id == "LIC-2026-001"
    assert len(result.rag_matches) == 1
    assert result.rag_matches[0].document_id == "wf_12345"
    assert result.rag_matches[0].score == 0.82
    assert "Resumen Ejecutivo" in result.proposal_text


def test_generate_proposal_graceful_on_provider_failure():
    mock_rag = AsyncMock(return_value={
        "results": [
            {
                "document_id": "wf_999",
                "title": "Email automation",
                "score": 0.65,
                "content": "Automates email processing.",
                "metadata": {},
            }
        ],
        "total": 1,
        "source": "supabase",
        "embedding_model": "text-embedding-3-small",
    })

    mock_provider = MagicMock()
    mock_provider.chat = AsyncMock(side_effect=RuntimeError("Provider unavailable"))

    with (
        patch("app.services.proposal_service.query_chunks", mock_rag),
        patch("app.services.proposal_service.get_provider_client", return_value=mock_provider),
        patch("app.services.proposal_service.provider_for", return_value="openrouter"),
    ):
        from app.services.proposal_service import generate_proposal

        result = asyncio.run(generate_proposal(ProposalGenerateRequest(
            licitacion_id="LIC-2026-002",
            title="Automatización de correos",
            description="Requerimiento de automatización de procesamiento de correos.",
        )))

    assert result.allowed is True
    assert result.licitacion_id == "LIC-2026-002"
    assert len(result.rag_matches) == 1
    assert "Provider unavailable" in result.reason or "unavailable" in result.reason
    assert "Email automation" in result.proposal_text or "Propuesta para" in result.proposal_text
    assert result.real_cost_usd == 0.0


def test_generate_proposal_empty_rag_still_works():
    mock_rag = AsyncMock(return_value={
        "results": [],
        "total": 0,
        "source": "supabase",
        "embedding_model": "text-embedding-3-small",
    })

    mock_provider = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Propuesta generada sin workflows previos relevantes."
    mock_response.model = "kimi-k2.6"
    mock_response.usage = MagicMock(input_tokens=200, output_tokens=300)
    mock_provider.chat = AsyncMock(return_value=mock_response)

    with (
        patch("app.services.proposal_service.query_chunks", mock_rag),
        patch("app.services.proposal_service.get_provider_client", return_value=mock_provider),
        patch("app.services.proposal_service.provider_for", return_value="openrouter"),
    ):
        from app.services.proposal_service import generate_proposal

        result = asyncio.run(generate_proposal(ProposalGenerateRequest(
            licitacion_id="LIC-NEW-999",
            title="Servicio completamente nuevo",
            description="No hay precedentes en el catálogo.",
        )))

    assert result.allowed is True
    assert result.rag_total == 0
    assert result.rag_matches == []
    assert result.proposal_text != ""


# ---------------------------------------------------------------------------
# Integration: /proposal/generate endpoint (FastAPI test client)
# ---------------------------------------------------------------------------

def test_proposal_generate_endpoint_exists():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.post(
        "/proposal/generate",
        json={
            "licitacion_id": "LIC-TEST",
            "title": "Test tender",
            "description": "Test description",
        },
        headers={"X-ANTS-API-Key": "test-key"},
    )
    # 401/403 = auth check hit; 503 = endpoint exists but DB unreachable in test env
    assert resp.status_code in (200, 401, 403, 503)
