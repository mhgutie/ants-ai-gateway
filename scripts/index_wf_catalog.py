#!/usr/bin/env python3
"""
ANTS WF Catalog RAG Indexer
===========================
Reads wf_solution_catalog from Supabase, generates OpenAI embeddings in batches
of 2048, and stores chunks in document_chunks for semantic search via /rag/query.

Usage (on VPS):
    cd ~/ants-apps/ants-ai-gateway
    python scripts/index_wf_catalog.py [--dry-run] [--batch-size 2000] [--limit 100]

Cost estimate: ~$0.06 for all 9,551 workflows (text-embedding-3-small at $0.02/1M tokens).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# Ensure app package is importable from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import asyncpg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("wf-indexer")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
OPENAI_URL = "https://api.openai.com/v1/embeddings"
DOCUMENT_COLLECTION = "wf_solution_catalog"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if v})
    return env


def build_document_text(row: dict) -> str:
    """Compose a rich text document from a wf_solution_catalog row."""
    parts = [
        f"{row.get('workflow_name', '')} [{row.get('domain', '')} / {row.get('use_case', '')}]",
    ]
    summary = row.get("summary") or ""
    if summary:
        parts.append(summary[:2000])

    tags = row.get("tags") or []
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = [tags]
    if tags:
        parts.append("Tags: " + ", ".join(str(t) for t in tags[:20]))

    integrations = row.get("required_integrations") or []
    if isinstance(integrations, str):
        try:
            integrations = json.loads(integrations)
        except Exception:
            integrations = [integrations]
    if integrations:
        parts.append("Integrations: " + ", ".join(str(i) for i in integrations[:10]))

    patterns = row.get("problem_patterns") or []
    if isinstance(patterns, str):
        try:
            patterns = json.loads(patterns)
        except Exception:
            patterns = [patterns]
    if patterns:
        parts.append("Solves: " + ", ".join(str(p) for p in patterns[:10]))

    return "\n".join(p for p in parts if p.strip())


async def embed_batch(texts: list[str], api_key: str) -> list[list[float]]:
    """Call OpenAI embeddings API for a batch of texts."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            OPENAI_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": EMBEDDING_MODEL, "input": texts, "dimensions": EMBEDDING_DIM, "encoding_format": "float"},
        )
        resp.raise_for_status()
        data = sorted(resp.json()["data"], key=lambda x: x["index"])
        usage = resp.json().get("usage", {})
        logger.info("  Embedded %d texts — %s tokens used", len(texts), usage.get("total_tokens", "?"))
        return [item["embedding"] for item in data]


async def run(args: argparse.Namespace) -> None:
    env = load_env()
    db_url = env.get("SUPABASE_DB_URL", "")
    openai_key = env.get("OPENAI_API_KEY") or env.get("OPENAI__DEFAULT__API_KEY", "")

    if not db_url:
        logger.error("SUPABASE_DB_URL not configured in .env")
        sys.exit(1)
    if not openai_key:
        logger.error("OPENAI_API_KEY not configured in .env")
        sys.exit(1)

    conn = await asyncpg.connect(db_url)
    logger.info("Connected to Supabase.")

    limit_clause = f"limit {args.limit}" if args.limit else ""
    rows = await conn.fetch(
        f"""
        select workflow_id, workflow_name, domain, use_case, summary,
               tags, required_integrations, problem_patterns,
               source_url, artifact_uri
        from wf_solution_catalog
        order by workflow_id
        {limit_clause}
        """
    )
    logger.info("Fetched %d workflows from wf_solution_catalog.", len(rows))

    if args.dry_run:
        sample = dict(rows[0]) if rows else {}
        text = build_document_text(sample)
        logger.info("DRY RUN — sample document text (%d chars):\n%s", len(text), text[:400])
        await conn.close()
        return

    # Build (document_id, text, metadata) tuples
    docs = []
    for row in rows:
        r = dict(row)
        text = build_document_text(r)
        if not text.strip():
            continue
        meta = {
            "domain": r.get("domain", ""),
            "use_case": r.get("use_case", ""),
            "source_url": r.get("source_url", ""),
            "artifact_uri": r.get("artifact_uri", ""),
        }
        docs.append((r["workflow_id"], r.get("workflow_name", ""), text, meta))

    logger.info("Building embeddings for %d documents in batches of %d...", len(docs), args.batch_size)

    # Clear existing chunks for this collection
    deleted = await conn.execute(
        "delete from document_chunks where document_id like 'n8n_template_%' or document_id like 'wf_%'"
    )
    logger.info("Cleared previous wf_catalog chunks: %s", deleted)

    total_inserted = 0
    t0 = time.perf_counter()

    for batch_start in range(0, len(docs), args.batch_size):
        batch = docs[batch_start : batch_start + args.batch_size]
        texts = [d[2] for d in batch]

        logger.info("Batch %d-%d: embedding...", batch_start + 1, batch_start + len(batch))
        try:
            embeddings = await embed_batch(texts, openai_key)
        except Exception as exc:
            logger.error("Batch %d-%d failed: %s — skipping.", batch_start + 1, batch_start + len(batch), exc)
            continue

        # Bulk insert
        records = []
        for (doc_id, title, text, meta), emb in zip(batch, embeddings):
            vec_str = "[" + ",".join(str(v) for v in emb) + "]"
            records.append((doc_id, title, 0, text, vec_str, json.dumps(meta)))

        await conn.executemany(
            """
            insert into document_chunks (document_id, title, chunk_index, content, embedding, metadata)
            values ($1, $2, $3, $4, $5::vector, $6)
            on conflict do nothing
            """,
            records,
        )
        total_inserted += len(records)
        elapsed = time.perf_counter() - t0
        logger.info("  Inserted %d chunks (total: %d) — %.1fs elapsed", len(records), total_inserted, elapsed)

        # Respect OpenAI rate limits
        if batch_start + args.batch_size < len(docs):
            await asyncio.sleep(1.0)

    elapsed = time.perf_counter() - t0
    logger.info("Done. %d chunks indexed in %.1fs.", total_inserted, elapsed)

    # Quick verification query
    count = await conn.fetchval("select count(*) from document_chunks where document_id like 'n8n_template_%' or document_id like 'wf_%'")
    logger.info("Verification: %d wf_catalog chunks in document_chunks.", count)
    await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Index wf_solution_catalog into RAG document_chunks")
    parser.add_argument("--dry-run", action="store_true", help="Print sample doc text, skip embedding and DB writes")
    parser.add_argument("--batch-size", type=int, default=400, help="Texts per OpenAI API call — keep under 300K tokens total (~400 for wf_catalog)")
    parser.add_argument("--limit", type=int, default=0, help="Max workflows to index (0 = all)")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
