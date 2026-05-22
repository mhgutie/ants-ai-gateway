from pathlib import Path


SQL_PATH = Path(__file__).resolve().parents[1] / "sql" / "init_supabase_tables.sql"


def test_operational_ledger_tables_exist():
    sql = SQL_PATH.read_text(encoding="utf-8").lower()
    required_tables = [
        "projects",
        "specs",
        "tasks",
        "agent_runs",
        "tool_runs",
        "harness_results",
        "artifacts",
        "knowledge_chunks",
        "model_usage",
        "decisions",
        "model_routes",
        "cost_budgets",
        "service_health",
        "secrets_registry",
        "reusable_patterns",
    ]
    for table in required_tables:
        assert f"create table if not exists {table}" in sql


def test_tasks_schema_links_linear_and_github_traceability():
    sql = SQL_PATH.read_text(encoding="utf-8").lower()
    assert "linear_issue_key text" in sql
    assert "github_branch text" in sql
    assert "github_pr_url text" in sql


def test_secrets_registry_stores_references_not_secret_values():
    sql = SQL_PATH.read_text(encoding="utf-8").lower()
    secrets_section = sql.split("create table if not exists secrets_registry", 1)[1]
    secrets_section = secrets_section.split(");", 1)[0]
    assert "storage_ref text not null" in secrets_section
    assert "secret_value" not in secrets_section


def test_operational_tables_enable_rls_and_revoke_public_roles():
    sql = SQL_PATH.read_text(encoding="utf-8").lower()
    required_tables = [
        "projects",
        "specs",
        "tasks",
        "model_usage",
        "agent_runs",
        "tool_runs",
        "harness_results",
        "artifacts",
        "knowledge_chunks",
        "decisions",
        "model_routes",
        "cost_budgets",
        "service_health",
        "secrets_registry",
        "reusable_patterns",
    ]
    for table in required_tables:
        assert f"alter table if exists {table} enable row level security;" in sql
        assert f"revoke all on {table} from anon, authenticated;" in sql
