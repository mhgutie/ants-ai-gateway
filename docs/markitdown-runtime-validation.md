# MarkItDown runtime validation

Date: 2026-05-28
Runtime: Dockerized ANTS AI Gateway
Service: `ants-ai-gateway`

## Purpose

Install and validate Microsoft MarkItDown inside the ANTS AI Gateway Docker runtime so future ingestion endpoints can convert documents into Markdown for n8n, RAG, and proposal-generation workflows.

## Installation approach

Direct host-level installation failed with an externally managed Python environment error. This is expected on modern Debian and Ubuntu Python environments governed by PEP 668.

Because ANTS AI Gateway runs in Docker, MarkItDown must be installed in the gateway image through `requirements.txt`, not in the host Python environment.

## Dependency added

```text
markitdown[all]==0.1.6
```

## Build and run commands

```bash
cd /root/ants-apps/ants-ai-gateway
docker compose build --no-cache
docker compose up -d
```

## Validation results

### Health check

```bash
curl http://localhost:8010/health
```

Observed:

```json
{"status":"ok","service":"ants-ai-gateway","env":"local"}
```

### Import check

```bash
docker compose exec ants-ai-gateway python -c "from markitdown import MarkItDown; print('MarkItDown OK')"
```

Observed:

```text
MarkItDown OK
```

### Conversion check

```bash
docker compose exec -T ants-ai-gateway python - <<'PY'
from markitdown import MarkItDown

test_file = "/tmp/test.md"

with open(test_file, "w", encoding="utf-8") as f:
    f.write("# Prueba ANTS MarkItDown\n\nEste es un archivo de prueba.")

md = MarkItDown()
result = md.convert(test_file)

print(result.text_content)
PY
```

Observed:

```markdown
# Prueba ANTS MarkItDown

Este es un archivo de prueba.
```

### Real file conversion check

A repository README file copied into the running container was converted successfully. The output started with:

```markdown
# ANTS AI Gateway v0.1

ANTS AI Gateway is the first production module of ANTS...
```

## Non-blocking warning

The runtime emitted a warning about missing `ffmpeg` or `avconv`. This is not blocking for document conversion. It may matter later only if audio or video conversion is required.

## Clarification about `/app/README.md`

The path `/app/README.md` failed because the Docker image currently copies only the application package, config directory, and requirements file. The README is not present inside the container. This was a test-path issue, not a MarkItDown issue.

## Current status

- Gateway health: OK
- Dockerized dependency installation: OK
- MarkItDown import: OK
- Temporary Markdown conversion: OK
- Real file conversion after copying into the container: OK
- Non-blocking ffmpeg warning: accepted for document-only use

## Suggested next step

Add a FastAPI endpoint such as:

```text
POST /tools/markitdown/convert
```

Expected behavior:

1. Accept uploaded files from n8n or internal agents.
2. Store the upload in a temporary file.
3. Convert it with MarkItDown.
4. Return Markdown text and metadata.
5. Apply file size, MIME type, timeout, and error-handling safeguards.

## Acceptance criteria for the next implementation PR

- Endpoint accepts at least PDF, DOCX, PPTX, XLSX, XLS, TXT, and MD.
- Endpoint returns structured JSON with `text_content`, `source_filename`, `content_type`, and `success`.
- Temporary files are deleted after conversion.
- Errors are returned as safe JSON responses.
- Tests cover success and failure paths.
- README or docs explain how n8n should call the endpoint.
