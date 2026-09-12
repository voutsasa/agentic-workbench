"""
Checks every relative Markdown link in this repository, including the ones into confluence-sync.

For a repository that is mostly prose, nothing else notices a link going stale: no test imports it
and no build resolves it. Renamed headings and moved documents are the two common causes.

    uv run python tools/check_links.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".venv", ".git", "engine", "node_modules", ".pytest_cache", "export", "api"}

# Directories whose links point somewhere this repository cannot see — vendored templates,
# third-party prose, documents belonging to another repo. Name them here WITH THE REASON: an
# exemption with a reason is a decision, one without is a hole. A gate that always fails is no gate.
EXEMPT: tuple[str, ...] = ()
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)


def slug(heading: str) -> str:
    """GitHub's anchor rule, near enough: lowercase, punctuation dropped, spaces hyphenated."""

    text = re.sub(r"`|\*+|\[|\]|\(.*?\)", "", heading.strip().lower())
    return re.sub(r"\s+", "-", re.sub(r"[^\w\s-]", "", text).strip())


def documents(root: Path, *, checkable: bool = False) -> list[Path]:
    """Every Markdown file; `checkable` also drops the ones exempted above."""

    found = [p for p in root.rglob("*.md") if not SKIP & set(p.parts)]
    if checkable:
        found = [p for p in found if not any(part in EXEMPT for part in p.parts)]
    return found


def main() -> int:
    anchors: dict[Path, set[str]] = {}
    # Add sibling repositories here if this project's prose links into them.
    for root in (ROOT,):
        if root.is_dir():
            for document in documents(root):
                anchors[document.resolve()] = {slug(h) for h in HEADING.findall(document.read_text(encoding="utf-8"))}

    broken: list[str] = []
    checked = documents(ROOT, checkable=True)
    for document in checked:
        text = document.read_text(encoding="utf-8")
        for match in LINK.finditer(text):
            link = match.group(1)
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            path, _, fragment = link.partition("#")
            target = (document.parent / path).resolve() if path else document.resolve()
            line = text[: match.start()].count("\n") + 1
            where = f"{document.relative_to(ROOT)}:{line}"
            if not target.exists():
                broken.append(f"{where}  {link}  -> no such file")
            elif fragment and target in anchors and fragment not in anchors[target]:
                broken.append(f"{where}  {link}  -> no such heading")

    for problem in broken:
        print(problem, file=sys.stderr)
    skipped = len(documents(ROOT)) - len(checked)
    print(f"{len(checked)} documents checked ({skipped} exempt), {len(broken)} broken links")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
