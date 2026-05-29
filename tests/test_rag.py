"""Tests for Phase 6: RAG + Document Services."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.services.embedding_service import EMBEDDING_DIMENSIONS, chunk_text
from app.services.rag_service import _cosine_similarity, index_document, query_chunks


# ---------------------------------------------------------------------------
# Unit: text chunking
# ---------------------------------------------------------------------------

def test_chunk_text_returns_empty_for_blank_input():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_single_short_paragraph():
    result = chunk_text("Hello world.")
    assert result == ["Hello world."]


def test_chunk_text_splits_by_paragraph():
    text = "Para one.\n\nPara two.\n\nPara three."
    result = chunk_text(text, chunk_size=50, chunk_overlap=10)
    assert len(result) >= 1
    assert all(isinstance(c, str) and c for c in result)


def test_chunk_text_respects_chunk_size():
    long_para = "word " * 1000  # ~5000 chars
    result = chunk_text(long_para, chunk_size=500, chunk_overlap=50)
    for chunk in result:
        assert len(chunk) <= 500 + 50 + 10  # allow slight overflow at word boundary


def test_chunk_text_overlap_carries_context():
    text = "A " * 200 + "\n\n" + "B " * 200
    chunks = chunk_text(text, chunk_size=300, chunk_overlap=100)
    assert len(chunks) >= 2


def test_chunk_text_no_empty_chunks():
    text = "\n\n".join(["paragraph"] * 20)
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
    assert all(c.strip() for c in chunks)


# ---------------------------------------------------------------------------
# Unit: cosine similarity
# ---------------------------------------------------------------------------

def test_cosine_similarity_identical_vectors():
    v = [1.0, 0.0, 0.0]
    assert _cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert _cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector_returns_zero():
    assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


# ---------------------------------------------------------------------------
# Unit: embedding_service — zero fallback when no API key
# ---------------------------------------------------------------------------

def test_embed_texts_returns_zero_vectors_without_api_key():
    with patch("app.services.embedding_service._api_key", return_value=""):
        result = asyncio.run(
            __import__("app.services.embedding_service", fromlist=["embed_texts"]).embed_texts(
                ["hello", "world"]
            )
        )
    assert len(result) == 2
    assert len(result[0]) == EMBEDDING_DIMENSIONS
    assert all(v == 0.0 for v in result[0])


# ---------------------------------------------------------------------------
# Unit: index_document — mock store fallback
# ---------------------------------------------------------------------------

def test_index_document_uses_mock_store_when_db_unavailable():
    content = "ANTS is a multi-agent solution factory.\n\nIt builds workflows and specs."

    with (
        patch("app.services.rag_service.db_connection") as mock_db,
        patch("app.services.rag_service.embed_texts", new=AsyncMock(return_value=[[0.1] * EMBEDDING_DIMENSIONS, [0.2] * EMBEDDING_DIMENSIONS])),
        patch("app.services.embedding_service._api_key", return_value=""),
    ):
        mock_db.return_value.__aenter__ = AsyncMock(return_value=None)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=False)

        result = asyncio.run(
            index_document(
                document_id="doc-test-1",
                content=content,
                title="ANTS Overview",
            )
        )

    assert result["document_id"] == "doc-test-1"
    assert result["chunks_indexed"] >= 1
    assert result["embedding_model"] == "text-embedding-3-small"


def test_index_document_empty_content_returns_zero_chunks():
    result = asyncio.run(
        index_document(document_id="doc-empty", content="")
    )
    assert result["chunks_indexed"] == 0


# ---------------------------------------------------------------------------
# Unit: query_chunks — mock store fallback
# ---------------------------------------------------------------------------

def test_query_chunks_returns_empty_when_no_documents_indexed():
    from app.services import rag_service
    original = list(rag_service._MOCK_CHUNKS)
    rag_service._MOCK_CHUNKS.clear()

    try:
        with (
            patch("app.services.rag_service.db_connection") as mock_db,
            patch("app.services.rag_service.embed_texts", new=AsyncMock(return_value=[[0.5] * EMBEDDING_DIMENSIONS])),
        ):
            mock_db.return_value.__aenter__ = AsyncMock(return_value=None)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)

            result = asyncio.run(
                query_chunks(query="test query", top_k=5, threshold=0.5)
            )
    finally:
        rag_service._MOCK_CHUNKS.extend(original)

    assert result["total"] == 0
    assert result["results"] == []
    assert result["query"] == "test query"


def test_query_chunks_returns_similar_chunks_from_mock():
    from app.services import rag_service

    base_vec = [1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1)
    similar_vec = [1.0] + [0.01] * (EMBEDDING_DIMENSIONS - 1)  # high cosine with base_vec
    unrelated_vec = [0.0] * (EMBEDDING_DIMENSIONS - 1) + [1.0]  # orthogonal to base_vec

    original = list(rag_service._MOCK_CHUNKS)
    rag_service._MOCK_CHUNKS.clear()
    rag_service._MOCK_CHUNKS.extend([
        {"document_id": "doc-a", "title": "A", "chunk_index": 0, "content": "relevant content", "embedding": similar_vec, "metadata": {}, "project_id": None},
        {"document_id": "doc-b", "title": "B", "chunk_index": 0, "content": "irrelevant content", "embedding": unrelated_vec, "metadata": {}, "project_id": None},
    ])

    try:
        with (
            patch("app.services.rag_service.db_connection") as mock_db,
            patch("app.services.rag_service.embed_texts", new=AsyncMock(return_value=[base_vec])),
        ):
            mock_db.return_value.__aenter__ = AsyncMock(return_value=None)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)

            result = asyncio.run(
                query_chunks(query="relevant", top_k=5, threshold=0.5)
            )
    finally:
        rag_service._MOCK_CHUNKS.clear()
        rag_service._MOCK_CHUNKS.extend(original)

    assert result["total"] >= 1
    assert result["results"][0]["document_id"] == "doc-a"
    assert result["results"][0]["score"] > 0.5


# ---------------------------------------------------------------------------
# Unit: SQL migration file exists and contains required DDL
# ---------------------------------------------------------------------------

def test_rag_sql_migration_exists_and_has_vector_extension():
    from pathlib import Path
    migration = Path(__file__).parent.parent / "sql" / "migrations" / "004_add_rag_document_chunks.sql"
    assert migration.exists(), "004_add_rag_document_chunks.sql must exist"
    sql = migration.read_text()
    assert "vector" in sql
    assert "document_chunks" in sql
    assert "hnsw" in sql.lower() or "ivfflat" in sql.lower() or "index" in sql.lower()
    assert "row level security" in sql.lower()


# ---------------------------------------------------------------------------
# Unit: endpoint schemas validation
# ---------------------------------------------------------------------------

def test_rag_index_request_schema():
    from app.schemas import RagIndexRequest
    req = RagIndexRequest(document_id="doc-1", content="hello world")
    assert req.chunk_size == 1800
    assert req.chunk_overlap == 200


def test_rag_query_request_schema_defaults():
    from app.schemas import RagQueryRequest
    req = RagQueryRequest(query="what is ANTS?")
    assert req.top_k == 5
    assert req.threshold == 0.5
    assert req.document_ids is None
