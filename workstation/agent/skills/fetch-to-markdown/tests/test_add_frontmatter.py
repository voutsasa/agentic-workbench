"""Unit tests for add_frontmatter.py — stdlib only, no network, no model calls.

    python3 -m unittest discover -s workstation/agent/skills/fetch-to-markdown/tests

The block has to match what defuddle's own `--frontmatter` writes, because half
the corpus comes from each route and a reader should not be able to tell which.
defuddle itself is never invoked here: the runner is injected, so these tests
pass on a machine that does not have it, which is also the fallback path.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# E402: sys.path has to be extended before this import, so it cannot move to the top.
import add_frontmatter

PAGE = (
    '<html lang="en-US"><head><title>Getting Started | Guide | Vitest</title>'
    '<meta name="description" content="Next generation testing framework powered by Vite">'
    '<meta property="og:site_name" content="Vitest">'
    "</head><body><p>Body.</p></body></html>"
)

URL = "https://vitest.dev/guide/"


def absent(*args, **kwargs):
    """defuddle is not installed — what `subprocess.run` raises for a missing binary."""
    raise FileNotFoundError("defuddle")


def defuddle_returning(**payload):
    """A stub `run` answering as `defuddle parse - --json` would."""
    def run(cmd, **kwargs):
        assert cmd[:2] == ["defuddle", "parse"], cmd
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")
    return run


def block(html: str = PAGE, url: str = URL, body: str = "one two three", run=absent) -> str:
    return add_frontmatter.frontmatter(html, url, body, run=run)


def fields(text: str) -> dict[str, str]:
    """The block's `key: value` pairs, quotes stripped, in no particular order."""
    inner = text.split("---\n")[1]
    out = {}
    for line in inner.splitlines():
        key, _, value = line.partition(": ")
        out[key] = value[1:-1] if value.startswith('"') else value
    return out


class DefuddleMetadata(unittest.TestCase):
    """The preferred path: defuddle's own values, so both routes agree."""

    def test_uses_defuddles_fields_verbatim(self):
        run = defuddle_returning(title="Learn Java", site="Dev.java: The Destination",
                                 language="en", author="", description="")
        got = fields(block("<html><head><title>Learn Java - Dev.java</title></head></html>",
                           "https://dev.java/learn/", run=run))
        self.assertEqual(got["title"], "Learn Java")
        self.assertEqual(got["site"], "Dev.java: The Destination")
        self.assertEqual(got["language"], "en")
        self.assertNotIn("author", got)
        self.assertNotIn("description", got)

    def test_source_and_domain_still_come_from_the_url(self):
        run = defuddle_returning(title="Testing", site="docs.spring.io")
        got = fields(block(PAGE, "https://docs.spring.io/spring-boot/reference/testing/index.html", run=run))
        self.assertEqual(got["source"], "https://docs.spring.io/spring-boot/reference/testing/index.html")
        self.assertEqual(got["domain"], "docs.spring.io")

    def test_field_order_matches_defuddle(self):
        run = defuddle_returning(title="T", author="A", site="S", language="en", description="D")
        keys = [line.split(":")[0] for line in block(run=run).split("---\n")[1].splitlines()]
        self.assertEqual(
            keys,
            ["title", "author", "site", "source", "domain", "language", "description", "word_count"],
        )

    def test_falls_back_when_defuddle_is_not_installed(self):
        self.assertEqual(fields(block(run=absent))["title"], "Getting Started | Guide")

    def test_falls_back_when_defuddle_fails_or_answers_nonsense(self):
        def failing(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")

        def garbage(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="not json", stderr="")

        for run in (failing, garbage):
            with self.subTest(run=run):
                self.assertEqual(fields(block(run=run))["title"], "Getting Started | Guide")

    def test_the_fetched_html_is_what_gets_parsed(self):
        """Fed on stdin, never re-fetched: a second request could differ from the
        page that was actually converted."""
        seen = {}

        def run(cmd, **kwargs):
            seen["input"] = kwargs.get("input")
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"title": "T"}), stderr="")

        block(run=run)
        self.assertEqual(seen["input"], PAGE)


class FallbackFields(unittest.TestCase):
    """No defuddle: the page's own title, lang and meta tags."""

    def test_reads_title_language_description_and_site(self):
        got = fields(block())
        self.assertEqual(got["title"], "Getting Started | Guide")
        self.assertEqual(got["site"], "Vitest")
        self.assertEqual(got["language"], "en-US")
        self.assertEqual(got["description"], "Next generation testing framework powered by Vite")

    def test_word_count_counts_the_converted_body(self):
        """Whitespace-separated tokens of the markdown, `#` included — the count
        already written into the corpus, and within a word or two of defuddle's."""
        self.assertEqual(fields(block(body="# Title\n\none two three four"))["word_count"], "6")

    def test_absent_fields_are_omitted_not_written_empty(self):
        got = fields(block("<html><head><title>Bare</title></head><body></body></html>"))
        self.assertEqual(got["title"], "Bare")
        for missing in ("author", "site", "language", "description"):
            self.assertNotIn(missing, got)

    def test_a_twitter_handle_is_not_an_author(self):
        html = PAGE.replace("<head>", '<head><meta name="twitter:creator" content="@java">')
        self.assertNotIn("author", fields(block(html)))

    def test_entities_in_the_title_element_are_decoded(self):
        html = "<html><head><title>Tom &amp; Jerry</title></head><body></body></html>"
        self.assertEqual(fields(block(html))["title"], "Tom & Jerry")

    def test_quotes_and_backslashes_are_escaped(self):
        html = '<html><head><title>The "best" C:\\path tool</title></head><body></body></html>'
        line = next(x for x in block(html).splitlines() if x.startswith("title:"))
        self.assertEqual(line, 'title: "The \\"best\\" C:\\\\path tool"')

    def test_a_multiline_description_becomes_one_line(self):
        html = PAGE.replace(
            '"Next generation testing framework powered by Vite"',
            '"Next generation\n   testing framework"',
        )
        self.assertEqual(fields(block(html))["description"], "Next generation testing framework")


class TitleSuffix(unittest.TestCase):
    """Fallback-only cleaning: defuddle does its own."""

    def test_strips_a_site_name_that_opens_the_site_field(self):
        self.assertEqual(
            add_frontmatter.strip_site_suffix(
                "Learn Java - Dev.java", "Dev.java: The Destination for Java Developers"),
            "Learn Java",
        )

    def test_strips_a_tail_matching_the_domain(self):
        self.assertEqual(
            add_frontmatter.strip_site_suffix("Checkstyle 14.1.0 – checkstyle", "", "checkstyle.org"),
            "Checkstyle 14.1.0",
        )

    def test_ignores_www_when_matching_the_domain(self):
        self.assertEqual(
            add_frontmatter.strip_site_suffix("Docs | typescriptlang", "", "www.typescriptlang.org"),
            "Docs",
        )

    def test_collapses_a_title_repeated_around_a_separator(self):
        """Antora writes "Spring Boot :: Spring Boot" on a page with no section."""
        self.assertEqual(
            add_frontmatter.strip_site_suffix("Spring Boot :: Spring Boot", ""), "Spring Boot"
        )

    def test_keeps_a_title_whose_tail_is_neither_site_nor_domain(self):
        self.assertEqual(
            add_frontmatter.strip_site_suffix("Testing - Overview", "Angular", "angular.dev"),
            "Testing - Overview",
        )

    def test_a_title_that_is_only_the_site_name_survives(self):
        self.assertEqual(add_frontmatter.strip_site_suffix("Vitest", "Vitest", "vitest.dev"), "Vitest")


class FileHandling(unittest.TestCase):
    def run_main(self, markdown: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            md, html = Path(tmp) / "out.md", Path(tmp) / "page.html"
            md.write_text(markdown, encoding="utf-8")
            html.write_text(PAGE, encoding="utf-8")
            argv = sys.argv
            sys.argv = ["add_frontmatter.py", str(md), str(html), URL]
            try:
                self.assertEqual(add_frontmatter.main(), 0)
            finally:
                sys.argv = argv
            return md.read_text(encoding="utf-8")

    def test_prepends_the_block_and_keeps_the_body(self):
        out = self.run_main("# Getting Started\n\nBody text.\n")
        self.assertTrue(out.startswith("---\n"))
        self.assertIn(f'source: "{URL}"', out)
        self.assertTrue(out.endswith("# Getting Started\n\nBody text.\n"))

    def test_a_file_that_already_has_frontmatter_is_untouched(self):
        """defuddle's own output must survive a re-run unchanged."""
        existing = '---\ntitle: "Already"\nword_count: 2\n---\n\nBody text.\n'
        self.assertEqual(self.run_main(existing), existing)


if __name__ == "__main__":
    unittest.main()
