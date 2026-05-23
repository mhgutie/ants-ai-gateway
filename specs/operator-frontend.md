# ANT-20 Operator Frontend

## Functional Specification

ANTS operators need a local browser surface to inspect gateway health, protected dependency status, model routing configuration, preflight decisions, executor policy, executor sessions, credential-pool status, and executor smoke checks.

The frontend must make the existing FastAPI gateway easier to operate without becoming a second source of truth. It should display live responses from the gateway and keep all durable memory, logs, costs, and decisions in Supabase or the existing repository records.

## Technical Specification

- Serve a static frontend from the existing FastAPI app at `/ui`.
- Serve static assets from `/ui/assets`.
- Use the existing protected API endpoints and send `X-ANTS-API-Key` from the browser.
- Avoid a separate JavaScript build pipeline for this first operator console.
- Keep the interface read-heavy, with only existing explicit actions: preflight and executor smoke test.
- Do not add provider execution from the UI in this iteration.

## Acceptance Criteria

- `/ui` returns the operator console HTML.
- `/ui/assets/app.js` and `/ui/assets/styles.css` are served by the gateway.
- The console supports health, dependencies, credentials, models, executors, sessions, preflight, and smoke-test flows.
- No secrets, tokens, `.env` files, or credential blobs are committed.
- `pytest` passes.

## Model and Tool Routing

- Codex implements repository changes.
- FastAPI serves the operator frontend.
- Existing gateway routes remain the backend contract.
- Validation uses repository pytest harness and GitHub Secret Scan after PR update.

## Harness

- Static endpoint tests validate `/ui` and asset serving.
- Existing endpoint tests continue to cover gateway API behavior.
- Full `pytest` validates the repository.

## Out of Scope

- Auth sessions beyond the current gateway key header.
- Provider chat execution from the UI.
- Supabase writes from the frontend.
- New Convex reactive state.
