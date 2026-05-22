# ADR 0001: Separate Gateway Governance From Executor Runtime

## Status

Accepted

## Context

ANTS needs to coordinate model routing, cost control, secret hygiene, harness validation, and agentic execution through tools such as Codex, Claude Code, and Antigravity.

During the first executor setup on the VPS, the gateway ran correctly inside Docker while Codex and Claude Code were installed and authenticated on the VPS host. This revealed a useful architectural boundary:

- The gateway is best suited to governance: validate requests, enforce policy, estimate cost, route work, expose safe APIs, and log evidence.
- Agentic coding tools are best suited to the executor runtime: authenticated host sessions, CLI-specific behavior, workspace access, and real file/process interaction.

Trying to put all executor authentication, CLIs, OAuth sessions, and live workspace permissions inside the gateway would couple a public-facing API service to operational credentials and tool-specific runtime behavior.

## Decision

ANTS will keep the AI gateway separate from the executor runtime.

The gateway must:

- Validate specs, harness requirements, budgets, and allowed roots.
- Authorize or reject executor requests.
- Expose safe executor status and smoke-test endpoints.
- Sanitize logs and outputs.
- Store metadata, evidence, decisions, and usage in Supabase.
- Avoid storing or returning raw executor tokens.

The executor runtime must:

- Run Codex, Claude Code, Antigravity, or future agentic tools.
- Own official CLI/OAuth/device-auth sessions on the host or in a dedicated executor container.
- Execute only authorized tasks under configured workspace roots.
- Return structured, sanitized execution evidence to the gateway.

The future implementation should introduce an `executor-service` or equivalent adapter rather than expanding the gateway into a general command runner.

## Consequences

Positive:

- Keeps the gateway smaller, safer, and easier to reason about.
- Avoids placing live OAuth sessions and agentic CLIs in the same container as the gateway API.
- Allows executor runtimes to evolve independently per tool.
- Matches the ANTS rule: gateway governs, harness validates, executors act, Supabase remembers.

Trade-offs:

- Requires an additional local service or adapter.
- Adds one more internal API boundary to secure.
- Requires explicit deployment and health checks for executor runtime availability.

## Implementation Notes

Initial smoke testing may use host-side scripts to validate CLI availability and authentication. Production-grade execution should use a dedicated executor adapter with:

- Fixed command templates.
- No shell interpolation.
- Closed stdin for non-interactive CLI calls.
- Timeouts.
- Allowed roots enforcement.
- Secret redaction.
- Harness evidence collection.
- Supabase `tool_runs` or equivalent logging.

## Serendipity Note

This decision came from deployment reality rather than pure design. The gateway-container versus host-executor split first appeared as a friction point, but it revealed the cleaner ANTS architecture: the gateway should be the referee, not the player.
