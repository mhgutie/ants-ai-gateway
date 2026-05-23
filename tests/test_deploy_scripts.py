import shutil
import subprocess
from pathlib import Path

import pytest


def test_vps_deploy_script_uses_supabase_compose_override():
    script = Path("scripts/deploy_vps_supabase.sh").read_text()

    assert "docker-compose.supabase.yml" in script
    assert "docker network inspect" in script
    assert "if [ ! -f .env" in script
    assert 'if [ -z "${ANTS_KEY}" ]' in script
    assert "--connect-timeout" in script
    assert "--max-time" in script
    assert "/dependencies" in script
    assert "seq 1 20" in script
    assert "docker compose logs --tail 120" in script
    assert "ANTS_GATEWAY_API_KEY" in script


def test_direct_provider_smoke_script_targets_deepseek_and_kimi():
    script = Path("scripts/smoke_direct_providers.sh").read_text()

    assert "if [ ! -f .env" in script
    assert 'if [ -z "${ANTS_KEY}" ]' in script
    assert "--connect-timeout" in script
    assert "--max-time" in script
    assert '"provider":"deepseek"' in script
    assert '"model":"deepseek-v4-flash"' in script
    assert '"provider":"kimi"' in script
    assert '"model":"kimi-k2.6"' in script


def test_ant12_evidence_script_collects_required_checks_without_secret_echoes():
    script = Path("scripts/collect_ant12_vps_evidence.sh").read_text()

    assert "check_no_public_db_ports" in script
    assert "0\\.0\\.0\\.0" in script
    assert ":5432|:6543" in script
    assert "/health" in script
    assert "/dependencies" in script
    assert "X-ANTS-API-Key" in script
    assert "docker compose logs --tail=30 supabase-pooler" in script
    assert "docker compose logs --tail=30 supabase-kong" in script
    assert "printenv" not in script
    assert "env |" not in script


@pytest.mark.parametrize(
    ("script_name", "env_text"),
    [
        ("deploy_vps_supabase.sh", "ANTS_GATEWAY_PORT=8010\n"),
        ("smoke_direct_providers.sh", "ANTS_GATEWAY_PORT=8010\n"),
    ],
)
def test_scripts_fail_cleanly_when_gateway_api_key_is_absent(tmp_path, script_name, env_text):
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is required for shell script behavior tests")
    bash_probe = subprocess.run(
        [bash, "-lc", "true"],
        capture_output=True,
        text=True,
        check=False,
    )
    if bash_probe.returncode != 0:
        pytest.skip("bash runtime is not usable in this environment")

    repo = tmp_path / "repo"
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir(parents=True)
    (repo / ".env").write_text(env_text)
    script = scripts_dir / script_name
    script.write_text(Path("scripts", script_name).read_text())

    result = subprocess.run(
        [bash, str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Missing ANTS_GATEWAY_API_KEY in .env." in result.stderr
    assert "secret" not in result.stderr.lower()
