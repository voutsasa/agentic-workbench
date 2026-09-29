"""Tests that DEVELOPMENT-PLAN.md's ``✓``/``➕`` markers agree with SOURCES.md.

``✓`` means a reading row's source is already registered in ``SOURCES.md``; ``➕``
means it is not (`docs/guidance/DEVELOPMENT-PLAN.md` § *How to read the tables*,
`AGENTS.md` § *Register and corpus*). Nothing else reads the marker, so a source
that gets registered — or removed — without the plan's row being flipped drifts
silently. These tests hold every plan row that names a real source to the
register's own URLs, rather than trusting the marker as written.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PLAN = REPO / "docs" / "guidance" / "DEVELOPMENT-PLAN.md"
SOURCES = REPO / "SOURCES.md"

REGISTERED = "✓"
UNREGISTERED = "➕"

#: A row's source, when it names one with a markdown link: ``[text](http...)``.
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")

#: A reading row: marker, importance stars (ignored), then the reading cell.
#: Every table this checks has exactly this shape — see the module docstring.
ROW = re.compile(r"^\|\s*([✓➕])\s*\|\s*[^|]*\|\s*(.*)\|\s*$")


def normalize_url(url: str) -> str:
    """Strip a fragment and one trailing slash, so equivalent URLs compare equal."""
    url = url.split("#", 1)[0]
    return url.removesuffix("/")


def registered_sources(text: str) -> tuple[set[str], dict[str, str]]:
    """Every ``[text](http...)`` entry in ``SOURCES.md``.

    Returns its normalized URLs, plus a lowercased-title -> URL map for the rare
    plan row that names a source without a link of its own (see ``plan_rows``).
    Rows without an ``http(s)`` link — relative cross-references, italic *see
    also* notes — never match ``LINK`` and so never enter either result.
    """
    urls: set[str] = set()
    titles: dict[str, str] = {}
    for title, url in LINK.findall(text):
        norm = normalize_url(url)
        urls.add(norm)
        titles[title.strip().lower()] = norm
    return urls, titles


class PlanRow:
    """One reading row: its line number, marker, source name, and URL if linked."""

    __slots__ = ("line_no", "marker", "name", "url")

    def __init__(self, line_no: int, marker: str, name: str, url: str | None) -> None:
        self.line_no = line_no
        self.marker = marker
        self.name = name
        self.url = url


def plan_rows(text: str) -> list[PlanRow]:
    """Every ``| ✓ | ... |`` / ``| ➕ | ... |`` row in the plan.

    Most rows carry a markdown link; its URL is what gets checked. A few name a
    source by title only, with no link in the cell (e.g. a row that reads
    "Agent SDK overview" instead of repeating the link already given earlier)
    — for those, the row's name is kept as text and matched by title in
    ``marker_mismatches`` instead. A row with neither a link nor a name that
    matches a registered title (a gap-closing or "your own X" row) carries no
    evidence either way and is left for the caller to skip.
    """
    rows: list[PlanRow] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        m = ROW.match(line.strip())
        if not m:
            continue
        marker, rest = m.group(1), m.group(2)
        link = LINK.search(rest)
        if link:
            rows.append(
                PlanRow(
                    line_no, marker, link.group(1).strip(), normalize_url(link.group(2))
                )
            )
        else:
            name = rest.split("—", 1)[0].strip()
            rows.append(PlanRow(line_no, marker, name, None))
    return rows


def marker_mismatches(
    rows: list[PlanRow], urls: set[str], titles: dict[str, str]
) -> list[str]:
    """Rows whose marker disagrees with the register, as human-readable lines.

    A linked row is checked against ``urls``. An unlinked row is checked only
    when its name exactly matches a registered title in ``titles``; otherwise
    it is skipped — it names a gap or a generic deliverable, not a source.
    """
    problems: list[str] = []
    for row in rows:
        if row.url is not None:
            is_registered = row.url in urls
        elif row.name.lower() in titles:
            is_registered = True
        else:
            continue
        if row.marker == UNREGISTERED and is_registered:
            problems.append(
                f"line {row.line_no}: {row.name!r} is marked {UNREGISTERED} "
                "(not registered) but its source is in SOURCES.md"
            )
        elif row.marker == REGISTERED and not is_registered:
            problems.append(
                f"line {row.line_no}: {row.name!r} is marked {REGISTERED} "
                "(registered) but its source is not in SOURCES.md"
            )
    return problems


class NormalizeUrl(unittest.TestCase):
    def test_strips_fragment(self) -> None:
        self.assertEqual(normalize_url("https://x.io/a#frag"), "https://x.io/a")

    def test_strips_one_trailing_slash(self) -> None:
        self.assertEqual(normalize_url("https://x.io/a/"), "https://x.io/a")

    def test_leaves_a_plain_url_alone(self) -> None:
        self.assertEqual(normalize_url("https://x.io/a"), "https://x.io/a")


class RegisteredSourcesParser(unittest.TestCase):
    def test_collects_urls_and_titles_ignoring_relative_links(self) -> None:
        text = (
            "* [Real Source](https://example.com/docs/)\n"
            "* [Internal](../../AGENTS.md)\n"
            "*See also:* Something Else (§2).\n"
        )
        urls, titles = registered_sources(text)
        self.assertEqual(urls, {"https://example.com/docs"})
        self.assertEqual(titles, {"real source": "https://example.com/docs"})


class PlanRowsParser(unittest.TestCase):
    def test_reads_linked_and_unlinked_rows(self) -> None:
        text = (
            "| | Importance | Reading / tutorial |\n"
            "|---|---|---|\n"
            "| ✓ | ★★★★★ | [Thing](https://example.com/thing) "
            "— a thing |\n"
            "| ➕ | ★★ | Named source — no link this time |\n"
            "| ➕ | — | Close a gap — not a source at all |\n"
        )
        rows = plan_rows(text)
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            (rows[0].marker, rows[0].name, rows[0].url),
            ("✓", "Thing", "https://example.com/thing"),
        )
        self.assertEqual(
            (rows[1].marker, rows[1].name, rows[1].url), ("➕", "Named source", None)
        )
        self.assertEqual(
            (rows[2].marker, rows[2].name, rows[2].url), ("➕", "Close a gap", None)
        )

    def test_ignores_non_reading_rows(self) -> None:
        self.assertEqual(plan_rows("| ✅ | ♻️ | 🔷 | not a reading row |\n"), [])


class MarkerMismatches(unittest.TestCase):
    def test_flags_unregistered_marker_on_a_registered_link(self) -> None:
        rows = [PlanRow(10, UNREGISTERED, "Thing", "https://x.io/a")]
        problems = marker_mismatches(rows, {"https://x.io/a"}, {})
        self.assertEqual(len(problems), 1)
        self.assertIn("line 10", problems[0])

    def test_flags_registered_marker_on_an_unregistered_link(self) -> None:
        rows = [PlanRow(11, REGISTERED, "Thing", "https://x.io/b")]
        problems = marker_mismatches(rows, {"https://x.io/a"}, {})
        self.assertEqual(len(problems), 1)

    def test_flags_by_title_when_the_row_has_no_link(self) -> None:
        rows = [PlanRow(12, UNREGISTERED, "Agent SDK overview", None)]
        problems = marker_mismatches(
            rows,
            set(),
            {
                "agent sdk overview": "https://code.claude.com/docs/en/agent-sdk/overview"
            },
        )
        self.assertEqual(len(problems), 1)

    def test_skips_an_unlinked_row_with_no_title_match(self) -> None:
        rows = [PlanRow(13, UNREGISTERED, "Close a gap", None)]
        self.assertEqual(marker_mismatches(rows, set(), {}), [])

    def test_no_problem_when_marker_and_registration_agree(self) -> None:
        rows = [
            PlanRow(14, REGISTERED, "Thing", "https://x.io/a"),
            PlanRow(15, UNREGISTERED, "Other", "https://x.io/b"),
        ]
        self.assertEqual(marker_mismatches(rows, {"https://x.io/a"}, {}), [])


class DevelopmentPlanMarkers(unittest.TestCase):
    """The real plan against the real register."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.urls, cls.titles = registered_sources(SOURCES.read_text(encoding="utf-8"))
        cls.rows = plan_rows(PLAN.read_text(encoding="utf-8"))

    def test_sources_are_not_empty(self) -> None:
        # Guards the real-file test below: an empty source would make it vacuous.
        self.assertTrue(self.urls)
        self.assertTrue(self.rows)

    def test_every_marker_agrees_with_the_register(self) -> None:
        problems = marker_mismatches(self.rows, self.urls, self.titles)
        self.assertEqual(problems, [], "\n" + "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
