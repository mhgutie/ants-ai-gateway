import asyncio

import httpx
import pytest

from app.github_repositories import (
    GitHubRepositoryProvisioningError,
    create_github_repository,
    repository_endpoint,
    repository_payload,
    validate_repository_name,
)
from app.schemas import GitHubRepositoryCreateRequest


def test_repository_name_validation_rejects_unsafe_names():
    for name in ["", "../secret", "repo.git", "bad name", "a" * 101]:
        with pytest.raises(GitHubRepositoryProvisioningError):
            validate_repository_name(name)


def test_repository_name_validation_accepts_common_names():
    validate_repository_name("ants-ai-gateway")
    validate_repository_name("careerlab_lite")
    validate_repository_name("dr.server")


def test_repository_endpoint_defaults_to_authenticated_user(monkeypatch):
    monkeypatch.setenv("GITHUB_API_BASE_URL", "https://api.github.test")
    request = GitHubRepositoryCreateRequest(name="ants-ai-gateway")

    assert repository_endpoint(request) == "https://api.github.test/user/repos"


def test_repository_endpoint_supports_organizations(monkeypatch):
    monkeypatch.setenv("GITHUB_API_BASE_URL", "https://api.github.test/")
    request = GitHubRepositoryCreateRequest(name="ants-ai-gateway", owner_type="organization", owner="ants")

    assert repository_endpoint(request) == "https://api.github.test/orgs/ants/repos"


def test_repository_payload_is_safe_and_does_not_include_tokens():
    request = GitHubRepositoryCreateRequest(
        name="ants-ai-gateway",
        description="ANTS gateway",
        visibility="public",
    )

    payload = repository_payload(request)

    assert payload["name"] == "ants-ai-gateway"
    assert payload["private"] is False
    assert "token" not in str(payload).lower()


def test_create_repository_dry_run_does_not_require_token(monkeypatch):
    monkeypatch.delenv("ANTS_GITHUB_TOKEN", raising=False)
    request = GitHubRepositoryCreateRequest(name="ants-ai-gateway", visibility="public")

    response = asyncio.run(create_github_repository(request))

    assert response.dry_run is True
    assert response.created is False
    assert response.full_name == "authenticated-user/ants-ai-gateway"


def test_create_repository_live_requires_explicit_authorization(monkeypatch):
    monkeypatch.setenv("ANTS_GITHUB_TOKEN", "not-a-real-token")
    request = GitHubRepositoryCreateRequest(name="ants-ai-gateway", dry_run=False)

    with pytest.raises(GitHubRepositoryProvisioningError) as exc_info:
        asyncio.run(create_github_repository(request))

    assert "explicitly_authorized" in str(exc_info.value)


def test_create_repository_live_requires_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("ANTS_GITHUB_TOKEN", raising=False)
    request = GitHubRepositoryCreateRequest(name="ants-ai-gateway", dry_run=False, explicitly_authorized=True)

    with pytest.raises(GitHubRepositoryProvisioningError) as exc_info:
        asyncio.run(create_github_repository(request))

    assert str(exc_info.value) == "GitHub token is not configured."


def test_create_repository_success_is_sanitized(monkeypatch):
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, endpoint, json, headers):
            assert headers["Authorization"] == "Bearer secret-token"
            assert "secret-token" not in str(json)
            return httpx.Response(
                201,
                json={
                    "name": "ants-ai-gateway",
                    "full_name": "mhgutie/ants-ai-gateway",
                    "owner": {"login": "mhgutie"},
                    "private": False,
                    "visibility": "public",
                    "html_url": "https://github.com/mhgutie/ants-ai-gateway",
                    "clone_url": "https://github.com/mhgutie/ants-ai-gateway.git",
                    "default_branch": "main",
                },
            )

    monkeypatch.setenv("ANTS_GITHUB_TOKEN", "secret-token")
    monkeypatch.setattr("app.github_repositories.httpx.AsyncClient", FakeClient)
    request = GitHubRepositoryCreateRequest(
        name="ants-ai-gateway",
        visibility="public",
        dry_run=False,
        explicitly_authorized=True,
    )

    response = asyncio.run(create_github_repository(request))

    assert response.created is True
    assert response.full_name == "mhgutie/ants-ai-gateway"
    assert "secret" not in response.model_dump_json().lower()


def test_create_repository_error_is_sanitized(monkeypatch):
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, endpoint, json, headers):
            return httpx.Response(422, json={"message": "token-like detail should not be returned"})

    monkeypatch.setenv("ANTS_GITHUB_TOKEN", "secret-token")
    monkeypatch.setattr("app.github_repositories.httpx.AsyncClient", FakeClient)
    request = GitHubRepositoryCreateRequest(
        name="ants-ai-gateway",
        dry_run=False,
        explicitly_authorized=True,
    )

    with pytest.raises(GitHubRepositoryProvisioningError) as exc_info:
        asyncio.run(create_github_repository(request))

    assert str(exc_info.value) == "GitHub repository creation failed with status 422."
