"""Unit tests for extract_article.py — stdlib only, no network, no model calls.

    python3 -m unittest discover -s workstation/agent/skills/fetch-to-markdown/tests

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
        extract_article.ANCHOR_NO_HREF,
        extract_article.STYLE_TAG,
        extract_article.BACKTOP_ICON,
        extract_article.EDIT_DROPDOWN,
        extract_article.NAV_CHROME,
        extract_article.TOC_ASIDE,
        extract_article.ICON_IMG,
        extract_article.DECORATIVE_IMG,
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

    def test_attribute_selector(self):
        self.assertEqual(
            extract_article.parse_selector("main[role=main]"), ("main", "role", "main")
        )

    def test_attribute_selector_accepts_quotes_and_dotted_values(self):
        self.assertEqual(
            extract_article.parse_selector('div[data-page="docs.index"]'),
            ("div", "data-page", "docs.index"),
        )

    def test_bare_tag_selector(self):
        """agents.md's <main> carries neither a class nor an id."""
        self.assertEqual(extract_article.parse_selector("main"), ("main", "", ""))

    def test_a_selector_that_is_neither_form_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_article.parse_selector("div .x")


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

    def test_bare_tag_selector_finds_a_node_with_no_attributes_at_all(self):
        """agents.md's article sits in a plain <main>, with the nav outside it."""
        html = "<body><nav>chrome</nav><main><h2>AGENTS.md</h2></main><footer>x</footer></body>"
        out = extract(html, "main")
        self.assertIn("<h2>AGENTS.md</h2>", out)
        self.assertNotIn("chrome", out)
        self.assertNotIn("<footer>", out)

    def test_attribute_selector_finds_a_node_with_no_class_or_id(self):
        """typescriptlang.org/docs keeps its article in a bare <main role="main">,
        with the site settings and the footer outside it."""
        html = (
            '<body><section id="customize">Site Colours</section>'
            '<main role="main"><h2>Handbook</h2><p>Everyday Types</p></main>'
            "<footer>Terms of Use</footer></body>"
        )
        out = extract(html, "main[role=main]")
        self.assertIn("<h2>Handbook</h2>", out)
        self.assertIn("Everyday Types", out)
        self.assertNotIn("Site Colours", out)
        self.assertNotIn("Terms of Use", out)

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

    def test_unwraps_section_tags_but_keeps_their_children(self):
        """Doxia and Sphinx wrap each section in <section id>, which pandoc would
        emit as a raw <div class="section">."""
        html = (
            '<main id="bodyColumn"><section id="Getting_Started">'
            "<h2>Getting started</h2><p>Body.</p></section></main>"
        )
        out = extract(html, "main#bodyColumn")
        self.assertIn("<h2>Getting started</h2>", out)
        self.assertIn("Body.", out)
        self.assertNotIn("<section", out)
        self.assertNotIn("</section>", out)

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

    def test_strips_logo_and_icon_images_by_class_or_src_but_keeps_content_images(self):
        """checkstyle.org decorates cards with <img class="cs-card-logo">;
        site.mockito.org and java.testcontainers.org name theirs in the src."""
        html = (
            '<div class="a">'
            '<img src="images/report.png" class="cs-card-logo" />'
            '<img src="images/arrow.svg" class="nav-icon">'
            '<img src="https://site.mockito.org/img/logo%402x.png" width="400" alt="Mockito" />'
            '<img src="https://java.testcontainers.org/sponsor_logos/vivy.png" style="width: 100%" />'
            '<img src="images/screenshot.png" alt="report">'
            '<img src="/assets/images/a-prettier-printer-by-james-long.png" alt="talk">'
            "</div>"
        )
        out = extract(html, "div.a")
        for decoration in (
            "cs-card-logo",
            "arrow.svg",
            "logo%402x.png",
            "sponsor_logos/vivy.png",
        ):
            self.assertNotIn(decoration, out)
        self.assertIn("images/screenshot.png", out)
        self.assertIn("a-prettier-printer-by-james-long.png", out)

    def test_unwraps_a_figure_around_a_code_block(self):
        """site.mockito.org wraps every code block in <figure class="highlight">.
        pandoc cannot express that in gfm and falls back to raw HTML for the whole
        figure, syntax-highlighting spans and all."""
        html = (
            '<div class="a"><figure class="highlight">'
            '<pre><code class="language-groovy" data-lang="groovy">mavenCentral()</code></pre>'
            "<figcaption>Gradle</figcaption></figure></div>"
        )
        out = extract(html, "div.a")
        self.assertNotIn("<figure", out)
        self.assertNotIn("<figcaption", out)
        self.assertIn(
            '<code class="language-groovy" data-lang="groovy">mavenCentral()</code>',
            out,
        )
        self.assertIn("Gradle", out)

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

    def test_strips_empty_id_anchors_but_keeps_real_links_with_an_id(self):
        """Doxia puts <a id="Section_Title"></a> before every heading."""
        html = (
            '<div class="a"><a id="Getting_Started"></a><h2>Getting started</h2>'
            '<a id="docs-link" href="/docs/">Read the docs</a></div>'
        )
        out = extract(html, "div.a")
        self.assertNotIn('id="Getting_Started"', out)
        self.assertIn('<a id="docs-link" href="/docs/">Read the docs</a>', out)

    def test_unwraps_an_anchor_with_no_href_but_keeps_real_links(self):
        """java.testcontainers.org marks the current page with a hrefless anchor,
        which pandoc turns into a raw <span class="card-grid-item">."""
        html = (
            '<div class="a"><p><a class="card-grid-item">Java</a> '
            '<a href="https://golang.testcontainers.org/" class="card-grid-item">Go</a></p></div>'
        )
        out = extract(html, "div.a")
        self.assertNotIn('<a class="card-grid-item">', out)
        self.assertIn("Java", out)
        self.assertIn(
            '<a href="https://golang.testcontainers.org/" class="card-grid-item">Go</a>',
            out,
        )

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

    def test_strips_antora_breadcrumbs_and_pagination_with_their_content(self):
        """docs.spring.io keeps both inside article.doc, the narrowest node. The
        trail's empty copy-url <li> otherwise reaches the markdown as a raw
        <div id>, and its links repeat the section path as if they were content."""
        html = (
            '<article class="doc">'
            '<div class="breadcrumbs-container">'
            '<nav class="breadcrumbs" aria-label="breadcrumbs"><ul>'
            '<li id="copy-url" title="Copy versioned URL"></li>'
            '<li><a href="index.html">Spring Boot</a></li>'
            '<li><a href="index.html">Overview</a></li>'
            "</ul></nav></div>"
            "<h1>Spring Boot</h1><p>Real text.</p>"
            '<nav class="pagination">'
            '<span class="next"><a href="documentation.html">Documentation</a></span>'
            "</nav>"
            "</article>"
        )
        out = extract(html, "article.doc")
        self.assertIn("<h1>Spring Boot</h1>", out)
        self.assertIn("Real text.", out)
        for chrome in (
            "copy-url",
            "breadcrumbs",
            "Overview",
            "pagination",
            "Documentation",
        ):
            self.assertNotIn(chrome, out)

    def test_keeps_a_nav_the_article_uses_for_its_own_content(self):
        """Only the breadcrumbs and pagination classes are chrome; a table of
        contents inside the article is the page's own text."""
        html = (
            '<article class="doc"><nav class="toc">'
            '<a href="#install">Install</a></nav><p>Body.</p></article>'
        )
        out = extract(html, "article.doc")
        self.assertIn("Install", out)
        self.assertIn("Body.", out)

    def test_strips_an_on_this_page_aside_but_keeps_a_note_aside(self):
        """angular.dev's per-page TOC is a class-less <aside> inside the article;
        an aside holding a note is content and stays."""
        html = (
            '<main class="docs-viewer"><h1>Testing</h1>'
            "<aside _ngcontent-ng-c1><h2>On this page</h2>"
            '<ul><li><a href="#setup">Setup</a></li></ul>'
            '<a href="#top">Back to the top</a></aside>'
            "<p>Body.</p>"
            '<aside class="note"><p>Vitest is the default runner.</p></aside>'
            "</main>"
        )
        out = extract(html, "main.docs-viewer")
        self.assertIn("<h1>Testing</h1>", out)
        self.assertIn("Body.", out)
        self.assertNotIn("On this page", out)
        self.assertNotIn("Back to the top", out)
        self.assertIn("Vitest is the default runner.", out)

    def test_a_clean_docusaurus_page_passes_the_guides_grep(self):
        """The end-to-end assertion: zero hits for the guide's own check."""
        html = (
            "<html><body>"
            '<nav class="navbar"><span>Docs</span></nav>'
            '<div class="theme-doc-markdown markdown">'
            "<style>.hidden{display:none}</style>"
            '<h1>Writing tests<a class="hash-link" href="#t">\u200b</a></h1>'
            "<p>Playwright <strong>is</strong> an end-to-end test framework.</p>"
            '<div class="tabs-container"><div class="tab"><pre><code>npm i</code></pre>'
            '<button><svg><path d="M0"/></svg></button></div></div>'
            "<ul><li>One</li><li>Two</li></ul>"
            "</div>"
            "<footer><div>Edit this page</div></footer>"
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


class AbsolutiseTests(unittest.TestCase):
    """The third argument resolves relative targets against the page's own URL.

    Added after the Berkeley LLM-agents syllabus converted cleanly — 0 markup
    noise, every table intact — while five slide links still read `./assets/…`
    and pointed at nothing outside the site. No markup check can see that: the
    markdown is well-formed, the target is simply wrong.
    """

    BASE = "https://rdi.berkeley.edu/llm-agents/f24"

    def absolutise(self, html: str) -> str:
        return extract_article.absolutise(html, self.BASE)

    def test_dot_slash_relative_href(self) -> None:
        out = self.absolutise('<a href="./assets/intro.pdf">Intro</a>')
        self.assertIn(
            'href="https://rdi.berkeley.edu/llm-agents/assets/intro.pdf"', out
        )

    def test_bare_relative_src(self) -> None:
        out = self.absolutise('<img src="assets/dawn.jpg" height="200" />')
        self.assertIn('src="https://rdi.berkeley.edu/llm-agents/assets/dawn.jpg"', out)

    def test_root_relative_href(self) -> None:
        out = self.absolutise('<a href="/llm-agents-mooc/">MOOC</a>')
        self.assertIn('href="https://rdi.berkeley.edu/llm-agents-mooc/"', out)

    def test_unquoted_root_relative_href_is_resolved_and_quoted(self) -> None:
        """Minified Docusaurus output (typescript-eslint.io, prettier.io) drops
        attribute quotes, which a quoted-only pattern never matched."""
        out = self.absolutise(
            "<a href=/getting-started/typed-linting>Typed Linting</a>"
        )
        self.assertIn(
            'href="https://rdi.berkeley.edu/getting-started/typed-linting"', out
        )
        self.assertIn(">Typed Linting</a>", out)

    def test_unquoted_absolute_url_is_untouched(self) -> None:
        html = "<a href=https://eslint.org target=_blank>ESLint</a>"
        self.assertEqual(html, self.absolutise(html))

    def test_absolute_url_is_untouched(self) -> None:
        html = '<a href="https://arxiv.org/abs/2402.10200">CoT</a>'
        self.assertEqual(html, self.absolutise(html))

    def test_fragment_is_untouched(self) -> None:
        """An intra-document link must stay intra-document."""
        for html in (
            '<a href="#syllabus">Syllabus</a>',
            "<a href=#syllabus>Syllabus</a>",
        ):
            with self.subTest(html=html):
                self.assertEqual(html, self.absolutise(html))

    def test_non_http_schemes_are_untouched(self) -> None:
        for html in (
            '<a href="mailto:staff@example.edu">Mail</a>',
            '<a href="javascript:void(0)">Menu</a>',
            '<img src="data:image/png;base64,AAAA" />',
        ):
            with self.subTest(html=html):
                self.assertEqual(html, self.absolutise(html))

    def test_single_quoted_attribute_keeps_its_quoting(self) -> None:
        out = self.absolutise("<a href='./a.pdf'>A</a>")
        self.assertIn("href='https://rdi.berkeley.edu/llm-agents/a.pdf'", out)

    def test_empty_target_is_untouched(self) -> None:
        html = '<a href="">Nothing</a>'
        self.assertEqual(html, self.absolutise(html))

    def test_no_base_url_leaves_the_document_alone(self) -> None:
        """The argument is optional, and omitting it must change nothing."""
        html = '<a href="./assets/intro.pdf">Intro</a>'
        self.assertEqual(html, extract_article.absolutise(html, ""))


if __name__ == "__main__":
    unittest.main()
