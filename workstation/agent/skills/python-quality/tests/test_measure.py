"""
Unit tests for the threshold arithmetic and the output parsing.

Everything here works on fixtures rather than live tool runs: the point of the module is the
*decision* it makes from numbers, and that decision has to be checkable without a project, a
network, or a particular version of radon installed.

Standard library only, like the `review` and `verify-docs` suites — a skill's own tests must
run on a bare interpreter, before the project they are about to gate has been set up.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from measure import (
    Finding,
    at_the_gate,
    parse_coverage,
    parse_radon,
    parse_ruff,
    parse_ruff_complexity,
    propose_complexity,
    propose_coverage,
    python_requirement,
    report,
    venv_executable,
)

# ruff's own numbers from the project this skill came from. Note how much smaller they are than
# radon's for the same functions — radon scored `run_checks` 20 where ruff scores it 5.
REAL_SCORES = {
    "page_index": 7,
    "_subtree": 7,
    "_walk": 6,
    "run_checks": 5,
    "_check": 5,
    "space_checks": 4,
}


class TheThresholdRule(unittest.TestCase):
    def test_the_gate_is_the_tightest_value_that_is_green_today(self) -> None:
        """The rule the whole skill turns on: introduce a gate that passes, then ratchet it down."""

        self.assertEqual(propose_complexity(list(REAL_SCORES.values())), 7)

    def test_the_proposed_gate_fails_nothing_on_the_day_it_is_introduced(self) -> None:
        """A gate that opens red is a gate that gets switched off. C901 fails on > gate, not >=."""

        gate = propose_complexity(list(REAL_SCORES.values()))

        self.assertEqual(
            [name for name, score in REAL_SCORES.items() if score > gate], []
        )

    def test_a_project_with_no_branching_still_gets_a_usable_floor(self) -> None:
        self.assertEqual(propose_complexity([]), 5)

    def test_the_functions_at_the_gate_are_named_for_the_next_refactor(self) -> None:
        """These go in the config comment: one added branch to any of them turns the build red."""

        self.assertEqual(at_the_gate(REAL_SCORES, 7), ["_subtree", "page_index"])
        self.assertEqual(at_the_gate(REAL_SCORES, 8), [])


class TheCoverageFloor(unittest.TestCase):
    def test_the_floor_sits_under_what_the_project_achieves(self) -> None:
        self.assertEqual(propose_coverage(90), 85)

    def test_the_floor_never_exceeds_actual_coverage(self) -> None:
        """A floor above actual fails on the day it is introduced, which is how gates get disabled."""

        for actual in (0, 12, 55, 100):
            with self.subTest(actual=actual):
                self.assertLessEqual(propose_coverage(actual), actual)

    def test_the_floor_never_goes_negative(self) -> None:
        self.assertEqual(propose_coverage(2), 0)


class ParsingWhatTheToolsPrint(unittest.TestCase):
    def test_ruff_reports_its_own_complexity_which_is_what_c901_gates_on(self) -> None:
        """radon and ruff count differently, so a gate must be proposed from ruff's numbers."""

        output = (
            "src/pkg/a.py:104:5: C901 `page_index` is too complex (7 > 1)\n"
            "src/pkg/b.py:145:5: C901 `run_checks` is too complex (5 > 1)\n"
        )

        self.assertEqual(
            parse_ruff_complexity(output), {"page_index": 7, "run_checks": 5}
        )

    def test_a_clean_complexity_run_parses_to_nothing(self) -> None:
        self.assertEqual(parse_ruff_complexity("All checks passed!"), {})

    def test_radon_output_becomes_names_and_scores(self) -> None:
        output = """
src/pkg/checks.py
    F 144:0 run_checks - D (21)
    F 98:0 space_checks - C (12)
src/pkg/cli.py
    F 123:0 _check - C (14)
"""
        self.assertEqual(
            parse_radon(output), {"run_checks": 21, "space_checks": 12, "_check": 14}
        )

    def test_radon_output_with_nothing_above_grade_a_is_empty_not_an_error(
        self,
    ) -> None:
        self.assertEqual(
            parse_radon(
                "3 blocks (classes, functions, methods) analyzed.\nAverage complexity: A (2.1)"
            ),
            {},
        )

    def test_the_coverage_total_is_read_from_the_terminal_report(self) -> None:
        output = "src/pkg/a.py    45    5    89%\nTOTAL           808   85    89%\n"
        self.assertEqual(parse_coverage(output), 89)

    def test_a_run_without_coverage_reports_nothing_rather_than_guessing(self) -> None:
        self.assertIsNone(parse_coverage("12 passed in 0.4s"))

    def test_ruff_statistics_become_a_rule_census(self) -> None:
        output = (
            "6\tF401 \t[*] unused-import\n5\tD103 \t[ ] undocumented-public-function\n"
        )
        self.assertEqual(parse_ruff(output), {"F401": 6, "D103": 5})


class TheVersionAnythingParsingTheSourceMustMatch(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp_path = Path(directory.name)

    def test_the_target_python_is_read_from_the_project(self) -> None:
        """radon on an older interpreter skips files silently, so this drives `uvx --python`."""

        (self.tmp_path / "pyproject.toml").write_text(
            '[project]\nrequires-python = ">=3.14"\n', encoding="utf-8"
        )

        self.assertEqual(python_requirement(self.tmp_path), "3.14")

    def test_a_project_that_does_not_pin_python_returns_empty(self) -> None:
        for contents in ("", "[project]\nname = 'x'\n"):
            with self.subTest(contents=contents):
                (self.tmp_path / "pyproject.toml").write_text(
                    contents, encoding="utf-8"
                )

                self.assertEqual(python_requirement(self.tmp_path), "")

    def test_no_pyproject_at_all_is_not_a_crash(self) -> None:
        self.assertEqual(python_requirement(self.tmp_path), "")

    def test_venv_executables_follow_the_platform_layout(self) -> None:
        self.assertEqual(
            venv_executable(self.tmp_path, "python", "nt"),
            self.tmp_path / ".venv" / "Scripts" / "python.exe",
        )
        self.assertEqual(
            venv_executable(self.tmp_path, "pyright", "posix"),
            self.tmp_path / ".venv" / "bin" / "pyright",
        )


class TheReport(unittest.TestCase):
    def test_the_report_shows_absent_tools_without_pretending_they_passed(self) -> None:
        """Measuring must never silently skip a gate: an unavailable tool is a visible row."""

        text = report([Finding("ruff", False, "not installed — `uv add --dev ruff`")])

        self.assertIn("--    ruff", text)
        self.assertIn("not installed", text)

    def test_the_report_carries_the_proposal_next_to_the_measurement(self) -> None:
        text = report(
            [Finding("coverage", True, "90%", proposal="--cov-fail-under=85")]
        )

        self.assertIn("90%", text)
        self.assertIn("--cov-fail-under=85", text)


if __name__ == "__main__":
    unittest.main()
