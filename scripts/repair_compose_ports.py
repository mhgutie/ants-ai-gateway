#!/usr/bin/env python3
"""
Repair docker-compose.yml after sed removed ports: keys,
then remove 5432/6543 port publications (ANT-12 hardening).

Usage:
  python3 repair_compose_ports.py --file /path/to/docker-compose.yml [--dry-run]

What it does:
  1. Restores missing 'ports:' keys before orphaned port-mapping list items.
  2. Removes 5432 and 6543 port mappings (hardening goal).
  3. Removes now-empty 'ports:' blocks.
  4. Validates the result is parseable YAML.
"""

import re
import sys
import shutil
import argparse
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)


PORT_MAPPING_RE = re.compile(r'^-\s+["\']?[\d.]*:?(\d+):\d+["\']?\s*$')
HARDEN_PORTS = {5432, 6543}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--file", default="docker-compose.yml")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    path = Path(args.file)

    if not path.exists():
        print(f"ERROR: {path} not found")
        sys.exit(1)

    lines = path.read_text().splitlines(keepends=True)
    print(f"Read {len(lines)} lines from {path}")

    # Pass 1: remove 5432/6543 port mapping lines
    removed_ports = []
    after_p1 = []
    for i, line in enumerate(lines):
        m = PORT_MAPPING_RE.match(line.strip())
        if m:
            port = int(m.group(1))
            if port in HARDEN_PORTS:
                removed_ports.append((i + 1, line.rstrip()))
                continue
        after_p1.append(line)

    print(f"Pass 1: removed {len(removed_ports)} port-mapping lines:")
    for lineno, content in removed_ports:
        print(f"  line {lineno}: {content}")

    # Pass 2: restore missing 'ports:' key before orphaned port-mapping items
    after_p2 = []
    restored = 0
    i = 0
    while i < len(after_p1):
        line = after_p1[i]
        stripped = line.strip()
        if PORT_MAPPING_RE.match(stripped):
            # Check if previous non-empty line already has 'ports:'
            j = len(after_p2) - 1
            while j >= 0 and after_p2[j].strip() == "":
                j -= 1
            if j < 0 or after_p2[j].strip() != "ports:":
                list_indent = len(line) - len(line.lstrip())
                # ports: sits 2 spaces left of its list items in Docker Compose YAML
                ports_indent = max(0, list_indent - 2)
                after_p2.append(" " * ports_indent + "ports:\n")
                print(f"  Restored 'ports:' key (indent={ports_indent}) before line {i+1}")
                restored += 1
        after_p2.append(line)
        i += 1
    print(f"Pass 2: restored {restored} 'ports:' keys")

    # Pass 3: remove empty 'ports:' blocks (ports: followed by no list items)
    after_p3 = []
    removed_empty = 0
    i = 0
    while i < len(after_p2):
        line = after_p2[i]
        if line.strip() == "ports:":
            # Look ahead for the next non-empty line
            j = i + 1
            while j < len(after_p2) and after_p2[j].strip() == "":
                j += 1
            if j >= len(after_p2) or not after_p2[j].strip().startswith("-"):
                removed_empty += 1
                i += 1
                continue
        after_p3.append(line)
        i += 1
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
