"""Set the `version:` frontmatter field across every skill, guide, machine
note, key document and the agent harness to match a release's new version.

Read-only by default — reports what would change. Pass --apply to write.
`workstation/scripts/tests/test_frontmatter_version.py` imports the same
file list, so the two cannot drift apart.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

GLOBS = [
    "workstation/cli/*/install.md",
    "workstation/cli/*/quick_start.md",
    "workstation/machines/*-*.md",
    "workstation/mcp/*/setup.md",
    "workstation/agent/skills/*/SKILL.md",
    "skills/*/SKILL.md",
]
EXPLICIT = [
    "docs/guidance/DEVELOPMENT-PLAN.md",
    "SOURCES.md",
    "SOURCE_CATALOGUE.md",
    "TODO.md",
    "AGENTS.md",
    "workstation/agent/AGENT-INSTRUCTIONS.md",
]

VERSION_LINE = re.compile(r"^version:\s*(.+?)\s*$", re.MULTILINE)


def versioned_files(repo: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in GLOBS:
        files.extend(sorted(repo.glob(pattern)))
    files.extend(repo / rel for rel in EXPLICIT)
    return files


def frontmatter_version(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    match = VERSION_LINE.search(text[4:end])
    return match.group(1) if match else None


def set_version(path: Path, new_version: str) -> str:
    """Rewrite the `version:` line in place. Returns a one-word status."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return "no-frontmatter"
    end = text.find("\n---", 4)
    if end == -1:
        return "no-frontmatter"
    header = text[4:end]
    match = VERSION_LINE.search(header)
    if match is None:
        return "no-version-field"
    if match.group(1) == new_version:
        return "already-set"
    new_header = VERSION_LINE.sub(f"version: {new_version}", header, count=1)
    path.write_text(text[:4] + new_header + text[end:], encoding="utf-8")
    return "updated"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("new_version", help="e.g. 0.2.0 (no leading v)")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repo root (default: inferred from this file)",
    )
    parser.add_argument(
        "--apply", action="store_true", help="write the changes (default: report only)"
    )
    args = parser.parse_args(argv)

    for path in versioned_files(args.repo):
        rel = path.relative_to(args.repo).as_posix()
        if args.apply:
            print(f"{set_version(path, args.new_version)}\t{rel}")
            continue
        current = frontmatter_version(path)
        status = (
            "already-set"
            if current == args.new_version
            else f"would-change ({current})"
        )
        print(f"{status}\t{rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
