"""Unit tests for extract_article.py — stdlib only, no network, no model calls.

    python3 -m unittest discover -s skills/fetch-to-markdown/tests

The assertions are written against the ingestion guide's quality check: after a
Docusaurus extraction, `grep -c "<div\\|<header\\|<span\\|<svg\\|<style"` on the
converted output must be 0. Each stripping test below is one clause of that.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# E402: sys.path has to be extended before this import, so it cannot move to the top.
import extract_article


def extract(html: str, selector: str) -> str:
    """Run the parser and the stripping passes, as main() does."""
    tag, attr, value = extract_article.parse_selector(selector)
    parser = extract_article.ArticleExtractor(tag, attr, value)
    parser.feed(html)
    article = "".join(parser.chunks).strip()
    for pattern in (
        extract_article.HASH_LINK,
        extract_article.ANCHOR_BOOKMARK,
        extract_article.STYLE_TAG,
        extract_article.BACKTOP_ICON,
        extract_article.EDIT_DROPDOWN,
        extract_article.ICON_IMG,
        extract_article.SVG_TAG,
        extract_article.DIV_TAG,
    ):
        article = pattern.sub("", article)
    return article


class ParseSelectorTests(unittest.TestCase):
    def test_class_selector(self):
        self.assertEqual(
            extract_article.parse_selector("div.theme-doc-markdown"),
            ("div", "class", "theme-doc-markdown"),
        )

    def test_id_selector(self):
        self.assertEqual(
            extract_article.parse_selector("main#D7"), ("main", "id", "D7")
        )

    def test_bare_tag_is_rejected(self):
        """A bare tag would match the first <div> on the page, which is chrome."""
        with self.assertRaises(ValueError):
            extract_article.parse_selector("div")


class NodeSelectionTests(unittest.TestCase):
    def test_takes_the_article_and_leaves_the_chrome(self):
        html = (
            "<html><body>"
            '<nav class="navbar">Site nav</nav>'
            '<div class="theme-doc-markdown"><h1>Real heading</h1><p>Real text.</p></div>'
            '<footer class="footer">Cookie banner</footer>'
            "</body></html>"
        )
        out = extract(html, "div.theme-doc-markdown")
        self.assertIn("<h1>Real heading</h1>", out)
        self.assertIn("Real text.", out)
        self.assertNotIn("Site nav", out)
        self.assertNotIn("Cookie banner", out)

    def test_matches_one_class_among_several(self):
        """Docusaurus emits `class="theme-doc-markdown markdown"`, so an equality
        check on the attribute would find nothing."""
        html = '<div class="theme-doc-markdown markdown"><p>Body.</p></div>'
        self.assertIn("Body.", extract(html, "div.theme-doc-markdown"))

    def test_a_class_that_is_only_a_substring_does_not_match(self):
        html = '<div class="theme-doc-markdown-wrapper"><p>Wrapper.</p></div>'
        self.assertEqual(extract(html, "div.theme-doc-markdown"), "")

    def test_nested_same_tag_does_not_close_the_article_early(self):
        """The depth counter is the whole reason this is a parser and not a
        regex: an inner </div> must not end the extraction."""
        html = (
            '<div class="theme-doc-markdown">'
            "<p>Before.</p><div><div><p>Deep.</p></div></div><p>After.</p>"
            "</div>"
            "<p>Outside.</p>"
        )
        out = extract(html, "div.theme-doc-markdown")
        self.assertIn("Before.", out)
        self.assertIn("Deep.", out)
        self.assertIn("After.", out)
        self.assertNotIn("Outside.", out)

    def test_id_selector_finds_a_hand_rolled_layout(self):
        """plantuml.com's article sits in <main id="D7">, not a Docusaurus node."""
        html = '<body><nav>chrome</nav><main id="D7"><h2>PlantUML</h2></main></body>'
        out = extract(html, "main#D7")
        self.assertIn("<h2>PlantUML</h2>", out)
        self.assertNotIn("chrome", out)

    def test_missing_node_yields_nothing(self):
        self.assertEqual(extract("<p>no article here</p>", "div.absent"), "")

    def test_entities_survive(self):
        """convert_charrefs=False, so these come through the entity handlers and
        have to be re-emitted rather than dropped."""
        html = '<div class="a"><p>Tom &amp; Jerry &#8212; &lt;tag&gt;</p></div>'
        out = extract(html, "div.a")
        self.assertIn("&amp;", out)
        self.assertIn("&#8212;", out)
        self.assertIn("&lt;tag&gt;", out)


class StrippingTests(unittest.TestCase):
    """One test per clause of the guide's grep-for-zero quality check."""

    def test_strips_hash_link_permalink_anchors(self):
        html = (
            '<div class="a"><h2>Install'
            '<a class="hash-link" href="#install">\u200b</a></h2></div>'
        )
        out = extract(html, "div.a")
        self.assertIn("<h2>Install</h2>", out)
        self.assertNotIn("hash-link", out)

    def test_strips_layout_tags_but_keeps_their_children(self):
        html = (
            '<div class="a"><div class="tabs"><span><h3>Kept</h3></span>'
            "<header>Header text</header></div></div>"
        )
        out = extract(html, "div.a")
        self.assertIn("<h3>Kept</h3>", out)
        self.assertIn("Header text", out)
        for tag in ("<div", "<span", "<header"):
            self.assertNotIn(tag, out)

    def test_strips_inline_svg_icons(self):
        html = '<div class="a"><p>Note<svg viewBox="0 0 24 24"><path d="M0"/></svg></p></div>'
        out = extract(html, "div.a")
        self.assertIn("<p>Note</p>", out)
        self.assertNotIn("<svg", out)

    def test_strips_base64_icon_images_but_keeps_real_ones(self):
        html = (
            '<div class="a">'
            '<img src="data:image/svg+xml;base64,PHN2Zz4=" alt="copy">'
            '<img src="/img/screenshot.png" alt="screenshot">'
            "</div>"
        )
        out = extract(html, "div.a")
        self.assertNotIn("data:image", out)
        self.assertIn("/img/screenshot.png", out)

    def test_strips_style_blocks(self):
        html = '<div class="a"><style>.x{color:red}</style><p>Body.</p></div>'
        out = extract(html, "div.a")
        self.assertNotIn("<style", out)
        self.assertNotIn("color:red", out)
        self.assertIn("Body.", out)

    def test_strips_empty_anchor_bookmarks(self):
        html = '<div class="a"><a name="section-3"></a><p>Body.</p></div>'
        out = extract(html, "div.a")
        self.assertNotIn('name="section-3"', out)
        self.assertIn("Body.", out)

    def test_strips_plantuml_backtop_and_edit_dropdown_with_their_content(self):
        """Unlike the layout tags, the dropdown's own text is chrome too — three
        edit links that DIV_TAG would leave behind as bare content."""
        html = (
            '<div class="a"><h2>'
            '<img class="backtop" src="/top.png">'
            '<div class="dropdown"><div class="menu">'
            "<a>Edit in Dokuwiki</a><a>Edit in Asciidoc</a><a>Edit in Markdown</a>"
            "</div></div>"
            "Sequence diagrams</h2></div>"
        )
        out = extract(html, "div.a")
        self.assertIn("Sequence diagrams", out)
        self.assertNotIn("backtop", out)
        self.assertNotIn("Edit in", out)

    def test_a_clean_docusaurus_page_passes_the_guides_grep(self):
        """The end-to-end assertion: zero hits for the guide's own check."""
        html = (
            "<html><body>"
            '<nav class="navbar"><span>Docs</span></nav>'
            '<div class="theme-doc-markdown markdown">'
            '<style>.hidden{display:none}</style>'
            '<h1>Writing tests<a class="hash-link" href="#t">\u200b</a></h1>'
            "<p>Playwright <strong>is</strong> an end-to-end test framework.</p>"
            '<div class="tabs-container"><div class="tab"><pre><code>npm i</code></pre>'
            '<button><svg><path d="M0"/></svg></button></div></div>'
            "<ul><li>One</li><li>Two</li></ul>"
            "</div>"
            '<footer><div>Edit this page</div></footer>'
            "</body></html>"
        )
        out = extract(html, "div.theme-doc-markdown")

        for noise in ("<div", "<header", "<span", "<svg", "<style"):
            self.assertNotIn(noise, out, f"guide's quality check would fail on {noise}")
        # Verbatim source text, unparaphrased — the reason this exists instead
        # of WebFetch.
        self.assertIn("<strong>is</strong> an end-to-end test framework", out)
        self.assertIn("<h1>Writing tests</h1>", out)
        self.assertIn("<code>npm i</code>", out)
        self.assertIn("<li>One</li>", out)
        self.assertNotIn("Edit this page", out)


if __name__ == "__main__":
    unittest.main()
