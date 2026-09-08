#!/usr/bin/env python3
"""Scan the repo for script headers and regenerate docs/inventory.json.

Header format is documented in docs/SCRIPT_HEADERS.md. Run from anywhere;
paths are resolved relative to the repo root (this file's parent's parent).
"""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "docs" / "inventory.json"

SCRIPT_EXTS = {".sh", ".py"}
EXCLUDE_DIRS = {".git", "docs", "node_modules", ".venv", "venv"}

HEADER_RE = re.compile(
    r"^#\s*---\s*$\n(?P<body>(?:^#.*$\n?)*?)^#\s*---\s*$",
    re.MULTILINE,
)
FIELD_RE = re.compile(r"^#\s*(purpose|usage|tags|note)\s*:\s*(.*)$")


def parse_header(text: str):
    match = HEADER_RE.search(text)
    if not match:
        return None
    fields = {}
    for line in match.group("body").splitlines():
        fm = FIELD_RE.match(line)
        if fm:
            key, val = fm.group(1), fm.group(2).strip()
            fields[key] = val
    if "purpose" not in fields:
        return None
    fields["tags"] = [t.strip() for t in fields.get("tags", "").split(",") if t.strip()]
    return fields


def iter_scripts():
    for path in sorted(REPO_ROOT.rglob("*")):
        if path.suffix not in SCRIPT_EXTS:
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        yield path


def main():
    categories = {}
    missing = []

    for path in iter_scripts():
        rel = path.relative_to(REPO_ROOT)
        category = rel.parts[0]
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        fields = parse_header(text)
        if fields is None:
            missing.append(str(rel))
            continue
        categories.setdefault(category, []).append({
            "name": path.name,
            "path": str(rel),
            "purpose": fields.get("purpose", ""),
            "usage": fields.get("usage", ""),
            "tags": fields.get("tags", []),
            "note": fields.get("note", ""),
        })

    result = {
        "generated_from": "script headers, see docs/SCRIPT_HEADERS.md",
        "categories": [
            {"category": cat, "scripts": sorted(scripts, key=lambda s: s["name"])}
            for cat, scripts in sorted(categories.items())
        ],
    }

    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")

    total = sum(len(c["scripts"]) for c in result["categories"])
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}: {total} scripts across {len(result['categories'])} categories.")
    if missing:
        print(f"\n{len(missing)} script(s) missing a header block (skipped):")
        for m in missing:
            print(f"  - {m}")


if __name__ == "__main__":
    main()
