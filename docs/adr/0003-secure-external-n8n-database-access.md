# ADR 0003: Secure External Database Ingress for n8n via Docker-User Filtering

## Status
Proposed — May 28, 2026

## Context
On May 28, 2026, ANTS evaluated a production error where the external n8n server (`123.245.85.70`) encountered a `Connection timed out` error when executing the Postgres node (`Claim Proposal Candidates`) connecting to the VPS public IP (`173.212.232.176:5432`).

* **Root Cause:** In accordance with [ADR 0002](file:///C:/Users/EQUIPO/appmultiANTS/ants-ai-gateway/docs/adr/0002-private-supabase-network-boundary.md), the database port `5432` is not published to the host in `/root/ants-infra/supabase-ants/docker-compose.yml` to prevent public Postgres exposure.
* **Problem:** Since the production n8n server runs on an external stack, it requires raw TCP access to Postgres to fetch, prioritize, and log opportunity intake rows.

### Core Security Challenge: Docker vs. UFW
By default, mapping a port in Docker (`-p 5432:5432`) instructs the Docker daemon to insert routing rules directly into the `PREROUTING` chain of `iptables`. These rules bypass standard UFW `INPUT` block rules, exposing the database port publicly to the entire internet even if UFW has a default deny rule.

---

## Decision
ANTS proposes to publish the database port in Docker, but block all public ingress using the special `DOCKER-USER` chain in `iptables`, whitelisting *only* the specific IP address of the external n8n server.

### The Target Security Architecture:
1. **Docker compose publishing:**
   Add `ports: - "5432:5432"` inside the `db` service definition in `/root/ants-infra/supabase-ants/docker-compose.yml`.
2. **Iptables DOCKER-USER rule:**
   Inject a rule at the top of the `DOCKER-USER` chain that drops all TCP traffic on port 5432 that does **not** originate from the n8n IP `123.245.85.70`:
   ```bash
   iptables -I DOCKER-USER -p tcp --dport 5432 ! -s 123.245.85.70 -j DROP
   ```

### Why this works:
* The `DOCKER-USER` chain is evaluated **before** Docker's internal routing and network virtualization rules.
* The rule uses `! -s 123.245.85.70` (negation), meaning "if the packet is NOT from this IP, drop it instantly".
* This keeps the database port 100% closed to hackers, port scanners, and unauthorized clients, while allowing seamless connection for the external n8n server.

---

## Consequences

### Positive:
* Resolves the n8n `Connection timed out` instantly.
* Prevents public Postgres exposure to the internet, maintaining the security intent of ADR 0002.
* Extremely lightweight control (no complex VPN or SSH tunnel orchestration required on the n8n side).

### Trade-offs:
* **IP Dependency:** If the n8n server IP changes, the firewall rule must be updated.
* **Firewall Persistence:** Direct `iptables` commands are active instantly but do not survive system reboots by default. A persistence system (like `iptables-persistent` or adding the rule to a startup script) must be documented and verified.

---

## Linear Backlog Issue Seed

Copy and paste this specification to create the work item in Linear:

### `ANT-47` — Secure external n8n database whitelist via DOCKER-USER

* **Goal:** Allow the external n8n server to connect securely to the Supabase database without exposing the port publicly to the internet.
* **Context:** n8n requires Postgres connection to claim opportunity candidates, but port 5432 is isolated.
* **Acceptance Criteria:**
  - `docker-compose.yml` publishes port `5432` for `supabase-db`.
  - An `iptables` rule in the `DOCKER-USER` chain restricts port 5432 access **strictly** to the n8n IP `123.245.85.70`.
  - Connection tests from n8n are successful.
  - Connection tests from other external IPs (using a port scan or separate curl) are dropped.
  - The firewall persistence mechanism is documented.
* **Technical Constraints:** Do not let Docker bypass UFW rules. Use only the `DOCKER-USER` chain.
* **Test or Harness:**
  - n8n node execution succeeds.
  - `nmap -p 5432 173.212.232.176` from an external client reports `filtered` or `closed` (packets dropped).
* **Definition of Done:**
  - ADR 0003 is merged.
  - Reglas applied and verified on VPS.
  - Handoff logs successfully ingested.

---

## CodeRabbit Review Questions
When you open the pull request for this ADR, ask CodeRabbit to comment on:
1. Is the `DOCKER-USER` rule robust enough for multi-interface Docker bridges?
2. What is the recommended best practice for `iptables-persistent` on Ubuntu 22.04 LTS to ensure this survives reboots?
