# Public Repository Publication Checklist

## Repository Scope

Publish only the `ants-ai-gateway` directory as its own repository.

Do not publish the parent `appmultiANTS` directory yet because it contains local `.env` files, operational artifacts, prior attempts, and private deployment context.

## Pre-Publication Checklist

- [ ] Create a fresh Git repository from `ants-ai-gateway`.
- [ ] Confirm `.env` and `.env.*` are ignored.
- [ ] Confirm no real provider keys or OAuth tokens are present.
- [ ] Confirm `executor_credentials.json` is not present.
- [ ] Confirm generated archives such as `*.tar.gz` are not present.
- [ ] Confirm backup YAML files are not present.
- [ ] Run `pytest`.
- [ ] Build a sanitized package with `python scripts/package_release.py --output ../ants-ai-gateway.tar.gz`.
- [ ] Confirm GitHub secret scanning or the included Gitleaks workflow is active.
- [ ] Confirm `.coderabbit.yaml` is present in the isolated repository root.
- [ ] Create the GitHub repository.
- [ ] Install CodeRabbit on the public repository.
- [ ] Create initial Linear issue `ANTS-001 Gateway baseline`.
- [ ] Open the baseline PR with validation evidence.

## Current Publication Status

- [x] Public repository created at `mhgutie/ants-ai-gateway`.
- [x] Baseline `main` branch pushed from isolated publication repository.
- [x] Publication notes added in `docs/publication-notes.md`.
- [ ] CodeRabbit enabled for the repository.
- [ ] First PR reviewed by CodeRabbit.

## Suggested Baseline Commands

Use these commands from a clean location, not from `C:\Users\EQUIPO`:

```bash
python scripts/package_release.py --output ../ants-ai-gateway.tar.gz
git init
git add .
git commit -m "ANTS-001 Add AI gateway baseline"
git branch -M main
git remote add origin <github-repo-url>
git push -u origin main
```

For feature work after baseline:

```bash
git checkout -b feat/ants-005-executor-smoke
pytest
git add .
git commit -m "ANTS-005 Add executor smoke harness"
git push -u origin feat/ants-005-executor-smoke
```

## Safety Notes

The current machine appears to have a Git repository rooted at the user home directory. Avoid committing from that root. Publish `ants-ai-gateway` as an isolated repository to prevent accidentally tracking personal files.
