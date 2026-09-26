#!/usr/bin/env python3
"""Turn a publisher's own served markdown into plain GitHub-flavoured markdown.

Several documentation platforms serve each page's markdown source next to the
rendered page — Mintlify (`code.claude.com`, `platform.claude.com`,
`modelcontextprotocol.io`) and GitHub Docs both answer `<url>.md` with
`content-type: text/markdown`. That text is the source rather than a conversion
of it, so it beats the HTML route: no extractor selector to choose, no pandoc
writer to lose a table to, and no model anywhere near it.

What it is not is publishable markdown. It carries the platform's own component
tags (`<Note>`, `<Tab title="…">`, `<div class="ghd-tool vscode">`), anchor-only
tags, raw `<ul><li>` inside table cells — GFM cannot hold block content in a
cell, so the publisher falls back to HTML there — and site-relative link
targets that point at nothing once the file is local. This strips all of that,
**outside fenced code blocks only**: a `<Note>` or a `</li>` inside an example
is that example's content, and mangling it is the one failure this script must
not have.

Usage: python clean_publisher_md.py <served.md> <dest.md> <base-url>

`<base-url>` is the site root that site-relative targets resolve against, e.g.
`https://docs.github.com`. Frontmatter is not this script's job — run
`add_frontmatter.py` over the result, as the other routes do.

Standard library only: this runs on a fresh clone before any venv exists.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Mintlify's callout components. The tag becomes a bold label so the callout
# still reads as one in a plain viewer; the closing tag goes.
CALLOUTS = ("Note", "Warning", "Tip", "Info", "Check", "Danger")

# Layout-only components: they group their children and say nothing themselves.
DROP_WRAPPERS = ("Tabs", "Steps", "Frame", "CodeGroup", "Columns", "AccordionGroup")

# Components whose `title` is the only content they carry.
TITLED = ("Tab", "Step", "Card", "Accordion")

CALLOUT_OPEN = re.compile(rf"<({'|'.join(CALLOUTS)})(\s[^>]*)?>")
CALLOUT_CLOSE = re.compile(rf"</({'|'.join(CALLOUTS)})>")
WRAPPER = re.compile(rf"</?({'|'.join(DROP_WRAPPERS)})(\s[^>]*)?>")
TITLED_OPEN = re.compile(rf"<({'|'.join(TITLED)})\s[^>]*title=\"([^\"]*)\"[^>]*>")
TITLED_CLOSE = re.compile(rf"</({'|'.join(TITLED)})>")

IMG = re.compile(r"<img\s[^>]*?src=\"([^\"]+)\"[^>]*?/?>")
IMG_ALT = re.compile(r"alt=\"([^\"]*)\"")
ANCHOR_ONLY = re.compile(r"<(a|span)\s+id=\"[^\"]*\"\s*/>")
DIV = re.compile(r"</?div(\s[^>]*)?>")
SPAN = re.compile(r"<span(\s[^>]*)?>(.*?)</span>")
KBD = re.compile(r"<kbd>(.*?)</kbd>")
RELATIVE_LINK = re.compile(r"\]\((/[^)\s]*)\)")
FENCE = re.compile(r"^\s*(```|~~~)")
BLANK_RUN = re.compile(r"\n{3,}")


def strip_preamble(text: str) -> str:
    """Drop a blockquote preamble above the H1 — Mintlify injects one.

    Every line skipped has to be blank or a blockquote, so a page that simply
    opens with prose is returned untouched rather than beheaded.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            skipped = lines[:index]
            if all(not s.strip() or s.lstrip().startswith(">") for s in skipped):
                return "\n".join(lines[index:])
            return text
    return text


def flatten_cell_list(line: str) -> str:
    """`<ul><li>a</li><li>b</li></ul>` in a table cell -> `a; b`.

    GFM has no way to put a list inside a cell, which is why the publisher
    emitted raw HTML there. Joining with `; ` keeps every item's text at the
    cost of the bullets.
    """
    line = line.replace("</li><li>", "; ")
    for tag in ("<ul>", "</ul>", "<li>", "</li>"):
        line = line.replace(tag, "")
    return line


def transform_line(line: str, base: str) -> str:
    """Rewrite one line that is not inside a fenced code block."""
    image = IMG.search(line)
    if image and line.strip().startswith("<img"):
        alt = IMG_ALT.search(line)
        return f"![{alt.group(1) if alt else ''}]({image.group(1)})"

    line = CALLOUT_OPEN.sub(lambda m: f"**{m.group(1)}**", line)
    line = CALLOUT_CLOSE.sub("", line)
    line = TITLED_OPEN.sub(lambda m: f"**{m.group(2)}**", line)
    line = TITLED_CLOSE.sub("", line)
    line = WRAPPER.sub("", line)

    line = ANCHOR_ONLY.sub("", line)
    line = DIV.sub("", line)
    line = SPAN.sub(r"\2", line)
    line = KBD.sub(r"`\1`", line)

    if "<ul>" in line:
        line = flatten_cell_list(line)

    return RELATIVE_LINK.sub(rf"]({base}\1)", line)


def convert(text: str, base: str) -> str:
    """Clean a whole document. Fenced code blocks pass through byte-identical."""
    base = base.rstrip("/")
    out: list[str] = []
    in_code = False
    for line in strip_preamble(text).splitlines():
        if FENCE.match(line):
            in_code = not in_code
            out.append(line)
            continue
        if in_code:
            out.append(line)
            continue
        new = transform_line(line, base)
        # A line that held nothing but tags is now empty; drop it rather than
        # leaving the blank runs the stripped wrappers would otherwise create.
        if new.strip() or not line.strip():
            out.append(new)
    return BLANK_RUN.sub("\n\n", "\n".join(out)).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean a publisher's served markdown into plain GFM."
    )
    parser.add_argument("source", type=Path, help="the fetched <url>.md file")
    parser.add_argument("dest", type=Path, help="where to write the cleaned markdown")
    parser.add_argument("base_url", help="site root for relative targets")
    args = parser.parse_args()

    if not args.source.is_file():
        print(f"not a file: {args.source}", file=sys.stderr)
        return 1

    cleaned = convert(args.source.read_text(encoding="utf-8"), args.base_url)
    args.dest.write_text(cleaned, encoding="utf-8")
    print(f"{args.dest}: {len(cleaned.split())} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())
