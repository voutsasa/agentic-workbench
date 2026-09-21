"""Unit tests for `inventory.py`.

Run from the repo root::

    python -m unittest discover -s workstation/scripts/tests -t workstation/scripts/tests
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import inventory
from inventory import (
    ABSENT,
    BLOCKED,
    ERROR,
    INSTALLED,
    Probe,
    Tool,
    discover_tools,
    extract_version,
    first_line,
    parse_frontmatter,
    probe_command,
    render_markdown,
    roll_up,
    suggested_id,
)


def completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    """A stand-in for `subprocess.run`'s return value."""
    return subprocess.CompletedProcess(
        args=["x"], returncode=returncode, stdout=stdout, stderr=stderr
    )


class ParseFrontmatterTests(unittest.TestCase):
    def test_reads_flat_pairs(self):
        text = (
            "---\ntool: magick\ncommand: magick\nproduct: ImageMagick\n---\n\n# body\n"
        )
        self.assertEqual(
            parse_frontmatter(text),
            {"tool": "magick", "command": "magick", "product": "ImageMagick"},
        )

    def test_no_frontmatter_returns_empty(self):
        self.assertEqual(parse_frontmatter("# just a heading\n"), {})

    def test_empty_file_returns_empty(self):
        self.assertEqual(parse_frontmatter(""), {})

    def test_stops_at_closing_fence(self):
        text = "---\ntool: a\n---\nprose: not frontmatter\n"
        self.assertEqual(parse_frontmatter(text), {"tool": "a"})

    def test_value_may_contain_colons(self):
        text = "---\nnote: see this: a caveat\n---\n"
        self.assertEqual(parse_frontmatter(text), {"note": "see this: a caveat"})


class DiscoverToolsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cli = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write(self, folder: str, frontmatter: str):
        directory = self.cli / folder
        directory.mkdir(parents=True)
        (directory / "install.md").write_text(
            f"---\n{frontmatter}\n---\n", encoding="utf-8"
        )

    def test_splits_multiple_commands(self):
        self.write(
            "dbml-cli", "command: dbml2sql, sql2dbml, db2dbml\nproduct: DBML CLI"
        )
        (tool,) = discover_tools(self.cli)
        self.assertEqual(tool.commands, ["dbml2sql", "sql2dbml", "db2dbml"])
        self.assertEqual(tool.product, "DBML CLI")

    def test_version_flag_defaults_and_overrides(self):
        self.write("pandoc", "command: pandoc\nproduct: Pandoc")
        self.write(
            "plantuml-cli",
            "command: plantuml\nproduct: PlantUML\nversion_flag: -version",
        )
        flags = {t.folder: t.version_flag for t in discover_tools(self.cli)}
        self.assertEqual(flags, {"pandoc": "--version", "plantuml-cli": "-version"})

    def test_skips_tool_with_no_command_field(self):
        self.write("broken", "product: Nothing")
        self.assertEqual(discover_tools(self.cli), [])

    def test_falls_back_to_folder_name_for_product(self):
        self.write("sem-cli", "command: sem")
        (tool,) = discover_tools(self.cli)
        self.assertEqual(tool.product, "sem-cli")

    def test_results_are_sorted_by_folder(self):
        self.write("zzz", "command: z")
        self.write("aaa", "command: a")
        self.assertEqual([t.folder for t in discover_tools(self.cli)], ["aaa", "zzz"])


class ExtractVersionTests(unittest.TestCase):
    def test_real_world_outputs(self):
        cases = {
            "pandoc 3.10.2": "3.10.2",
            "ImageMagick 7.1.2-29 Q16-HDRI aarch64": "7.1.2-29",
            "d2 0.8.1-HEAD": "0.8.1-HEAD",
            "PlantUML version 1.2026.6 (Sat Jun 20 2026)": "1.2026.6",
            "Docling version: 2.115.0": "2.115.0",
            "Version 5.5.3": "5.5.3",
        }
        for output, expected in cases.items():
            with self.subTest(output=output):
                self.assertEqual(extract_version(output), expected)

    def test_skips_leading_lines_without_a_version(self):
        self.assertEqual(
            extract_version("warning: something\n\npandoc 3.10.2\n"), "3.10.2"
        )

    def test_bare_integer_is_not_a_version(self):
        # A lone "5" is far more likely to be an exit code or a count than a
        # version, so a dotted number is required.
        self.assertEqual(extract_version("only 5 things happened"), "")

    def test_no_version_returns_empty(self):
        self.assertEqual(extract_version("command not recognised"), "")

    def test_trailing_punctuation_is_not_part_of_version(self):
        self.assertEqual(extract_version("Copilot CLI 1.0.87.\n"), "1.0.87")


class FirstLineTests(unittest.TestCase):
    def test_skips_blank_lines(self):
        self.assertEqual(first_line("\n\n  hello  \nworld\n"), "hello")

    def test_all_blank_returns_empty(self):
        self.assertEqual(first_line("\n \n"), "")


class ProbeCommandTests(unittest.TestCase):
    def test_absent_when_not_on_path(self):
        result = probe_command("nope", which=lambda _: None)
        self.assertEqual(result.status, ABSENT)
        self.assertEqual(result.path, "")
        self.assertEqual(result.detail, "not on PATH")

    def test_installed_captures_version_and_path(self):
        result = probe_command(
            "pandoc",
            which=lambda _: "/usr/bin/pandoc",
            run=lambda *a, **k: completed(stdout="pandoc 3.10.2\n"),
        )
        self.assertEqual(result.status, INSTALLED)
        self.assertEqual(result.version, "3.10.2")
        self.assertEqual(result.path, "/usr/bin/pandoc")

    def test_version_may_arrive_on_stderr(self):
        # Several tools print their version to stderr; that is not a failure.
        result = probe_command(
            "tool",
            which=lambda _: "/bin/tool",
            run=lambda *a, **k: completed(stderr="tool 1.2.3\n", returncode=1),
        )
        self.assertEqual(result.status, INSTALLED)
        self.assertEqual(result.version, "1.2.3")

    def test_permission_error_is_blocked_not_absent(self):
        # This is the docling case: on PATH, ACL says yes, launch still denied.
        def deny(*_args, **_kwargs):
            raise PermissionError(13, "Access is denied")

        result = probe_command("docling", which=lambda _: "/bin/docling", run=deny)
        self.assertEqual(result.status, BLOCKED)
        self.assertEqual(result.path, "/bin/docling")
        self.assertIn("PermissionError", result.detail)

    def test_other_oserror_is_blocked(self):
        def fail(*_args, **_kwargs):
            raise OSError("Exec format error")

        self.assertEqual(
            probe_command("x", which=lambda _: "/bin/x", run=fail).status, BLOCKED
        )

    def test_timeout_is_error(self):
        def hang(*_args, **_kwargs):
            raise subprocess.TimeoutExpired(cmd="x", timeout=60)

        result = probe_command("x", which=lambda _: "/bin/x", run=hang, timeout=60)
        self.assertEqual(result.status, ERROR)
        self.assertEqual(result.detail, "no response in 60s")

    def test_ran_but_no_version_is_error(self):
        result = probe_command(
            "x",
            which=lambda _: "/bin/x",
            run=lambda *a, **k: completed(stderr="unknown flag\n", returncode=2),
        )
        self.assertEqual(result.status, ERROR)
        self.assertEqual(result.detail, "unknown flag")

    def test_silent_nonzero_exit_reports_the_code(self):
        result = probe_command(
            "x",
            which=lambda _: "/bin/x",
            run=lambda *a, **k: completed(returncode=127),
        )
        self.assertEqual(result.status, ERROR)
        self.assertEqual(result.detail, "exit 127, no version output")

    def test_version_flag_is_passed_through(self):
        seen = {}

        def capture(argv, **_kwargs):
            seen["argv"] = argv
            return completed(stdout="PlantUML version 1.2026.6")

        probe_command(
            "plantuml", "-version", which=lambda _: "/bin/plantuml", run=capture
        )
        self.assertEqual(seen["argv"], ["/bin/plantuml", "-version"])


class RollUpTests(unittest.TestCase):
    def test_worst_status_wins(self):
        tool = Tool("dbml-cli", "DBML CLI", ["a", "b", "c"])
        probes = [
            Probe("a", INSTALLED, version="10.1.1"),
            Probe("b", ABSENT, detail="not on PATH"),
            Probe("c", INSTALLED, version="10.1.1"),
        ]
        result = roll_up(tool, probes)
        self.assertEqual(result.status, ABSENT)
        self.assertEqual(result.detail, "not on PATH")

    def test_blocked_outranks_error(self):
        tool = Tool("t", "T", ["a", "b"])
        result = roll_up(
            tool, [Probe("a", ERROR, detail="e"), Probe("b", BLOCKED, detail="denied")]
        )
        self.assertEqual(result.status, BLOCKED)

    def test_all_installed_keeps_version_and_drops_detail(self):
        tool = Tool("pandoc", "Pandoc", ["pandoc"])
        result = roll_up(
            tool, [Probe("pandoc", INSTALLED, version="3.10.2", detail="pandoc 3.10.2")]
        )
        self.assertEqual(result.status, INSTALLED)
        self.assertEqual(result.version, "3.10.2")
        self.assertEqual(result.detail, "")

    def test_version_is_kept_even_when_a_sibling_is_missing(self):
        tool = Tool("t", "T", ["a", "b"])
        result = roll_up(
            tool, [Probe("a", ABSENT), Probe("b", INSTALLED, version="2.0.0")]
        )
        self.assertEqual(result.version, "2.0.0")


class RenderMarkdownTests(unittest.TestCase):
    def setUp(self):
        self.facts = {
            "node": "HOST-1",
            "system": "Windows",
            "release": "10",
            "version": "10.0.26200",
            "machine": "AMD64",
            "python": "3.14.7",
        }

    def render(self, results):
        return render_markdown(results, self.facts)

    def test_counts_only_installed_as_usable(self):
        results = [
            roll_up(Tool("a", "A", ["a"]), [Probe("a", INSTALLED, version="1.0.0")]),
            roll_up(Tool("b", "B", ["b"]), [Probe("b", ABSENT, detail="not on PATH")]),
            roll_up(Tool("c", "C", ["c"]), [Probe("c", BLOCKED, detail="denied")]),
        ]
        self.assertIn("**1 of 3 usable.**", self.render(results))

    def test_records_the_host_it_probed(self):
        output = self.render(
            [roll_up(Tool("a", "A", ["a"]), [Probe("a", INSTALLED, version="1.0")])]
        )
        self.assertIn("HOST-1", output)
        self.assertIn("Python 3.14.7", output)

    def test_escapes_pipes_so_the_table_survives(self):
        results = [
            roll_up(Tool("a", "A", ["a"]), [Probe("a", ERROR, detail="use a | b")])
        ]
        row = next(
            line
            for line in self.render(results).splitlines()
            if line.startswith("| `a`")
        )
        self.assertIn(r"use a \| b", row)
        # 5 columns => 6 border pipes, plus the one escaped inside a cell.
        self.assertEqual(row.count("|"), 7)
        self.assertEqual(row.count(r"\|"), 1)

    def test_missing_values_render_as_dashes(self):
        results = [roll_up(Tool("a", "A", ["a"]), [Probe("a", ABSENT)])]
        self.assertIn("| absent | — | — |", self.render(results))

    def test_a_host_label_replaces_the_probed_name(self):
        """A machine file is committed under a chosen id, and a hostname can be
        a person's name. Everything else in the provenance line is unaffected."""
        results = [
            roll_up(Tool("a", "A", ["a"]), [Probe("a", INSTALLED, version="1.0")])
        ]
        output = render_markdown(results, self.facts, host="workstation")
        self.assertIn("Probed on `workstation`", output)
        self.assertNotIn("HOST-1", output)
        self.assertIn("Python 3.14.7", output)

    def test_no_host_label_keeps_the_probed_name(self):
        results = [
            roll_up(Tool("a", "A", ["a"]), [Probe("a", INSTALLED, version="1.0")])
        ]
        self.assertIn("Probed on `HOST-1`", render_markdown(results, self.facts))

    def test_multiple_commands_listed_in_one_cell(self):
        tool = Tool("dbml-cli", "DBML CLI", ["dbml2sql", "sql2dbml"])
        probes = [
            Probe("dbml2sql", INSTALLED, version="10.1.1"),
            Probe("sql2dbml", INSTALLED, version="10.1.1"),
        ]
        self.assertIn(
            "| `dbml2sql`, `sql2dbml` |", self.render([roll_up(tool, probes)])
        )


class SuggestedIdTests(unittest.TestCase):
    def test_windows(self):
        self.assertEqual(
            suggested_id({"system": "Windows", "node": "EMA-PF5N4XE7"}),
            "windows-ema-pf5n4xe7",
        )

    def test_darwin_becomes_macos(self):
        self.assertEqual(suggested_id({"system": "Darwin", "node": "MBP"}), "macos-mbp")

    def test_linux_passes_through(self):
        self.assertEqual(suggested_id({"system": "Linux", "node": "box"}), "linux-box")

    def test_an_fqdn_keeps_only_the_first_label(self):
        """macOS reports `host.local`; link_config.py matches on the short form,
        so an id carrying the domain names a file nothing looks for."""
        self.assertEqual(
            suggested_id({"system": "Darwin", "node": "MBP.local"}), "macos-mbp"
        )

    def test_a_multi_label_domain_is_dropped_too(self):
        self.assertEqual(
            suggested_id({"system": "Linux", "node": "box.eu.example.org"}), "linux-box"
        )


class RealCliDirTests(unittest.TestCase):
    """The repo's own `cli/` tree must stay parseable by this script."""

    def test_every_install_md_declares_a_command(self):
        cli_dir = Path(inventory.__file__).resolve().parents[1] / "cli"
        installs = sorted(cli_dir.glob("*/install.md"))
        self.assertTrue(installs, f"no install.md found under {cli_dir}")
        self.assertEqual(len(discover_tools(cli_dir)), len(installs))


if __name__ == "__main__":
    unittest.main()
