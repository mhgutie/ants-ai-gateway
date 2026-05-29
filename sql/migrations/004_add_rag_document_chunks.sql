-- Phase 6: RAG + Document Services
-- Requires pgvector extension. On Supabase self-hosted this is pre-installed.
-- On vanilla Postgres, run: CREATE EXTENSION IF NOT EXISTS vector;

create extension if not exists vector;

create table if not exists document_chunks (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references projects(id) on delete set null,
    document_id text not null,
    title text,
    chunk_index int not null,
    content text not null,
    embedding vector(1536),
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_document_chunks_document_id
    on document_chunks(document_id);

create index if not exists idx_document_chunks_project_id
    on document_chunks(project_id);

-- HNSW index for fast approximate cosine similarity search
create index if not exists idx_document_chunks_embedding_hnsw
    on document_chunks using hnsw (embedding vector_cosine_ops)
    with (m = 16, ef_construction = 64);

alter table if exists document_chunks enable row level security;
revoke all on document_chunks from anon, authenticated;
