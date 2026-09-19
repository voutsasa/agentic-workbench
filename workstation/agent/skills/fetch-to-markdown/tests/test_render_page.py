"""Unit tests for render_page.py — stdlib only, no browser, no network.

    python3 -m unittest discover -s workstation/agent/skills/fetch-to-markdown/tests

Playwright itself is never imported here: the browser is a fake injected into
``render``, so these tests pass under the repo venv, which does not have it.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import Self
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# E402: sys.path has to be extended before this import, so it cannot move to the top.
import render_page


class FakeTimeout(Exception):
    pass


class FakePage:
    def __init__(self, idle_times_out: bool) -> None:
        self.idle_times_out = idle_times_out
        self.calls: list[tuple] = []

    def goto(self, url: str, wait_until: str) -> None:
        self.calls.append(("goto", url, wait_until))
        if wait_until == "networkidle" and self.idle_times_out:
            raise FakeTimeout("Page.goto: Timeout 30000ms exceeded.")

    def wait_for_timeout(self, ms: int) -> None:
        self.calls.append(("wait", ms))

    def eval_on_selector_all(self, selector: str, script: str) -> None:
        self.calls.append(("eval", selector, script))

    def content(self) -> str:
        return "<html><body><a href='https://example.org/x'>x</a></body></html>"


class FakeBrowser:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.closed = False

    def new_page(self) -> FakePage:
        return self.page

    def close(self) -> None:
        self.closed = True


class FakePlaywright:
    def __init__(self, page: FakePage) -> None:
        self.browser = FakeBrowser(page)
        self.chromium = mock.Mock(launch=mock.Mock(return_value=self.browser))

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def render(idle_times_out: bool) -> tuple[str, FakePage, FakePlaywright]:
    page = FakePage(idle_times_out)
    pw = FakePlaywright(page)
    html = render_page.render(
        "https://example.org/docs", lambda: pw, FakeTimeout, settle_ms=1234
    )
    return html, page, pw


class TestRender(unittest.TestCase):
    def test_waits_for_network_idle_first(self) -> None:
        _html, page, _pw = render(idle_times_out=False)
        self.assertEqual(
            ("goto", "https://example.org/docs", "networkidle"), page.calls[0]
        )
        self.assertNotIn(("wait", 1234), page.calls)

    def test_falls_back_to_load_and_a_settle_wait_when_idle_times_out(self) -> None:
        _html, page, _pw = render(idle_times_out=True)
        gotos = [c for c in page.calls if c[0] == "goto"]
        self.assertEqual(["networkidle", "load"], [c[2] for c in gotos])
        self.assertIn(("wait", 1234), page.calls)

    def test_makes_links_and_images_absolute_before_capturing(self) -> None:
        _html, page, _pw = render(idle_times_out=False)
        selectors = [c[1] for c in page.calls if c[0] == "eval"]
        self.assertEqual(["a[href]", "img[src]"], selectors)
        scripts = [c[2] for c in page.calls if c[0] == "eval"]
        self.assertIn("e.href", scripts[0])
        self.assertIn("e.src", scripts[1])

    def test_returns_the_page_html_and_closes_the_browser(self) -> None:
        html, _page, pw = render(idle_times_out=False)
        self.assertIn("https://example.org/x", html)
        self.assertTrue(pw.browser.closed)


class TestMain(unittest.TestCase):
    def test_writes_the_rendered_html_to_the_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "rendered.html"
            with (
                mock.patch.object(
                    render_page, "render", return_value="<html>ok</html>"
                ),
                mock.patch.object(
                    render_page, "load_playwright", return_value=(object, FakeTimeout)
                ),
            ):
                code = render_page.main(["https://example.org", str(out)])
            self.assertEqual(0, code)
            self.assertEqual("<html>ok</html>", out.read_text(encoding="utf-8"))

    def test_missing_playwright_exits_2_naming_the_pipx_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "rendered.html"
            with (
                mock.patch.object(
                    render_page,
                    "load_playwright",
                    side_effect=ImportError("no playwright"),
                ),
                mock.patch("sys.stderr") as err,
            ):
                code = render_page.main(["https://example.org", str(out)])
            self.assertEqual(2, code)
            written = "".join(c.args[0] for c in err.write.call_args_list)
            self.assertIn("PIPX_LOCAL_VENVS", written)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
