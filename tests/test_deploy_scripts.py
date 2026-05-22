from pathlib import Path


def test_vps_deploy_script_uses_supabase_compose_override():
    script = Path("scripts/deploy_vps_supabase.sh").read_text()

    assert "docker-compose.supabase.yml" in script
    assert "docker network inspect" in script
    assert "/dependencies" in script
    assert "seq 1 20" in script
    assert "docker compose logs --tail 120" in script
    assert "ANTS_GATEWAY_API_KEY" in script


def test_direct_provider_smoke_script_targets_deepseek_and_kimi():
    script = Path("scripts/smoke_direct_providers.sh").read_text()

    assert '"provider":"deepseek"' in script
    assert '"model":"deepseek-v4-flash"' in script
    assert '"provider":"kimi"' in script
    assert '"model":"kimi-k2.6"' in script
