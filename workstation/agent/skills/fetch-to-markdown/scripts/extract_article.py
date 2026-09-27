#!/usr/bin/env python3
"""Pull a page's article body out of its nav/sidebar/breadcrumb chrome.

WebFetch paraphrases through a model instead of returning the source text
(see the ingestion session that wrote this), so this extracts one HTML node
directly from raw markup and lets `pandoc` do the HTML-to-markdown
conversion — no model in the loop, no site chrome in the output.

Usage: python extract_article.py <html-file> <tag|tag.class|tag#id|tag[attr=value]> [base-url] > article.html

  tag.class        e.g. div.theme-doc-markdown — Docusaurus sites (playwright.dev,
                   dbml.dbdiagram.io, d2lang.com, drawio.com all use this)
  tag#id           e.g. main#D7 — plantuml.com's hand-rolled layout
  tag[attr=value]  e.g. main[role=main] — typescriptlang.org/docs, whose article
                   node carries neither a class nor an id
  tag              e.g. main — agents.md, whose <main> carries no attribute at
                   all. The first node of that name wins, so use it only where
                   the page has one

Not Docusaurus-specific despite where it started: the selector is an argument,
so any server-rendered page whose article sits in one identifiable node works.

Pass the page's own URL as the optional third argument to rewrite relative
href/src targets against it. Without it a link like `./assets/slides.pdf`
survives the conversion intact and is dead the moment the file leaves the site,
which no markup check catches — the markdown is well-formed, it just points at
nothing.

Standard library only: this runs on a fresh clone before any venv exists.
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

# Docusaurus wraps every heading in a hash-link anchor (just a permalink icon)
# and every tab/code-block in layout <div>s. None of it is content — pandoc's
# gfm writer has no semantic mapping for a generic <div> and emits it as raw
# HTML, which is exactly the "leftover markup noise" the ingestion guide's
# quality check rules out. Stripping tags, not content: the div's children —
# a heading, a code block, a list — pass through untouched.
HASH_LINK = re.compile(r'<a\b[^>]*class=["\']?hash-link["\']?[^>]*>.*?</a>', re.DOTALL)
# <section> joins the list for Doxia (maven.apache.org, checkstyle.org) and
# Sphinx, which wrap every section in `<section id>`: pandoc's HTML reader maps
# it to a Div, and the gfm writer falls back to a raw `<div class="section">`.
#
# <figure> is the same failure with a worse blast radius. site.mockito.org wraps
# every code block in `<figure class="highlight">`; pandoc reads that as a Figure,
# gfm cannot express a figure holding a code block, and the writer falls back to
# raw HTML for the whole thing — 124 syntax-highlighting <span>s out of three code
# blocks, none of them in the input. Unwrapped, each block fences normally.
DIV_TAG = re.compile(r"</?(?:div|header|span|section|figure|figcaption)\b[^>]*>")
# Copy-button and admonition icons are inlined as base64 SVGs — a few hundred
# bytes of noise per icon, never content. A real content image (a screenshot)
# has a normal file src and is left alone.
ICON_IMG = re.compile(r'<img\b[^>]*src=["\']?data:image[^"\'>]*["\']?[^>]*/?>')
# The same noise with a file src: checkstyle.org decorates each feature card with
# `<img class="cs-card-logo">`, site.mockito.org opens with `logo@2x.png`, and
# java.testcontainers.org lists sponsors from `sponsor_logos/`. Matched on a
# `logo` or `icon` class word, or either word anywhere in the src, so a screenshot
# or diagram whose name carries neither is left alone.
DECORATIVE_IMG = re.compile(
    r'<img\b(?=[^>]*(?:class=["\'][^"\']*\b(?:logo|icon)\b|src=["\'][^"\']*(?:logo|icon)))[^>]*/?>',
    re.IGNORECASE,
)
# Admonition/copy-button icons are inline <svg> markup, not <img> — pandoc's
# HTML reader can't map them either, and re-encodes each one as a base64
# data-URI image in the gfm output otherwise.
SVG_TAG = re.compile(r"<svg\b.*?</svg>", re.DOTALL)
# Empty scroll-anchor bookmarks, by `name` (old-style) or by `id` (Doxia's
# `<a id="Section_Title"></a>` before every heading). Pandoc's HTML reader turns
# each into a Span-with-id, which its gfm writer then has to fall back to raw
# HTML for. Empty by construction, so a real link with an id is never matched.
ANCHOR_BOOKMARK = re.compile(
    r'<a\b[^>]*\b(?:name|id)=["\']?[^"\'\s>]*["\']?[^>]*>\s*</a>'
)
# An anchor with no href is not a link — java.testcontainers.org marks the page
# you are already on that way, `<a class="card-grid-item">Java</a>` among its
# links to the other languages. Pandoc maps it to a Span-with-class and the gfm
# writer emits raw HTML. Only the opening tag goes: the text is content, and the
# orphaned `</a>` left behind is ignored by pandoc's reader (measured, 3.11).
ANCHOR_NO_HREF = re.compile(r"<a\b(?![^>]*\bhref=)[^>]*>")
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
# Antora (docs.spring.io) puts its breadcrumb trail and its prev/next pagination
# *inside* article.doc, which is still the narrowest node holding the page. Both
# are site navigation, and the trail's empty `<li id="copy-url">` comes out of
# pandoc as a raw `<div id>` that fails the guide's markup check. Dropped whole,
# tags and content, like EDIT_DROPDOWN — and matched by class, so a <nav> the
# article uses for its own content is left alone.
NAV_CHROME = re.compile(
    r'<nav\b[^>]*\bclass="[^"]*\b(?:breadcrumbs|pagination)\b[^"]*"[^>]*>.*?</nav>',
    re.DOTALL,
)
# angular.dev renders its per-page table of contents as a class-less <aside>
# inside the article node: "On this page", the heading links, "Back to the top".
# Pandoc maps <aside> to a Div and emits it raw. Matched on that heading rather
# than on every <aside>, because an aside can also be a note that is content.
TOC_ASIDE = re.compile(
    r"<aside\b[^>]*>(?:(?!</aside>).)*?\bOn this page\b.*?</aside>", re.DOTALL
)


#: Attributes whose value is a single URL. `srcset` is deliberately absent: it
#: holds a comma-separated list with descriptors, so it needs its own parser and
#: no page ingested so far has one inside the article node.
URL_ATTRS = ("href", "src", "poster")
# Quoted, or bare: minified Docusaurus output (typescript-eslint.io, prettier.io)
# drops the quotes, `href=/getting-started/`, which a quoted-only pattern misses.
_URL_ATTR_RE = re.compile(
    r"\b("
    + "|".join(URL_ATTRS)
    + r')=(?:(["\'])(?P<url>[^"\']*)\2|(?P<bare>[^\s"\'=<>`]+))',
    re.IGNORECASE,
)


def absolutise(html: str, base_url: str) -> str:
    """Resolve relative href/src targets against the page's own URL.

    ``urljoin`` leaves an absolute URL alone and resolves a relative one, and an
    unchanged target is returned exactly as written, so it needs no branch of
    ours. Two targets are skipped because joining them would corrupt them: a
    fragment-only link (``#section``) is intra-document, and a non-http scheme
    (``mailto:``, ``data:``, ``javascript:``) is not a path. A resolved bare
    value is written back quoted.
    """

    def replace(match: re.Match[str]) -> str:
        url = (
            match.group("url")
            if match.group("url") is not None
            else match.group("bare")
        )
        if not url or url.startswith(("#", "data:")):
            return match.group(0)
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url) and not url.startswith(
            ("http:", "https:")
        ):
            return match.group(0)
        joined = urljoin(base_url, url)
        if joined == url:
            return match.group(0)
        quote = match.group(2) or '"'
        return f"{match.group(1)}={quote}{joined}{quote}"

    return _URL_ATTR_RE.sub(replace, html)


def parse_selector(selector: str) -> tuple[str, str, str]:
    """'div.theme-doc-markdown' -> ('div', 'class', 'theme-doc-markdown').

    'main[role=main]' -> ('main', 'role', 'main'). The attribute form is checked
    first, because its value may itself contain a '.' or a '#'.
    """
    attribute = re.fullmatch(r"(\w+)\[([\w-]+)=[\"']?([^\"'\]]+)[\"']?\]", selector)
    if attribute:
        return attribute.group(1), attribute.group(2), attribute.group(3)
    if "." in selector:
        tag, _, value = selector.partition(".")
        if re.fullmatch(r"\w+", tag):
            return tag, "class", value
    elif "#" in selector:
        tag, _, value = selector.partition("#")
        if re.fullmatch(r"\w+", tag):
            return tag, "id", value
    if re.fullmatch(r"\w+", selector):
        # A bare tag name: no attribute to match on, so the first node of that
        # name wins. agents.md's <main> carries neither class nor id.
        return selector, "", ""
    raise ValueError(
        f"selector must be tag, tag.class, tag#id or tag[attr=value], got {selector!r}"
    )


#: Elements with no end tag at all; never pushed on the open-element stack.
VOID = frozenset(
    [
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    ]
)
#: HTML5 optional end tags: a start tag in the key closes an open element in the
#: first set, searching no further up than an element in the second (its scope).
#: docs.databricks.com leaves every one of these out; pandoc's HTML reader then
#: flattens tables into one paragraph per cell and silently drops list nesting.
IMPLIED_CLOSE: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "li": (frozenset({"li"}), frozenset({"ul", "ol"})),
    "dt": (frozenset({"dt", "dd"}), frozenset({"dl"})),
    "dd": (frozenset({"dt", "dd"}), frozenset({"dl"})),
    "td": (frozenset({"td", "th"}), frozenset({"tr", "table"})),
    "th": (frozenset({"td", "th"}), frozenset({"tr", "table"})),
    "tr": (
        frozenset({"td", "th", "tr"}),
        frozenset({"thead", "tbody", "tfoot", "table"}),
    ),
    **{
        section: (
            frozenset({"td", "th", "tr", "thead", "tbody", "tfoot"}),
            frozenset({"table"}),
        )
        for section in ("thead", "tbody", "tfoot")
    },
}
#: Block-level start tags that end an open <p> sitting directly above them.
CLOSES_P = frozenset(
    [
        "address",
        "article",
        "aside",
        "blockquote",
        "details",
        "div",
        "dl",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "ul",
    ]
)


class ArticleExtractor(HTMLParser):
    """Copy one node's markup, writing back any end tag the source left out.

    Tags are copied as written. An element the source never closed is closed
    where HTML5 implies it, when its container ends, or when the article ends,
    so pandoc receives well-formed markup whether or not the page was minified.
    """

    def __init__(self, tag: str, attr: str, value: str) -> None:
        super().__init__(convert_charrefs=False)
        self.tag, self.attr, self.value = tag, attr, value
        self.inside = False
        self.stack: list[str] = []  # open elements inside the target node
        self.chunks: list[str] = []

    def _close_to(self, names: frozenset[str], scope: frozenset[str]) -> None:
        """Close the outermost open element in ``names`` below the nearest scope boundary.

        Outermost, so a new `<tbody>` ends the open `<th>`, `<tr>` and `<thead>` alike.
        """
        found: int | None = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] in scope:
                break
            if self.stack[index] in names:
                found = index
        if found is not None:
            self._pop_to(found)

    def _pop_to(self, index: int) -> None:
        while len(self.stack) > index:
            self.chunks.append(f"</{self.stack.pop()}>")

    def _matches(self, tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        if tag != self.tag:
            return False
        if not self.attr:  # bare tag selector: the name is the whole test
            return True
        raw = dict(attrs).get(self.attr, "") or ""
        return self.value in raw.split() if self.attr == "class" else raw == self.value

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self.inside:
            if self._matches(tag, attrs):
                self.inside = True
            return
        if tag in IMPLIED_CLOSE:
            self._close_to(*IMPLIED_CLOSE[tag])
        if tag in CLOSES_P and self.stack and self.stack[-1] == "p":
            self._pop_to(len(self.stack) - 1)
        self.chunks.append(self.get_starttag_text() or "")
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # `<br/>`, `<img .../>`: copied as written, never opened.
        if self.inside:
            self.chunks.append(self.get_starttag_text() or "")

    def handle_endtag(self, tag: str) -> None:
        if not self.inside:
            return
        if tag in self.stack:
            # Everything opened after it and never closed ends here too.
            self._pop_to(len(self.stack) - 1 - self.stack[::-1].index(tag))
        elif tag == self.tag:
            # The target node's own end tag: close whatever it still holds.
            self._pop_to(0)
            self.inside = False
        elif tag not in VOID:
            # A stray end tag with nothing to close; pandoc ignores it.
            self.chunks.append(f"</{tag}>")

    def close(self) -> None:
        super().close()
        if self.inside:
            self._pop_to(0)

    def handle_data(self, data: str) -> None:
        if self.inside:
            self.chunks.append(data)

    def handle_entityref(self, name: str) -> None:
        if self.inside:
            self.chunks.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self.inside:
            self.chunks.append(f"&#{name};")


#: One whole `<a …>` opening tag, and one attribute inside it.
LINK_OPEN = re.compile(r"<a\s[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r"""([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?""")
#: The only link attributes pandoc's gfm writer can express; any other one —
#: `target`, `rel`, `id` (measured, pandoc 3.11) — makes it emit raw `<a …>`.
KEPT_LINK_ATTRS = ("href", "title")


def trim_link_attributes(html: str) -> str:
    """Rewrite each `<a …>` to keep only ``href`` and ``title``, quoted."""

    def rewrite(match: re.Match[str]) -> str:
        found: dict[str, str] = {}
        for attr in _ATTR.finditer(match.group(0)[2:-1]):
            name = attr.group(1).lower()
            if name in KEPT_LINK_ATTRS and name not in found:
                value = next((g for g in attr.group(2, 3, 4) if g is not None), "")
                found[name] = value.replace('"', "&quot;")
        kept = "".join(f' {n}="{found[n]}"' for n in KEPT_LINK_ATTRS if n in found)
        return f"<a{kept}>"

    return LINK_OPEN.sub(rewrite, html)


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print(__doc__, file=sys.stderr)
        return 2
    html_path, selector = sys.argv[1], sys.argv[2]
    base_url = sys.argv[3] if len(sys.argv) == 4 else ""
    tag, attr, value = parse_selector(selector)
    html = Path(html_path).read_text(encoding="utf-8")
    parser = ArticleExtractor(tag, attr, value)
    parser.feed(html)
    parser.close()
    article = "".join(parser.chunks).strip()
    if not article:
        wanted = f'<{tag} {attr}="...{value}...">' if attr else f"<{tag}>"
        print(f"no {wanted} found in {html_path}", file=sys.stderr)
        return 1
    article = HASH_LINK.sub("", article)
    article = ANCHOR_BOOKMARK.sub("", article)
    article = ANCHOR_NO_HREF.sub("", article)
    article = STYLE_TAG.sub("", article)
    article = BACKTOP_ICON.sub("", article)
    article = EDIT_DROPDOWN.sub("", article)
    article = NAV_CHROME.sub("", article)
    article = TOC_ASIDE.sub("", article)
    article = ICON_IMG.sub("", article)
    article = DECORATIVE_IMG.sub("", article)
    article = SVG_TAG.sub("", article)
    article = DIV_TAG.sub("", article)
    article = trim_link_attributes(article)
    if base_url:
        article = absolutise(article, base_url)
    sys.stdout.buffer.write(article.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
