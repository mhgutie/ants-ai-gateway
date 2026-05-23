# AI Credits and Open Source Funding Opportunities

## Purpose

ANTS should use public, useful open source projects to create community value, attract review, and qualify for legitimate AI credit programs. Credits are a support mechanism, not the reason for the projects.

## Candidate Projects

| Project | Public/Private | Why it fits |
|---|---|---|
| `ants-ai-gateway` | Public | Reusable routing, cost control, provider policy, and executor harness infrastructure. |
| `dr-server` | Public core, private pro | Practical VPS maintenance, diagnostics, reports, and safe remediation guidance. |
| `careerlab-lite` | Public | Useful CV/LinkedIn improvement app with privacy-first defaults. |
| `careerlab-pro` | Private | Paid product with user data, tracking, premium prompts, and advanced workflows. |
| ANTS deployment/ops | Private | Credentials, VPS configuration, customer data, and operational automation. |

## Opportunity Tracker

| Provider | Program | Potential benefit | Candidate project | Status | Link |
|---|---|---:|---|---|---|
| OpenAI | Codex Open Source Fund | Up to USD 25,000 API credits | `ants-ai-gateway`, `dr-server` | Researching | https://openai.com/form/codex-open-source-fund/ |
| OpenAI | Grants | Program-dependent credits or funding | ANTS research, OSS tooling | Researching | https://grants.openai.com/ |
| OpenAI | Researcher Access Program | Up to USD 1,000 API credits | Evaluation/harness research | Optional | https://grants.openai.com/prog/openai_researcher_access_program/ |
| Anthropic | Startup Program | API credits, priority limits, resources | CareerLab Pro, ANTS | Researching | https://www.anthropic.com/startup-program-official-terms |
| Google | Google for Startups Gemini / Cloud | Cloud credits for Gemini/Vertex usage | CareerLab, Dr. Server Pro | Researching | https://startup.google.com/gemini/ |
| CodeRabbit | Public repository reviews | Free automated PR review on public repos | All public repos | Ready | https://www.coderabbit.ai/pricing |

## Application Readiness Checklist

- Public repository exists.
- README explains the problem and impact.
- License selected.
- `.env.example` is safe.
- Tests pass.
- Specs and ADRs are present.
- Issues and roadmap are public.
- Demo or screenshots exist when useful.
- No secrets, personal data, or customer data are committed.
- Clear plan for how credits will be used.

## Credit Usage Principles

- Use credits for public-good development, demos, tests, and evaluation harnesses.
- Keep cost logs in `model_usage`.
- Prefer cheaper models for bulk work.
- Reserve premium models for validation, architecture, and high-risk deliverables.
- Do not build a product that only works while credits last.

## Notes

Public projects should be useful even without credits. Private commercial modules should remain separate when they contain sensitive data, premium workflows, customer-specific logic, or operational credentials.
