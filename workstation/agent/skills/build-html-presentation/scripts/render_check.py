#!/usr/bin/env python3
"""Render every slide of a Reveal.js deck in headless Chromium and report what is broken.

Each slide is shown with all its fragments visible, then measured in slide coordinates (the
Reveal ``width``/``height`` config, before scaling). Reported per slide:

- ``overflow-bottom`` / ``overflow-right``: content reaches past the slide's edge;
- ``stacked-code``: a ``<pre>`` holds more than one ``<code>`` — step-by-step line highlighting
  (``data-line-numbers="1|2"``) stacks copies of the block, which show through any theme whose code
  background is not opaque; use static highlights (``data-line-numbers="2,4"``) instead.

Console errors and uncaught page errors are reported for the whole deck. ``--screenshots DIR``
saves one PNG per slide, named ``<h>.<v>.png``.

Not stdlib-only: it needs ``playwright``, which lives in the uv tool venv that
``workstation/cli/playwright/install.md`` puts there. Run it with that venv's interpreter
(``Scripts\\python.exe`` instead of ``bin/python`` on Windows):

    "$(uv tool dir)/playwright/bin/python" render_check.py <deck>/index.html

Exit codes: 0 no findings, 1 findings (JSON on stdout), 2 playwright not importable.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

#: Runs in the page for the current slide; returns raw measurements, judged by ``findings``.
MEASURE = """() => {
  const s = Reveal.getCurrentSlide();
  const scale = Reveal.getScale() || 1;
  const box = s.getBoundingClientRect();
  let bottom = 0, right = 0;
  for (const el of s.querySelectorAll('*')) {
    if (el.closest('aside.notes')) continue;
    const r = el.getBoundingClientRect();
    if (!r.width && !r.height) continue;
    bottom = Math.max(bottom, (r.bottom - box.top) / scale);
    right = Math.max(right, (r.right - box.left) / scale);
  }
  const stacked = [...s.querySelectorAll('pre')].filter(p => p.querySelectorAll('code').length > 1).length;
  const h = s.querySelector('h1, h2');
  return {title: h ? h.textContent.trim() : '', bottom: Math.round(bottom), right: Math.round(right), stacked};
}"""


def findings(
    slide: str, metrics: dict, width: int, height: int
) -> list[dict[str, str]]:
    """Judge one slide's measurements against the deck's configured slide size."""
    found = []
    if metrics["bottom"] > height:
        found.append(
            {
                "slide": slide,
                "issue": "overflow-bottom",
                "detail": f"content ends at {metrics['bottom']}px of {height}px",
            }
        )
    if metrics["right"] > width:
        found.append(
            {
                "slide": slide,
                "issue": "overflow-right",
                "detail": f"content ends at {metrics['right']}px of {width}px",
            }
        )
    if metrics["stacked"]:
        found.append(
            {
                "slide": slide,
                "issue": "stacked-code",
                "detail": f"{metrics['stacked']} code block(s) with stepped highlights",
            }
        )
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n", 1)[0])
    parser.add_argument("deck", type=Path, help="the deck's index.html")
    parser.add_argument(
        "--viewport", default="1280x720", help="browser size, WxH (default 1280x720)"
    )
    parser.add_argument(
        "--screenshots", type=Path, help="save one PNG per slide into this folder"
    )
    args = parser.parse_args(argv)

    try:
        from playwright.sync_api import (  # pyright: ignore[reportMissingImports] — uv tool venv only
            sync_playwright,
        )
    except ImportError:
        print(
            "playwright is not importable; run this with the uv tool venv's interpreter",
            file=sys.stderr,
        )
        return 2

    vw, vh = (int(n) for n in args.viewport.lower().split("x"))
    report: list[dict[str, str]] = []
    errors: list[str] = []
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": vw, "height": vh})
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(args.deck.resolve().as_uri())
        page.wait_for_function("window.Reveal && Reveal.isReady()")
        width, height = page.evaluate(
            "[Reveal.getConfig().width, Reveal.getConfig().height]"
        )
        slides = page.evaluate(
            "Reveal.getHorizontalSlides().map(h => Math.max(1, h.querySelectorAll(':scope > section').length))"
        )
        for h, count in enumerate(slides):
            for v in range(count):
                page.evaluate(
                    f"Reveal.slide({h}, {v}, 999)"
                )  # past the last fragment: all visible
                page.wait_for_timeout(500)
                label = f"{h + 1}.{v + 1}" if count > 1 else str(h + 1)
                metrics = page.evaluate(MEASURE)
                report.extend(
                    findings(
                        f"{label} {metrics['title']}".strip(), metrics, width, height
                    )
                )
                if args.screenshots:
                    page.screenshot(path=str(args.screenshots / f"{h + 1}.{v + 1}.png"))
        browser.close()

    report.extend({"slide": "-", "issue": "console-error", "detail": e} for e in errors)
    print(json.dumps({"slides": sum(slides), "findings": report}, indent=2))
    return 1 if report else 0


if __name__ == "__main__":
    sys.exit(main())
