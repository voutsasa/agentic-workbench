"""Report relative links in Markdown files that do not resolve.

Checks every inline link, image and reference definition whose target is a
relative path: the file or folder must exist, and a ``#fragment`` into a
Markdown file must match one of its headings (GitHub slug rules, with ``-1``,
``-2`` for repeats) or an HTML ``id``/``name``. Links inside fenced or inline
code are ignored. External URLs (any ``scheme:`` or ``//host``) are not fetched.

Standard library only. Exit 0 when nothing is broken, 1 otherwise, 2 on bad
arguments.

    check_links.py README.md docs/          # files, or folders searched for *.md
    check_links.py --json README.md         # one JSON object per broken link
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote

MARKDOWN = {".md", ".markdown"}
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__"}

FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
INLINE_CODE = re.compile(r"(`+)(?:(?!\1).)+?\1")
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(\s*(<[^>]+>|[^)\s]+)(?:\s+[\"'(][^)]*)?\s*\)")
REFERENCE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
HTML_ID = re.compile(r"""\b(?:id|name)\s*=\s*["']([^"']+)["']""")
SCHEME = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)")
MD_LINK_TEXT = re.compile(r"\[([^\]]*)\]\([^)]*\)")


@dataclass(frozen=True)
class Broken:
    """One link that does not resolve."""

    path: Path
    line: int
    target: str
    reason: str


def prose_lines(text: str) -> list[tuple[int, str]]:
    """Return (line number, text) for each line outside fenced code, inline code blanked."""
    lines: list[tuple[int, str]] = []
    fence: str | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        opened = FENCE.match(line)
        if fence is not None:
            if (
                opened
                and opened.group(1)[0] == fence[0]
                and len(opened.group(1)) >= len(fence)
            ):
                fence = None
            continue
        if opened:
            fence = opened.group(1)
            continue
        lines.append((number, INLINE_CODE.sub(lambda m: " " * len(m.group(0)), line)))
    return lines


def slug(heading: str) -> str:
    """GitHub's anchor for a heading: lower case, punctuation dropped, spaces to hyphens."""
    text = MD_LINK_TEXT.sub(r"\1", heading).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(text: str) -> set[str]:
    """Every fragment a link into this Markdown text may name."""
    found: set[str] = set()
    seen: dict[str, int] = {}
    fence: str | None = None
    for line in text.splitlines():
        opened = FENCE.match(line)
        if fence is not None:
            if (
                opened
                and opened.group(1)[0] == fence[0]
                and len(opened.group(1)) >= len(fence)
            ):
                fence = None
            continue
        if opened:
            fence = opened.group(1)
            continue
        found.update(HTML_ID.findall(line))
        heading = HEADING.match(line)
        if heading:
            base = slug(heading.group(1))
            count = seen.get(base, 0)
            seen[base] = count + 1
            found.add(base if count == 0 else f"{base}-{count}")
    return found


def links(text: str) -> list[tuple[int, str]]:
    """Return (line number, target) for every link and reference definition outside code."""
    found: list[tuple[int, str]] = []
    for number, line in prose_lines(text):
        targets = [m.group(1) for m in INLINE_LINK.finditer(line)]
        reference = REFERENCE.match(line)
        if reference:
            targets.append(reference.group(1))
        found.extend((number, target.strip("<>")) for target in targets)
    return found


def check_file(path: Path, cache: dict[Path, set[str]] | None = None) -> list[Broken]:
    """Return every relative link in one Markdown file that does not resolve."""
    cache = {} if cache is None else cache
    text = path.read_text(encoding="utf-8")
    broken: list[Broken] = []
    for line, target in links(text):
        if SCHEME.match(target):
            continue
        file_part, _, fragment = target.partition("#")
        dest = (
            (path.parent / unquote(file_part)).resolve()
            if file_part
            else path.resolve()
        )
        if not dest.exists():
            broken.append(Broken(path, line, target, "missing file"))
            continue
        if not fragment or dest.suffix.lower() not in MARKDOWN or not dest.is_file():
            continue
        if dest not in cache:
            cache[dest] = {a.lower() for a in anchors(dest.read_text(encoding="utf-8"))}
        if unquote(fragment).lower() not in cache[dest]:
            broken.append(Broken(path, line, target, "missing anchor"))
    return broken


def markdown_files(args: list[str]) -> list[Path]:
    """Expand each argument: a file as given, a folder to its *.md files, sorted."""
    files: list[Path] = []
    for arg in args:
        path = Path(arg)
        if path.is_dir():
            files.extend(
                p
                for p in sorted(path.rglob("*"))
                if p.suffix.lower() in MARKDOWN
                and p.is_file()
                and not SKIP_DIRS & set(p.parts)
            )
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(arg)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report relative Markdown links that do not resolve."
    )
    parser.add_argument(
        "paths", nargs="+", help="Markdown files, or folders searched for *.md"
    )
    parser.add_argument(
        "--json", action="store_true", help="print the broken links as JSON"
    )
    args = parser.parse_args(argv)
    try:
        files = markdown_files(args.paths)
    except FileNotFoundError as missing:
        print(f"no such file or folder: {missing}", file=sys.stderr)
        return 2
    cache: dict[Path, set[str]] = {}
    broken = [b for f in files for b in check_file(f, cache)]
    if args.json:
        print(json.dumps([asdict(b) | {"path": str(b.path)} for b in broken], indent=2))
    else:
        for b in broken:
            print(f"{b.path}:{b.line}: {b.reason}: {b.target}")
        noun = "file" if len(files) == 1 else "files"
        print(f"{len(broken)} broken links in {len(files)} {noun}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
