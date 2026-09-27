#!/usr/bin/env python3
"""Render a JS-hydrated page with headless Chromium and save its HTML.

The first half of the JS-hydrated route; defuddle is the second. The uv tool
venv's interpreter is `bin/python` on POSIX, `Scripts\\python.exe` on Windows:

    "$(uv tool dir)/playwright/bin/python" \\
        render_page.py <url> <tmp>/rendered.html
    defuddle parse - --md --frontmatter < <tmp>/rendered.html > "<dest>.md"

Two things it does that a bare `page.content()` does not, both measured on
agentskills.io on 2026-09-18:

- `wait_until="networkidle"` first, because `load` can fire before hydration —
  but a site holding a connection open never goes idle, and that times out after
  30 s. On timeout it reloads with `load` and waits `--settle-ms` for hydration.
- Every `href` and `src` is rewritten to its absolute value in the browser before
  capture. defuddle reads the HTML from stdin, never sees the URL, and has no
  option to take one, so a relative link would survive into the markdown.

Unlike its sibling scripts this one is not stdlib-only: it needs `playwright`,
which lives in the uv tool venv that `workstation/cli/playwright/install.md` puts
there. Run it with that venv's interpreter, as above. Exit codes: 0 written,
2 playwright not importable.

Usage: render_page.py <url> <out.html> [--settle-ms N]
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ABSOLUTE_HREF = "els => els.forEach(e => e.setAttribute('href', e.href))"
ABSOLUTE_SRC = "els => els.forEach(e => e.setAttribute('src', e.src))"
DEFAULT_SETTLE_MS = 3000

#: The uv tool venv's interpreter, relative to `uv tool dir`/playwright — POSIX
#: and Windows venvs lay out Scripts/bin differently.
_TOOL_PYTHON = "Scripts/python.exe" if os.name == "nt" else "bin/python"

MISSING = (
    "render_page: playwright is not importable from {python}.\n"
    "Run this script with the uv tool venv's interpreter:\n"
    f'  "$(uv tool dir)/playwright/{_TOOL_PYTHON}" '
    "render_page.py <url> <out.html>\n"
)


def load_playwright() -> tuple[Callable[[], Any], type[BaseException]]:
    """``sync_playwright`` and its ``TimeoutError``, imported only when needed."""
    from playwright.sync_api import (  # pyright: ignore[reportMissingImports] — uv tool venv only
        TimeoutError,
        sync_playwright,
    )

    return sync_playwright, TimeoutError


def render(
    url: str,
    sync_playwright: Callable[[], Any],
    timeout_error: type[BaseException],
    settle_ms: int = DEFAULT_SETTLE_MS,
) -> str:
    """The page's HTML after hydration, with every link and image made absolute."""
    with sync_playwright() as p:
        browser = p.chromium.launch()  # headless by default
        try:
            page = browser.new_page()
            try:
                page.goto(url, wait_until="networkidle")
            except timeout_error:  # a site holding a connection open never goes idle
                page.goto(url, wait_until="load")
                page.wait_for_timeout(settle_ms)
            page.eval_on_selector_all("a[href]", ABSOLUTE_HREF)
            page.eval_on_selector_all("img[src]", ABSOLUTE_SRC)
            return page.content()
        finally:
            browser.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render a JS-hydrated page with headless Chromium and save its HTML."
    )
    parser.add_argument("url")
    parser.add_argument("out", type=Path)
    parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS)
    args = parser.parse_args(argv)
    try:
        sync_playwright, timeout_error = load_playwright()
    except ImportError:
        sys.stderr.write(MISSING.format(python=sys.executable))
        return 2
    html = render(args.url, sync_playwright, timeout_error, args.settle_ms)
    args.out.write_text(html, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
