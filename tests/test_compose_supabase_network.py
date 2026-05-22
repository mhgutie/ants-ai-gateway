from pathlib import Path

import yaml


def test_supabase_compose_override_uses_external_network():
    compose = yaml.safe_load(Path("docker-compose.supabase.yml").read_text())

    service_networks = compose["services"]["ants-ai-gateway"]["networks"]
    supabase_network = compose["networks"]["supabase"]

    assert service_networks == ["default", "supabase"]
    assert supabase_network["external"] is True
    assert supabase_network["name"] == "${ANTS_SUPABASE_DOCKER_NETWORK:-supabase_default}"
