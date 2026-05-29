from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


def _api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI__DEFAULT__API_KEY", "")
    return key.strip()


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Get embeddings for a list of texts using OpenAI text-embedding-3-small.

    Batches all texts in a single API call (OpenAI supports up to 2048 inputs).
    Falls back to zero vectors when the API key is missing or the call fails,
    so the service degrades gracefully in offline / test environments.
    """
    api_key = _api_key()
    if not api_key:
        logger.warning("OPENAI_API_KEY not configured — returning zero embeddings.")
        return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OPENAI_EMBEDDINGS_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": texts,
                    "dimensions": EMBEDDING_DIMENSIONS,
                    "encoding_format": "float",
                },
            )
            response.raise_for_status()
            data: list[dict[str, Any]] = sorted(
                response.json()["data"], key=lambda x: x["index"]
            )
            return [item["embedding"] for item in data]
    except Exception as exc:
        logger.warning("Embedding API call failed: %s — returning zero vectors.", exc)
        return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]


def chunk_text(
    text: str,
    chunk_size: int = 1800,
    chunk_overlap: int = 200,
) -> list[str]:
    """Split text into overlapping chunks by paragraph boundaries.

    Prefers splitting at double-newline paragraph breaks. Falls back to
    character-level splitting when a paragraph exceeds chunk_size.
    """
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(para) > chunk_size:
            # Split oversized paragraph at character level
            if current:
                chunks.append(current.strip())
                current = current[-chunk_overlap:] if len(current) > chunk_overlap else current
            for i in range(0, len(para), chunk_size - chunk_overlap):
                piece = para[i : i + chunk_size]
                if piece.strip():
                    chunks.append(piece.strip())
            current = para[-(chunk_overlap):]
        elif len(current) + len(para) + 2 > chunk_size:
            chunks.append(current.strip())
            current = current[-chunk_overlap:] + "\n\n" + para if len(current) > chunk_overlap else para
        else:
            current = (current + "\n\n" + para).strip() if current else para

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if c]
