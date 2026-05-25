alter table if exists workflow_runs
    add column if not exists n8n_workflow_id text,
    add column if not exists n8n_execution_id text;

alter table if exists artifacts
    add column if not exists project_id uuid references projects(id) on delete set null,
    add column if not exists storage_provider text;

create table if not exists agent_handoffs (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references projects(id) on delete set null,
    task_id text,
    run_id text not null,
    source_agent text not null,
    target_agent text not null,
    branch text,
    status text not null default 'ready',
    completed jsonb not null default '[]'::jsonb,
    next_steps jsonb not null default '[]'::jsonb,
    risks jsonb not null default '[]'::jsonb,
    artifact_links jsonb not null default '[]'::jsonb,
    sanitized_context text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_workflow_runs_n8n_execution_id on workflow_runs(n8n_execution_id);
create index if not exists idx_artifacts_project_id on artifacts(project_id);
create index if not exists idx_agent_handoffs_task_run on agent_handoffs(task_id, run_id);
create index if not exists idx_agent_handoffs_project_id on agent_handoffs(project_id);

alter table if exists agent_handoffs enable row level security;
revoke all on agent_handoffs from anon, authenticated;
