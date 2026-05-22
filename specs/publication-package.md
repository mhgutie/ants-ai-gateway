# Publication Package Harness

## Problem

ANTS AI Gateway is currently developed inside a larger local workspace. Packaging or publishing from the wrong directory can accidentally include local environment files, generated archives, caches, or private operational context.

## Expected Result

Provide a repeatable package command that exports only the public gateway project files needed for deployment or repository publication.

## Technical Specification

- Package the `ants-ai-gateway` directory as a tarball with the top-level folder preserved.
- Exclude `.env`, `.env.*`, virtual environments, Python caches, pytest caches, generated archives, backup YAML files, local credential files, and VCS metadata.
- Keep `.env.example` in the package.
- Make the exclusion logic testable without creating a full package.
- Keep the script safe to run from either the project root or its parent directory.

## Acceptance Criteria

- `.env` and `.env.local` are excluded.
- `.env.example` is included.
- Generated `.tar.gz` files are excluded.
- `config/*.backup.yaml` files are excluded.
- Source, docs, specs, tests, Docker, and GitHub workflow files are included.

## Harness

```bash
pytest
python scripts/package_release.py --output ../ants-ai-gateway.tar.gz
```
