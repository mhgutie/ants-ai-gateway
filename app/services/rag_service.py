from __future__ import annotations

import json
import logging
from typing import Any

from app.db import db_connection
from app.services.embedding_service import chunk_text, embed_texts, EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)

# In-memory fallback store for offline / test environments
_MOCK_CHUNKS: list[dict[str, Any]] = []


async def index_document(
    document_id: str,
    content: str,
    title: str | None = None,
    project_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    chunk_size: int = 1800,
    chunk_overlap: int = 200,
) -> dict[str, Any]:
    """Chunk content, embed each chunk, and store in document_chunks table.

    Returns a summary dict with chunk count and embedding model info.
    """
    meta = metadata or {}
    chunks = chunk_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not chunks:
        return {
            "document_id": document_id,
            "chunks_indexed": 0,
            "embedding_model": "text-embedding-3-small",
            "stored_in": "none",
        }

    embeddings = await embed_texts(chunks)

    try:
        async with db_connection() as conn:
            if conn is None:
                raise RuntimeError("No DB connection")

            # Remove existing chunks for this document (idempotent re-index)
            await conn.execute(
                "delete from document_chunks where document_id = $1", document_id
            )

            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
                await conn.execute(
                    """
                    insert into document_chunks
                        (project_id, document_id, title, chunk_index, content, embedding, metadata)
                    values ($1, $2, $3, $4, $5, $6::vector, $7)
                    """,
                    project_id,
                    document_id,
                    title,
                    idx,
                    chunk,
                    vec_str,
                    json.dumps(meta),
                )

            return {
                "document_id": document_id,
                "chunks_indexed": len(chunks),
                "embedding_model": "text-embedding-3-small",
                "stored_in": "supabase",
            }

    except Exception as exc:
        logger.warning("DB unavailable for RAG index (%s). Using mock store.", exc)
        _MOCK_CHUNKS[:] = [c for c in _MOCK_CHUNKS if c["document_id"] != document_id]
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            _MOCK_CHUNKS.append({
                "document_id": document_id,
                "title": title,
                "chunk_index": idx,
                "content": chunk,
                "embedding": embedding,
                "metadata": meta,
                "project_id": project_id,
            })
        return {
            "document_id": document_id,
            "chunks_indexed": len(chunks),
            "embedding_model": "text-embedding-3-small",
            "stored_in": "mock",
        }


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def query_chunks(
    query: str,
    project_id: str | None = None,
    top_k: int = 5,
    threshold: float = 0.5,
    document_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Embed the query and return the top-k most similar document chunks."""
    query_embeddings = await embed_texts([query])
    query_vec = query_embeddings[0]

    try:
        async with db_connection() as conn:
            if conn is None:
                raise RuntimeError("No DB connection")

            vec_str = "[" + ",".join(str(v) for v in query_vec) + "]"

            filters = []
            args: list[Any] = [vec_str, top_k]
            arg_idx = 3

            if project_id:
                filters.append(f"project_id = ${arg_idx}")
                args.append(project_id)
                arg_idx += 1
            if document_ids:
                filters.append(f"document_id = any(${arg_idx}::text[])")
                args.append(document_ids)
                arg_idx += 1

            where = ("where " + " and ".join(filters)) if filters else ""
            similarity_threshold = f"having 1 - (embedding <=> $1::vector) >= {threshold}"

            sql = f"""
            select
                document_id,
                title,
                chunk_index,
                content,
                metadata,
                1 - (embedding <=> $1::vector) as score
            from document_chunks
            {where}
            group by document_id, title, chunk_index, content, metadata, embedding
            {similarity_threshold}
            order by score desc
            limit $2
            """

            rows = await conn.fetch(sql, *args)
            results = [
                {
                    "document_id": r["document_id"],
                    "title": r["title"],
                    "chunk_index": r["chunk_index"],
                    "content": r["content"],
                    "score": float(r["score"]),
                    "metadata": r["metadata"] if isinstance(r["metadata"], dict) else {},
                }
                for r in rows
            ]
            return {
                "query": query,
                "results": results,
                "total": len(results),
                "embedding_model": "text-embedding-3-small",
                "source": "supabase",
            }

    except Exception as exc:
        logger.warning("DB unavailable for RAG query (%s). Using mock store.", exc)
        query_vec_fallback = query_vec

        scored = []
        for chunk in _MOCK_CHUNKS:
            if project_id and chunk.get("project_id") != project_id:
                continue
            if document_ids and chunk["document_id"] not in document_ids:
                continue
            score = _cosine_similarity(query_vec_fallback, chunk["embedding"])
            if score >= threshold:
                scored.append({**chunk, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        results = [
            {
                "document_id": c["document_id"],
                "title": c.get("title"),
                "chunk_index": c["chunk_index"],
                "content": c["content"],
                "score": c["score"],
                "metadata": c.get("metadata", {}),
            }
            for c in scored[:top_k]
        ]
        return {
            "query": query,
            "results": results,
            "total": len(results),
            "embedding_model": "text-embedding-3-small",
            "source": "mock",
        }
