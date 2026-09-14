"""Tests that README.md's skill table matches the skills that actually exist.

A skill list in prose is not a claim verify_claims.py parses, so a skill that is
added, promoted or removed leaves the table stale and no gate notices. These
tests hold the table to the two authoritative sources: link_config.py's
``SKILLS`` tuple for the global skills, and the ``skills/<name>/SKILL.md``
folders for this repo's own.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import link_config as lc

REPO = Path(__file__).resolve().parents[3]
README = REPO / "README.md"
HEADING = "### Skills"

#: A skill row opens with a linked, code-formatted name and its scope:
#: ``| [`name`](path/SKILL.md) | global |``
ROW = re.compile(
    r"^\| \[`(?P<name>[a-z0-9-]+)`\]\((?P<path>[^)]+)\) \| (?P<scope>repo|global) \|"
)

EXPECTED_PATH = {
    "global": "workstation/agent/skills/{name}/SKILL.md",
    "repo": "skills/{name}/SKILL.md",
}


def skill_rows(text: str) -> dict[str, tuple[str, str]]:
    """Map each skill in the README's *Skills* section to its (scope, link path).

    Only rows between ``### Skills`` and the next ``## `` heading count, so a
    skill named in some other table cannot satisfy these tests.
    """
    if HEADING not in text:
        return {}
    section = text.split(HEADING, 1)[1].split("\n## ", 1)[0]
    rows = (ROW.match(line) for line in section.splitlines())
    return {m["name"]: (m["scope"], m["path"]) for m in rows if m}


def repo_skills() -> set[str]:
    """This repo's own skills: every ``skills/<name>/`` holding a SKILL.md."""
    return {p.parent.name for p in (REPO / "skills").glob("*/SKILL.md")}


class SkillRowsParser(unittest.TestCase):
    """The parser itself, so a broken regex cannot pass the table off as empty."""

    def test_reads_rows_inside_the_section_only(self) -> None:
        text = (
            "| [`outside`](skills/outside/SKILL.md) | repo | before the heading |\n"
            "### Skills\n\n| Skill | Scope | What it does |\n|---|---|---|\n"
            "| [`alpha`](skills/alpha/SKILL.md) | repo | does a thing |\n"
            "| [`beta`](workstation/agent/skills/beta/SKILL.md) | global | does another |\n"
            "\n## Layout\n"
            "| [`after`](skills/after/SKILL.md) | repo | after the section |\n"
        )
        self.assertEqual(
            skill_rows(text),
            {
                "alpha": ("repo", "skills/alpha/SKILL.md"),
                "beta": ("global", "workstation/agent/skills/beta/SKILL.md"),
            },
        )

    def test_missing_heading_yields_no_rows(self) -> None:
        self.assertEqual(skill_rows("# README\n"), {})


class ReadmeSkillTable(unittest.TestCase):
    """The real README against the real skill sources."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = skill_rows(README.read_text(encoding="utf-8"))

    def test_section_exists(self) -> None:
        self.assertIn(HEADING, README.read_text(encoding="utf-8"))

    def test_sources_are_not_empty(self) -> None:
        # Guards the comparisons below: an empty source would make them vacuous.
        self.assertTrue(lc.SKILLS)
        self.assertTrue(repo_skills())

    def test_every_global_skill_is_listed_as_global(self) -> None:
        for name in lc.SKILLS:
            with self.subTest(skill=name):
                self.assertIn(name, self.rows, "missing from README's skill table")
                self.assertEqual(self.rows[name][0], "global")

    def test_every_repo_skill_is_listed_as_repo(self) -> None:
        for name in sorted(repo_skills()):
            with self.subTest(skill=name):
                self.assertIn(name, self.rows, "missing from README's skill table")
                self.assertEqual(self.rows[name][0], "repo")

    def test_no_row_names_a_skill_that_does_not_exist(self) -> None:
        stale = set(self.rows) - set(lc.SKILLS) - repo_skills()
        self.assertEqual(stale, set(), "README lists skills that no source holds")

    def test_each_row_links_its_own_skill_file(self) -> None:
        for name, (scope, path) in self.rows.items():
            with self.subTest(skill=name):
                self.assertEqual(path, EXPECTED_PATH[scope].format(name=name))
                self.assertTrue((REPO / path).is_file(), f"{path} does not exist")


if __name__ == "__main__":
    unittest.main()
