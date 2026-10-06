#!/usr/bin/env python3
"""Prepend the corpus frontmatter block to a converted markdown file.

The defuddle route writes one itself (`--frontmatter`); the extractor route does
not, which is how a corpus ends up half with and half without. This produces the
same block, so a file's provenance is readable whichever route converted it:

    ---
    title: "Getting Started | Guide"
    site: "Vitest"
    source: "https://vitest.dev/guide/"
    domain: "vitest.dev"
    language: "en-US"
    description: "Next generation testing framework powered by Vite"
    word_count: 886
    ---

`source` and `domain` come from the URL the caller passes and `word_count` from
the converted body. The rest comes from `defuddle parse - --json`, the same
metadata the other routes write, so the two agree field for field. Where defuddle
is not installed the page's own `<title>`, `<html lang>` and meta tags are read
instead — a close approximation, not a copy: defuddle's title cleaning and site
naming are its own. A field neither source supplies is omitted rather than
written empty.

Usage: python add_frontmatter.py <markdown-file> <page-html-file> <url>

Idempotent: a file already starting with `---` is left untouched, so re-running
over a corpus, or over defuddle's own output, changes nothing.

Standard library only: this runs on a fresh clone before any venv exists.
"""

from __future__ import annotations

import json
import subprocess
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

#: Frontmatter fields, in the order defuddle writes them, mapped to its JSON keys.
#: `source`, `domain` and `word_count` are the caller's and are added separately.
DEFUDDLE_KEYS = (
    ("title", "title"),
    ("author", "author"),
    ("site", "site"),
    ("language", "language"),
    ("description", "description"),
)

#: Title/site separators, in the order publishers use them. Only for the fallback
#: path: a title ending in one of these followed by the site name is that name
#: twice — "Learn Java - Dev.java", "Checkstyle 14.1.0 – checkstyle".
SEPARATORS = (" :: ", " | ", " - ", " — ", " · ", " – ")

#: Fallback meta tags, by the field each fills; first hit wins. Twitter handles
#: are deliberately absent: `twitter:creator` is an account, not an author.
META_FIELDS = {
    "title": ("og:title",),
    "site": ("og:site_name", "application-name"),
    "description": ("description", "og:description"),
    "author": ("author", "article:author"),
}


class PageMetadata(HTMLParser):
    """`<title>`, `<html lang>` and the meta tags, pulled in one pass.

    Only the first `<title>` counts as the document's own. An inline SVG icon
    carries its own `<title>` for accessibility — GitHub's page serves nav
    icons titled "GitHub", "Discord", "X" and so on — and HTMLParser has no
    notion of nesting to tell those apart from `<head><title>`, so without this
    guard every icon's label runs on after the real title.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.language = ""
        self.meta: dict[str, str] = {}
        self._in_title = False
        self._title_done = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html" and values.get("lang"):
            self.language = self.language or values["lang"].strip()
        elif tag == "title":
            if not self._title_done:
                self._in_title = True
        elif tag == "meta":
            key = (values.get("name") or values.get("property") or "").strip().lower()
            content = values.get("content", "").strip()
            if key and content:
                self.meta.setdefault(key, content)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._in_title:
            self._in_title = False
            self._title_done = True

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def strip_site_suffix(title: str, site: str, domain: str = "") -> str:
    """'Learn Java - Dev.java' + domain 'dev.java' -> 'Learn Java'.

    The tail counts as the site's name when it equals the site, opens it
    ("Dev.java" for "Dev.java: The Destination for Java Developers"), or matches
    the domain with any `www.` and TLD dropped. Also collapses a title that is
    one name repeated around a separator, which Antora emits as "Spring Boot ::
    Spring Boot". Never returns an empty string: a title that is *only* the site
    name is left as it is.
    """
    host = domain.lower().removeprefix("www.")
    brands = {
        site.strip().lower(),
        host,
        host.rsplit(".", 1)[0] if "." in host else host,
    }
    brands.discard("")
    for separator in SEPARATORS:
        head, found, tail = title.rpartition(separator)
        if not found or not head.strip() or not tail.strip():
            continue
        low = tail.strip().lower()
        if (
            low == head.strip().lower()
            or low in brands
            or any(b.startswith(low) for b in brands)
        ):
            return head.strip()
    return title.strip()


def metadata_from_defuddle(html: str, run=subprocess.run) -> dict[str, str] | None:
    """defuddle's own metadata, or None when it is not installed or fails.

    Fed on stdin rather than by URL: the page has already been fetched, and a
    second request could answer differently from the one that was converted.
    """
    try:
        done = run(
            ["defuddle", "parse", "-", "--json"],
            input=html,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return None
    if done.returncode != 0 or not done.stdout.strip():
        return None
    try:
        parsed = json.loads(done.stdout)
    except json.JSONDecodeError:
        return None
    return {field: str(parsed.get(key) or "").strip() for field, key in DEFUDDLE_KEYS}


def metadata_from_html(html: str, domain: str = "") -> dict[str, str]:
    """The same fields from the page itself, for a machine without defuddle."""
    parser = PageMetadata()
    parser.feed(html)
    found = {
        field: next((parser.meta[key] for key in keys if key in parser.meta), "")
        for field, keys in META_FIELDS.items()
    }
    title = unescape(parser.title).strip() or found["title"]
    return {
        "title": strip_site_suffix(title, found["site"], domain),
        "author": found["author"],
        "site": found["site"],
        "language": parser.language,
        "description": found["description"],
    }


def quote(value: str) -> str:
    """YAML double-quoted scalar, matching how defuddle writes its own block."""
    flat = " ".join(value.split())
    return '"' + flat.replace("\\", "\\\\").replace('"', '\\"') + '"'


def frontmatter(html: str, url: str, body: str, run=subprocess.run) -> str:
    """The block, in defuddle's field order, omitting what the page lacks."""
    domain = urlparse(url).netloc
    meta = metadata_from_defuddle(html, run=run) or metadata_from_html(html, domain)
    fields = [
        ("title", meta.get("title", "")),
        ("author", meta.get("author", "")),
        ("site", meta.get("site", "")),
        ("source", url),
        ("domain", domain),
        ("language", meta.get("language", "")),
        ("description", meta.get("description", "")),
    ]
    lines = [f"{name}: {quote(value)}" for name, value in fields if value.strip()]
    lines.append(f"word_count: {len(body.split())}")
    return "---\n" + "\n".join(lines) + "\n---\n\n"


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    markdown_path, html_path, url = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    body = markdown_path.read_text(encoding="utf-8")
    if body.startswith("---\n"):
        print(
            f"{markdown_path} already has frontmatter; left unchanged", file=sys.stderr
        )
        return 0
    html = html_path.read_text(encoding="utf-8", errors="replace")
    markdown_path.write_text(
        frontmatter(html, url, body) + body.lstrip("\n"), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
