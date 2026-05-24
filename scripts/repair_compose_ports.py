#!/usr/bin/env python3
"""
Remove public 5432/6543 port publications from docker-compose.yml.

Usage:
  python3 repair_compose_ports.py --file /path/to/docker-compose.yml [--dry-run]

What it does:
  1. Removes 5432 and 6543 port mappings, including ${VAR}:5432 style lines.
  2. Removes now-empty 'ports:' blocks.
  3. Collapses accidental duplicate 'ports:' keys.
  4. Validates the result is parseable YAML.
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)


PORT_MAPPING_RE = re.compile(
    r"""^\s*-\s+["']?"""
    r"""(?P<mapping>(?:[\d.]+:)?(?:\$\{[^}]+\}|\d+):(?:\$\{[^}]+\}|\d+)(?:/\w+)?)"""
    r"""["']?\s*$"""
)
HARDEN_PORTS = {"5432", "6543"}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--file", default="docker-compose.yml")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def _is_hardened_port_mapping(line: str) -> bool:
    match = PORT_MAPPING_RE.match(line)
    if not match:
        return False
    mapping = match.group("mapping")
    parts = mapping.split(":")
    host_port = parts[-2] if len(parts) >= 2 else ""
    container_port = parts[-1].split("/")[0]
    return host_port in HARDEN_PORTS or container_port in HARDEN_PORTS


def _collapse_duplicate_ports_keys(lines: list[str]) -> tuple[list[str], int]:
    result = []
    previous_nonempty_ports_indent: int | None = None
    collapsed = 0
    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if stripped == "ports:":
            if previous_nonempty_ports_indent == indent:
                collapsed += 1
                continue
            previous_nonempty_ports_indent = indent
            result.append(line)
            continue

        if stripped and not stripped.startswith("-"):
            previous_nonempty_ports_indent = None
        result.append(line)
    return result, collapsed


def _remove_empty_ports_blocks(lines: list[str]) -> tuple[list[str], int]:
    result = []
    removed = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "ports:":
            indent = len(line) - len(line.lstrip())
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j >= len(lines):
                removed += 1
                i += 1
                continue
            next_indent = len(lines[j]) - len(lines[j].lstrip())
            if not lines[j].lstrip().startswith("-") or next_indent <= indent:
                removed += 1
                i += 1
                continue
        result.append(line)
        i += 1
    return result, removed


def main():
    args = parse_args()
    path = Path(args.file)

    if not path.exists():
        print(f"ERROR: {path} not found")
        sys.exit(1)

    lines = path.read_text().splitlines(keepends=True)
    print(f"Read {len(lines)} lines from {path}")

    # Pass 1: remove 5432/6543 port mapping lines.
    removed_ports = []
    after_p1 = []
    for i, line in enumerate(lines, 1):
        if _is_hardened_port_mapping(line):
            removed_ports.append((i, line.rstrip()))
            continue
        after_p1.append(line)

    print(f"Pass 1: removed {len(removed_ports)} port-mapping lines:")
    for lineno, content in removed_ports:
        print(f"  line {lineno}: {content}")

    after_p2, collapsed = _collapse_duplicate_ports_keys(after_p1)
    print(f"Pass 2: collapsed {collapsed} duplicate 'ports:' keys")

    after_p3, removed_empty = _remove_empty_ports_blocks(after_p2)
    print(f"Pass 3: removed {removed_empty} empty 'ports:' blocks")

    result = "".join(after_p3)

    # Validate YAML
    try:
        yaml.safe_load(result)
        print("YAML validation: OK")
    except yaml.YAMLError as e:
        print(f"YAML validation FAILED: {e}")
        print("The file has NOT been written. Inspect the original and repair manually.")
        sys.exit(1)

    if args.dry_run:
        print("Dry run — no changes written.")
        return

    # Backup
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    backup = path.with_suffix(f".yml.bak-{ts}")
    shutil.copy2(path, backup)
    print(f"Backup saved: {backup}")

    # Write
    path.write_text(result)
    print(f"Written: {path}")
    print("Done. Run 'docker compose config --quiet && echo YAML_OK' to confirm.")


if __name__ == "__main__":
    main()
