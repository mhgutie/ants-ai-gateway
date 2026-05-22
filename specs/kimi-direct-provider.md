# Kimi Direct Provider

## Problem

ANTS has a Kimi/Moonshot API key available, but `kimi` direct provider execution is currently a stub. Product-builder routes should be able to use Kimi directly instead of depending on an unrelated provider path.

## Expected Result

Enable direct Kimi execution through Moonshot's OpenAI-compatible chat completions API.

## Technical Specification

- Implement `KimiClient` using the existing OpenAI-compatible provider mixin.
- Default base URL to `https://api.moonshot.ai/v1`.
- Support `KIMI_API_KEY`, `KIMI_BASE_URL`, and profile keys such as `KIMI__1__API_KEY`.
- Use model ID `kimi-k2.6` for `kimi-k2.6`.
- Do not expose API keys in responses, logs, or raw payloads.

## Acceptance Criteria

- `provider: "kimi"` can execute `kimi-k2.6`.
- Missing key returns a controlled provider failure through `/chat`.
- Unit tests cover direct provider success and missing-key behavior.
- `/models` reflects Kimi as executable once the adapter exists.
- `kimi-k2.6` is marked `execution_enabled: true`.

## Harness

```bash
pytest
```
