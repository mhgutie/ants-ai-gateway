from __future__ import annotations

import os
import re
from typing import Any

import httpx

from app.config import get_settings
from app.schemas import GitHubRepositoryCreateRequest, GitHubRepositoryCreateResponse


REPOSITORY_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
GITHUB_API_VERSION = "2022-11-28"


class GitHubRepositoryProvisioningError(RuntimeError):
    pass


def github_token() -> str | None:
    return os.getenv("GITHUB_TOKEN") or os.getenv("ANTS_GITHUB_TOKEN")


def validate_repository_name(name: str) -> None:
    if not name or len(name) > 100:
        raise GitHubRepositoryProvisioningError("Repository name must be between 1 and 100 characters.")
    if name in {".", ".."} or name.endswith(".git"):
        raise GitHubRepositoryProvisioningError("Repository name is not allowed.")
    if not REPOSITORY_NAME_PATTERN.fullmatch(name):
        raise GitHubRepositoryProvisioningError(
            "Repository name may contain only letters, numbers, dots, underscores, and hyphens."
        )


def repository_endpoint(request: GitHubRepositoryCreateRequest) -> str:
    base_url = os.getenv("GITHUB_API_BASE_URL", "https://api.github.com").rstrip("/")
    if request.owner_type == "organization":
        if not request.owner:
            raise GitHubRepositoryProvisioningError("Organization repository creation requires owner.")
        return f"{base_url}/orgs/{request.owner}/repos"
    return f"{base_url}/user/repos"


def repository_payload(request: GitHubRepositoryCreateRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": request.name,
        "description": request.description,
        "private": request.visibility == "private",
        "has_issues": request.has_issues,
        "has_projects": request.has_projects,
        "has_wiki": request.has_wiki,
        "auto_init": request.auto_init,
        "allow_squash_merge": request.allow_squash_merge,
        "allow_merge_commit": request.allow_merge_commit,
        "allow_rebase_merge": request.allow_rebase_merge,
        "delete_branch_on_merge": request.delete_branch_on_merge,
    }
    return {key: value for key, value in payload.items() if value is not None}


def safe_repository_response(data: dict[str, Any], dry_run: bool, endpoint: str) -> GitHubRepositoryCreateResponse:
    return GitHubRepositoryCreateResponse(
        dry_run=dry_run,
        created=not dry_run,
        name=str(data.get("name", "")),
        full_name=str(data.get("full_name", data.get("name", ""))),
        owner=str(data.get("owner", {}).get("login", "")) if isinstance(data.get("owner"), dict) else None,
        visibility=str(data.get("visibility", "private" if data.get("private") else "public")),
        private=bool(data.get("private", False)),
        html_url=data.get("html_url"),
        clone_url=data.get("clone_url"),
        default_branch=data.get("default_branch"),
        api_endpoint=endpoint,
        reason="Dry run only. No GitHub repository was created." if dry_run else "Repository created.",
    )


async def create_github_repository(request: GitHubRepositoryCreateRequest) -> GitHubRepositoryCreateResponse:
    validate_repository_name(request.name)
    endpoint = repository_endpoint(request)
    payload = repository_payload(request)

    if request.dry_run:
        dry_run_data = {
            "name": request.name,
            "full_name": f"{request.owner or 'authenticated-user'}/{request.name}",
            "owner": {"login": request.owner or "authenticated-user"},
            "private": request.visibility == "private",
            "visibility": request.visibility,
        }
        return safe_repository_response(dry_run_data, dry_run=True, endpoint=endpoint)

    if not request.explicitly_authorized:
        raise GitHubRepositoryProvisioningError("Live repository creation requires explicitly_authorized=true.")

    token = github_token()
    if not token:
        raise GitHubRepositoryProvisioningError("GitHub token is not configured.")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": "ants-ai-gateway",
    }
    timeout_seconds = get_settings().request_timeout_seconds

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(endpoint, json=payload, headers=headers)

    if response.status_code != 201:
        raise GitHubRepositoryProvisioningError(f"GitHub repository creation failed with status {response.status_code}.")

    return safe_repository_response(response.json(), dry_run=False, endpoint=endpoint)
