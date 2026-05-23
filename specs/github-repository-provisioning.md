# GitHub Repository Provisioning

## Problem

ANTS needs to create GitHub repositories as part of its solution factory workflow, but repository creation must be governed, auditable, and safe. The current Codex GitHub connector can work with existing repositories, but does not expose repository creation.

## Expected Result

Expose a protected repository provisioning endpoint that can create a GitHub repository using a runtime token, without storing or returning the token.

## Technical Specification

- Add `POST /github/repositories`.
- Require the existing `X-ANTS-API-Key`.
- Read GitHub credentials only from `GITHUB_TOKEN` or `ANTS_GITHUB_TOKEN`.
- Never accept GitHub tokens in the request body.
- Default to `dry_run: true`.
- Require `explicitly_authorized: true` and `dry_run: false` for live creation.
- Validate repository names before calling GitHub.
- Support creating repositories for the authenticated user or an organization.
- Return only safe repository metadata.
- Hide GitHub response bodies from errors to avoid leaking unexpected details.

## Acceptance Criteria

- Missing token returns a safe configuration error.
- Dry-run returns the intended endpoint and payload without making an HTTP call.
- Live creation is blocked unless explicitly authorized.
- Invalid repository names are rejected locally.
- GitHub errors are sanitized.
- Tests cover validation, dry-run, authorization, missing token, success, and sanitized error handling.

## Harness

```bash
pytest
```

Operational smoke test:

```bash
curl -s -X POST http://localhost:8010/github/repositories \
  -H "Content-Type: application/json" \
  -H "X-ANTS-API-Key: $ANTS_KEY" \
  -d '{"name":"ants-ai-gateway","visibility":"public","dry_run":true}'
```
