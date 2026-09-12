#!/usr/bin/env python3
"""Pull a page's article body out of its nav/sidebar/breadcrumb chrome.

WebFetch paraphrases through a model instead of returning the source text
(see the ingestion session that wrote this), so this extracts one HTML node
directly from raw markup and lets `pandoc` do the HTML-to-markdown
conversion — no model in the loop, no site chrome in the output.

Usage: python extract_docusaurus_article.py <html-file> <tag.class|tag#id> > article.html

  tag.class  e.g. div.theme-doc-markdown — Docusaurus sites (playwright.dev,
             dbml.dbdiagram.io, d2lang.com, drawio.com all use this)
  tag#id     e.g. div#D7 — plantuml.com's hand-rolled layout
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser

# Docusaurus wraps every heading in a hash-link anchor (just a permalink icon)
# and every tab/code-block in layout <div>s. None of it is content — pandoc's
# gfm writer has no semantic mapping for a generic <div> and emits it as raw
# HTML, which is exactly the "leftover markup noise" the ingestion guide's
# quality check rules out. Stripping tags, not content: the div's children —
# a heading, a code block, a list — pass through untouched.
HASH_LINK = re.compile(r'<a\b[^>]*class=["\']?hash-link["\']?[^>]*>.*?</a>', re.DOTALL)
DIV_TAG = re.compile(r"</?(?:div|header|span)\b[^>]*>")
# Copy-button and admonition icons are inlined as base64 SVGs — a few hundred
# bytes of noise per icon, never content. A real content image (a screenshot)
# has a normal file src and is left alone.
ICON_IMG = re.compile(r'<img\b[^>]*src=["\']?data:image[^"\'>]*["\']?[^>]*/?>')
# Admonition/copy-button icons are inline <svg> markup, not <img> — pandoc's
# HTML reader can't map them either, and re-encodes each one as a base64
# data-URI image in the gfm output otherwise.
SVG_TAG = re.compile(r"<svg\b.*?</svg>", re.DOTALL)
# Old-style `<a name="..."></a>` scroll-anchor bookmarks, empty by construction.
# Pandoc's HTML reader turns each into a Span-with-id, which its gfm writer
# then has to fall back to raw HTML for — same shape of problem as the <svg>
# and <header> cases above, just one more tag pandoc can't map cleanly.
ANCHOR_BOOKMARK = re.compile(r'<a\b[^>]*\bname=["\']?[^"\'\s>]*["\']?[^>]*>\s*</a>')
# Inline CSS is never content, and pandoc's HTML reader passes an unrecognised
# <style> block through verbatim rather than dropping it.
STYLE_TAG = re.compile(r"<style\b.*?</style>", re.DOTALL)
# plantuml.com bakes a "back to top" icon and an "Edit in Dokuwiki/Asciidoc/
# Markdown" dropdown into the START of every heading, ahead of the actual
# heading text — the guide's "Edit this page" link, just several per page
# instead of one. The dropdown is two nested <div>s; DIV_TAG only strips tags
# and would leave its three edit-links as content, so this drops the whole
# thing, tags and content together.
BACKTOP_ICON = re.compile(r'<img\b[^>]*class="backtop"[^>]*/?>')
EDIT_DROPDOWN = re.compile(r'<div class="dropdown">.*?</div>\s*</div>', re.DOTALL)


def parse_selector(selector: str) -> tuple[str, str, str]:
    """'div.theme-doc-markdown' -> ('div', 'class', 'theme-doc-markdown')."""
    if "." in selector:
        tag, _, value = selector.partition(".")
        return tag, "class", value
    if "#" in selector:
        tag, _, value = selector.partition("#")
        return tag, "id", value
    raise ValueError(f"selector must be tag.class or tag#id, got {selector!r}")


class ArticleExtractor(HTMLParser):
    def __init__(self, tag: str, attr: str, value: str) -> None:
        super().__init__(convert_charrefs=False)
        self.tag, self.attr, self.value = tag, attr, value
        self.depth: int | None = None  # tag-nesting depth once inside the target
        self.chunks: list[str] = []

    def _matches(self, tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        if tag != self.tag:
            return False
        raw = dict(attrs).get(self.attr, "") or ""
        return self.value in raw.split() if self.attr == "class" else raw == self.value

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.depth is None and self._matches(tag, attrs):
            self.depth = 0
            return
        if self.depth is not None:
            self.chunks.append(self.get_starttag_text() or "")
            if tag == self.tag:
                self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self.depth is None:
            return
        if tag == self.tag:
            if self.depth == 0:
                self.depth = None
                return
            self.depth -= 1
        self.chunks.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self.depth is not None:
            self.chunks.append(data)

    def handle_entityref(self, name: str) -> None:
        if self.depth is not None:
            self.chunks.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self.depth is not None:
            self.chunks.append(f"&#{name};")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    html_path, selector = sys.argv[1], sys.argv[2]
    tag, attr, value = parse_selector(selector)
    html = open(html_path, encoding="utf-8").read()
    parser = ArticleExtractor(tag, attr, value)
    parser.feed(html)
    article = "".join(parser.chunks).strip()
    if not article:
        print(f"no <{tag} {attr}=\"...{value}...\"> found in {html_path}",
              file=sys.stderr)
        return 1
    article = HASH_LINK.sub("", article)
    article = ANCHOR_BOOKMARK.sub("", article)
    article = STYLE_TAG.sub("", article)
    article = BACKTOP_ICON.sub("", article)
    article = EDIT_DROPDOWN.sub("", article)
    article = ICON_IMG.sub("", article)
    article = SVG_TAG.sub("", article)
    article = DIV_TAG.sub("", article)
    sys.stdout.buffer.write(article.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
