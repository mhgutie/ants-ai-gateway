from __future__ import annotations

import argparse
import fnmatch
import tarfile
from pathlib import Path


PROJECT_NAME = "ants-ai-gateway"

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}

EXCLUDED_FILES = {
    ".env",
    "executor_credentials.json",
}

EXCLUDED_PATTERNS = (
    "*.pyc",
    "*.pyo",
    "*.tar",
    "*.tar.gz",
    "*.tgz",
    "*.zip",
    "*.keep",
    "config/*.backup.yaml",
)


def find_project_root(start: Path) -> Path:
    current = start.resolve()
    if current.name == PROJECT_NAME and (current / "app").is_dir():
        return current

    candidate = current / PROJECT_NAME
    if candidate.is_dir() and (candidate / "app").is_dir():
        return candidate

    for parent in current.parents:
        if parent.name == PROJECT_NAME and (parent / "app").is_dir():
            return parent
        candidate = parent / PROJECT_NAME
        if candidate.is_dir() and (candidate / "app").is_dir():
            return candidate

    raise SystemExit(f"Could not find {PROJECT_NAME} project root from {start}")


def should_include(relative_path: Path) -> bool:
    parts = relative_path.parts
    name = relative_path.name
    normalized = relative_path.as_posix()

    if any(part in EXCLUDED_DIRS for part in parts):
        return False

    if name in EXCLUDED_FILES:
        return False

    if name.startswith(".env.") and name != ".env.example":
        return False

    for pattern in EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(normalized, pattern):
            return False

    return True


def package_project(project_root: Path, output: Path) -> None:
    output = output.resolve()
    project_root = project_root.resolve()

    with tarfile.open(output, "w:gz") as archive:
        for path in sorted(project_root.rglob("*")):
            relative_path = path.relative_to(project_root)
            if not should_include(relative_path):
                continue
            archive.add(path, arcname=Path(PROJECT_NAME) / relative_path, recursive=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a sanitized ANTS AI Gateway release package.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root or parent directory. Defaults to the current directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.cwd().parent / f"{PROJECT_NAME}.tar.gz",
        help="Output .tar.gz path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.project_root)
    package_project(project_root, args.output)
    print(f"Packaged {project_root} -> {args.output.resolve()}")


if __name__ == "__main__":
    main()
