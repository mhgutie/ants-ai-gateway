# DeepSeek Direct Provider

## Problem

ANTS has a DeepSeek API key available, but `deepseek` direct provider execution is currently a stub. Routing DeepSeek traffic through OpenRouter prevents ANTS from using direct provider credentials, pricing, and account controls.

## Expected Result

Enable direct DeepSeek execution through the OpenAI-compatible chat completions API.

## Technical Specification

- Implement `DeepSeekClient` using the existing OpenAI-compatible provider mixin.
- Default base URL to `https://api.deepseek.com`.
- Support `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and profile keys such as `DEEPSEEK__1__API_KEY`.
- Use direct model IDs `deepseek-v4-flash` and `deepseek-v4-pro`.
- Keep OpenRouter as a possible fallback through explicit provider override.
- Do not expose API keys in responses, logs, or raw payloads.

## Acceptance Criteria

- `provider: "deepseek"` can execute `deepseek-v4-flash`.
- Missing key returns a controlled provider failure through `/chat`.
- Unit tests cover direct provider success and missing-key behavior.
- `/models` reflects direct DeepSeek as the executable provider for DeepSeek aliases.

## Harness

```bash
pytest
```
