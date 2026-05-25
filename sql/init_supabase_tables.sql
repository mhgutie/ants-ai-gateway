create extension if not exists pgcrypto;

create table if not exists projects (
    id uuid primary key default gen_random_uuid(),
    project_key text unique,
    name text not null,
    status text not null default 'active',
    owner text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists specs (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references projects(id) on delete set null,
    task_id text,
    title text not null,
    problem text not null,
    context jsonb not null default '{}'::jsonb,
    expected_result text,
    allowed_tools jsonb not null default '[]'::jsonb,
    required_agents_models jsonb not null default '[]'::jsonb,
    routing_decision jsonb not null default '{}'::jsonb,
    acceptance_criteria jsonb not null default '[]'::jsonb,
    risks jsonb not null default '[]'::jsonb,
    token_cost_budget jsonb not null default '{}'::jsonb,
    test_harness jsonb not null default '{}'::jsonb,
    final_output text,
    status text not null default 'draft',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists tasks (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references projects(id) on delete set null,
    spec_id uuid references specs(id) on delete set null,
    task_id text not null,
    title text not null,
    status text not null default 'backlog',
    priority text,
    owner_agent text,
    linear_issue_key text,
    linear_issue_url text,
    github_branch text,
    github_pr_url text,
    acceptance_criteria jsonb not null default '[]'::jsonb,
    definition_of_done jsonb not null default '[]'::jsonb,
    decision_log jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists model_usage (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references projects(id) on delete set null,
    task_id text not null,
    run_id text not null,
    provider text not null,
    model text not null,
    task_type text not null,
    input_tokens_estimated int not null,
    input_tokens_real int,
    output_tokens_real int,
    total_tokens_real int,
    estimated_cost_usd numeric not null,
    real_cost_usd numeric,
    latency_ms int,
    status text not null,
    stop_reason text,
    created_at timestamptz not null default now()
);

create table if not exists agent_runs (
    id uuid primary key default gen_random_uuid(),
    task_id text not null,
    run_id text not null,
    agent_name text,
    task_type text not null,
    selected_model text,
    fallback_model text,
    iteration int,
    status text not null,
    error_message text,
    decision_log jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists tool_runs (
    id uuid primary key default gen_random_uuid(),
    task_id text,
    run_id text not null,
    tool_name text not null,
    provider text,
    status text not null,
    input_summary jsonb not null default '{}'::jsonb,
    output_summary jsonb not null default '{}'::jsonb,
    error_message text,
    latency_ms int,
    created_at timestamptz not null default now()
);

create table if not exists workflow_runs (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references projects(id) on delete set null,
    task_id text,
    run_id text not null,
    workflow_name text not null,
    workflow_version text,
    orchestrator text not null default 'n8n',
    n8n_workflow_id text,
    n8n_execution_id text,
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
create table if not exists harness_results (
    id uuid primary key default gen_random_uuid(),
    task_id text,
    run_id text,
    harness_type text not null,
    status text not null,
    score numeric,
    findings jsonb not null default '[]'::jsonb,
    evidence jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists artifacts (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references projects(id) on delete set null,
    task_id text,
    run_id text,
    artifact_type text not null,
    name text not null,
    uri text not null,
    storage_provider text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

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

create table if not exists knowledge_chunks (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references projects(id) on delete set null,
    source_uri text,
    chunk_index int,
    content text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists decisions (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references projects(id) on delete set null,
    task_id text,
    decision text not null,
    rationale text,
    owner text,
    system_of_record text,
    reference_links jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists model_routes (
    id uuid primary key default gen_random_uuid(),
    task_type text not null unique,
    primary_model text not null,
    fallback_model text,
    validator_model text,
    enabled boolean not null default true,
    notes text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists cost_budgets (
    id uuid primary key default gen_random_uuid(),
    scope text not null,
    scope_id text,
    task_type text,
    max_total_cost_usd numeric not null,
    max_iterations int not null,
    max_input_tokens_per_call int not null,
    max_output_tokens_per_call int not null,
    enabled boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists service_health (
    id uuid primary key default gen_random_uuid(),
    service_name text not null,
    status text not null,
    details jsonb not null default '{}'::jsonb,
    checked_at timestamptz not null default now()
);

create table if not exists secrets_registry (
    id uuid primary key default gen_random_uuid(),
    secret_name text not null,
    provider text,
    storage_ref text not null,
    owner text,
    rotation_policy text,
    last_rotated_at timestamptz,
    created_at timestamptz not null default now()
);

create table if not exists reusable_patterns (
    id uuid primary key default gen_random_uuid(),
    pattern_type text not null,
    name text not null,
    description text,
    source_task_id text,
    content jsonb not null default '{}'::jsonb,
    validation_status text not null default 'unvalidated',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_model_usage_task_run on model_usage(task_id, run_id);
create index if not exists idx_model_usage_project_id on model_usage(project_id);
create index if not exists idx_agent_runs_task_run on agent_runs(task_id, run_id);
create index if not exists idx_specs_project_id on specs(project_id);
create index if not exists idx_tasks_project_id on tasks(project_id);
create index if not exists idx_tasks_task_id on tasks(task_id);
create index if not exists idx_tasks_linear_issue_key on tasks(linear_issue_key);
create index if not exists idx_tool_runs_task_run on tool_runs(task_id, run_id);
create index if not exists idx_workflow_runs_task_run on workflow_runs(task_id, run_id);
create index if not exists idx_workflow_runs_project_id on workflow_runs(project_id);
create index if not exists idx_workflow_runs_n8n_execution_id on workflow_runs(n8n_execution_id);
create index if not exists idx_harness_results_task_run on harness_results(task_id, run_id);
create index if not exists idx_artifacts_task_run on artifacts(task_id, run_id);
create index if not exists idx_artifacts_project_id on artifacts(project_id);
create index if not exists idx_agent_handoffs_task_run on agent_handoffs(task_id, run_id);
create index if not exists idx_agent_handoffs_project_id on agent_handoffs(project_id);
create index if not exists idx_knowledge_chunks_project_id on knowledge_chunks(project_id);
create index if not exists idx_decisions_project_task on decisions(project_id, task_id);
create index if not exists idx_service_health_service_name on service_health(service_name);

alter table if exists projects enable row level security;
alter table if exists specs enable row level security;
alter table if exists tasks enable row level security;
alter table if exists model_usage enable row level security;
alter table if exists agent_runs enable row level security;
alter table if exists tool_runs enable row level security;
alter table if exists workflow_runs enable row level security;
alter table if exists harness_results enable row level security;
alter table if exists artifacts enable row level security;
alter table if exists agent_handoffs enable row level security;
alter table if exists knowledge_chunks enable row level security;
alter table if exists decisions enable row level security;
alter table if exists model_routes enable row level security;
alter table if exists cost_budgets enable row level security;
alter table if exists service_health enable row level security;
alter table if exists secrets_registry enable row level security;
alter table if exists reusable_patterns enable row level security;

revoke all on projects from anon, authenticated;
revoke all on specs from anon, authenticated;
revoke all on tasks from anon, authenticated;
revoke all on model_usage from anon, authenticated;
revoke all on agent_runs from anon, authenticated;
revoke all on tool_runs from anon, authenticated;
revoke all on workflow_runs from anon, authenticated;
revoke all on harness_results from anon, authenticated;
revoke all on artifacts from anon, authenticated;
revoke all on agent_handoffs from anon, authenticated;
revoke all on knowledge_chunks from anon, authenticated;
revoke all on decisions from anon, authenticated;
revoke all on model_routes from anon, authenticated;
revoke all on cost_budgets from anon, authenticated;
revoke all on service_health from anon, authenticated;
revoke all on secrets_registry from anon, authenticated;
revoke all on reusable_patterns from anon, authenticated;
