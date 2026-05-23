alter table if exists model_usage
    add column if not exists project_id uuid references projects(id) on delete set null,
    add column if not exists latency_ms int;

create index if not exists idx_model_usage_project_id on model_usage(project_id);

create table if not exists workflow_runs (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references projects(id) on delete set null,
    task_id text,
    run_id text not null,
    workflow_name text not null,
    workflow_version text,
    orchestrator text not null default 'n8n',
    trigger_source text,
    status text not null,
    input_summary jsonb not null default '{}'::jsonb,
    output_summary jsonb not null default '{}'::jsonb,
    error_message text,
    latency_ms int,
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz not null default now()
);

create index if not exists idx_workflow_runs_task_run on workflow_runs(task_id, run_id);
create index if not exists idx_workflow_runs_project_id on workflow_runs(project_id);

alter table if exists workflow_runs enable row level security;
revoke all on workflow_runs from anon, authenticated;
