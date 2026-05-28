# ADR 0003: Secure External Database Ingress for n8n via Gateway HTTP Endpoints

## Status
Accepted — May 28, 2026

## Context
On May 28, 2026, ANTS evaluated a production error where the external n8n server (`123.245.85.70`) encountered a `Connection timed out` error when executing the Postgres node (`Claim Proposal Candidates`) connecting to the VPS public IP (`173.212.232.176:5432`).

* **Root Cause:** In accordance with [ADR 0002](file:///C:/Users/EQUIPO/appmultiANTS/ants-ai-gateway/docs/adr/0002-private-supabase-network-boundary.md), the database port `5432` is not published to the host in `/root/ants-infra/supabase-ants/docker-compose.yml` to prevent public Postgres exposure.
* **Problem:** Since the production n8n server runs on an external stack, it originally required direct SQL database access to fetch, prioritize, and log opportunity intake rows.

---

## Decision
ANTS has chosen to implement **Option B (ANTS AI Gateway secure endpoints)** as the definitive, production-ready solution, completely rejecting any direct host-level database port whitelisting (`iptables` / `DOCKER-USER` rules).

### The Chosen Architecture (Option B):
1. **Complete Database Isolation:**
   Postgres port `5432` remains strictly private and unexposed to the host inside `/root/ants-infra/supabase-ants/docker-compose.yml`. No public port mapping is allowed, in full compliance with ADR-0002.
2. **Secure HTTPS Endpoints:**
   FastAPI-based ANTS AI Gateway exposes two secure, specialized endpoints under `/n8n/*`:
   - `POST /n8n/claim-candidates`: Fetches unclaimed or failed opportunities from `noco_mvp_opportunity_workbench` and registers them in the intake ledger with state `queued`.
   - `POST /n8n/update-intake`: Updates the orchestration status of candidates (`queued`, `handoff_created`, `analysis_started`, `completed`, `failed`).
3. **Governance & API Key Auth:**
   Both endpoints require a secure HTTP header authentication token `X-ANTS-API-Key: (value of ANTS_GATEWAY_API_KEY)`. All external requests go through the Caddy reverse proxy HTTPS ingress (`https://gateway.fullants.com`).

### Discarded Alternatives:
* **Option C (DOCKER-USER iptables whitelisting):** Discarded. Although it whitelists only the n8n IP, it introduces firewall persistence risks (rules do not survive Docker restarts or server reboots by default) and violates the zero-exposure database core policy (ADR-0002).
* **Option A (Kong REST API):** Discarded. Exposing the generic Supabase REST API via Kong requires opening broader database access parameters and lacks custom transaction control (e.g. atomically claiming rows while shifting state to `queued`).

---

## Consequences

### Positive:
* **100% Secure database network isolation:** Port 5432 remains completely closed to the internet.
* **Unified Governance:** All n8n traffic is authenticated, monitored, and logged through the AI Gateway.
* **Atomic State Operations:** Complex data operations (like claiming workbench rows and queueing them in intake) are executed in a single, atomic database transaction inside the gateway backend instead of multiple roundtrips in n8n.
* **Reboot Resilience:** Requires zero host-level firewall maintenance.

### Trade-offs:
* **HTTP Overhead:** Minor HTTP request parsing overhead compared to raw TCP, which is negligible for periodic polling tasks.

---

## Linear Backlog Issue Seed

Copy and paste this specification to create the work item in Linear:

### `ANT-47` — Deploy secure n8n database endpoints on VPS (Option B)

* **Goal:** Enable the external n8n server to query and update proposal candidates securely via the AI Gateway, maintaining maximum database network hardening.
* **Context:** n8n requires candidate claims, but port 5432 is strictly isolated. Option B replaces direct DB connections with HTTPS REST endpoints.
* **Acceptance Criteria:**
  - AI Gateway is deployed on VPS with `/n8n/claim-candidates` and `/n8n/update-intake` routes active.
  - Endpoints require `X-ANTS-API-Key` header authentication.
  - n8n calls endpoints via HTTP Request nodes over Caddy HTTPS.
  - Database port 5432 remains closed to host and public interfaces.
* **Technical Constraints:** Complies fully with ADR-0002.
* **Test or Harness:**
  - `curl -X POST https://gateway.fullants.com/n8n/claim-candidates` without auth returns `403 Forbidden`.
  - Authorized n8n HTTP Request node successfully retrieves candidate rows.
  - `nmap -p 5432 173.212.232.176` from an external client reports `filtered` or `closed`.

---

## CodeRabbit Review Questions
When you open the pull request for this ADR, ask CodeRabbit to comment on:
1. Is the Pydantic input schema for `/n8n/update-intake` robust against SQL injection or unexpected string payloads?
2. Are the asyncpg database connections properly returned to the connection pool under heavy concurrent n8n polls?
