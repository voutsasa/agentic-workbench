"""Unit tests for workstation/scripts/status.py."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import inventory
import status


class VersionTests(unittest.TestCase):
    def test_compares_versions_numerically(self) -> None:
        self.assertTrue(status.meets_minimum("3.14.1", "3.14"))
        self.assertFalse(status.meets_minimum("3.9.20", "3.14"))

    def test_ignores_non_numeric_suffixes(self) -> None:
        self.assertTrue(status.meets_minimum("20.1.0-rc1", "20.1"))


class ProfileTests(unittest.TestCase):
    def test_companion_file_replaces_only_suffix(self) -> None:
        note = Path("workstation/machines/windows-box.md")
        self.assertEqual(
            status.prerequisite_file(note),
            Path("workstation/machines/windows-box.prerequisites.toml"),
        )

    def test_rejects_empty_dependency_list(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.toml"
            path.write_text("schema_version = 1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no .* entries"):
                status.load_toml(path, "dependencies")

    def test_machine_overrides_replace_only_named_values(self) -> None:
        common = {
            "dependencies": [
                {
                    "id": "python",
                    "product": "Python",
                    "commands": ["python3"],
                    "minimum_version": "3.14",
                },
                {
                    "id": "package-manager",
                    "product": "Platform package manager",
                    "commands": [],
                },
            ]
        }
        profile = {
            "overrides": {
                "python": {"commands": ["python"]},
                "package-manager": {"product": "Scoop", "commands": ["scoop"]},
            }
        }
        merged = status.merge_dependencies(common, profile)
        self.assertEqual(merged[0]["commands"], ["python"])
        self.assertEqual(merged[0]["minimum_version"], "3.14")
        self.assertEqual(merged[1]["product"], "Scoop")

    def test_unknown_override_is_rejected(self) -> None:
        common = {"dependencies": [{"id": "python"}]}
        with self.assertRaisesRegex(ValueError, "unknown dependency"):
            status.merge_dependencies(common, {"overrides": {"node": {}}})


PYTHON_RUNTIME = {
    "id": "python",
    "product": "Python",
    "commands": ["python"],
    "probe": "python-runtime",
    "minimum_version": "3.14",
    "required": True,
    "provisioning": "external",
    "corrective_action": "upgrade",
}


class PrerequisiteProbeTests(unittest.TestCase):
    @mock.patch("status.inventory.probe_command")
    def test_any_mode_accepts_one_installed_assistant(self, probe: mock.Mock) -> None:
        probe.side_effect = [
            inventory.Probe("claude", inventory.ABSENT),
            inventory.Probe("copilot", inventory.INSTALLED, version="1.0.86"),
        ]
        row = status.probe_prerequisite(
            {
                "id": "assistant",
                "product": "AI assistant",
                "commands": ["claude", "copilot"],
                "mode": "any",
                "required": True,
                "provisioning": "external",
                "corrective_action": "install one",
            },
            timeout=1,
        )
        self.assertEqual(row.status, inventory.INSTALLED)
        self.assertEqual(row.version, "copilot 1.0.86")

    @mock.patch("status.inventory.probe_command")
    def test_version_below_floor_is_outdated(self, probe: mock.Mock) -> None:
        probe.return_value = inventory.Probe(
            "python", inventory.INSTALLED, version="3.13.9"
        )
        row = status.probe_prerequisite(
            {
                "id": "python",
                "product": "Python",
                "commands": ["python"],
                "minimum_version": "3.14",
                "required": True,
                "provisioning": "external",
                "corrective_action": "upgrade",
            },
            timeout=1,
        )
        self.assertEqual(row.status, "outdated")
        self.assertEqual(row.corrective_action, "upgrade")

    @mock.patch("status.inventory.probe_command")
    def test_python_runtime_with_venv_reports_running_interpreter(
        self, probe: mock.Mock
    ) -> None:
        row = status.probe_prerequisite(
            PYTHON_RUNTIME,
            timeout=1,
            runtime_version="3.14.7",
            runtime_path=r"C:\repo\.venv\Scripts\python.exe",
            venv=True,
        )
        probe.assert_not_called()
        self.assertEqual(row.status, inventory.INSTALLED)
        self.assertEqual(row.version, "python 3.14.7")
        self.assertIn(r"running interpreter C:\repo\.venv", row.evidence)

    @mock.patch("status.inventory.probe_command")
    def test_python_runtime_without_venv_probes_path(self, probe: mock.Mock) -> None:
        probe.return_value = inventory.Probe(
            "python",
            inventory.INSTALLED,
            version="3.12.4",
            path="/usr/bin/python",
            detail="Python 3.12.4",
        )
        row = status.probe_prerequisite(
            PYTHON_RUNTIME,
            timeout=1,
            runtime_version="3.14.7",
            runtime_path="/repo/.venv/bin/python",
            venv=False,
        )
        probe.assert_called_once_with("python", "--version", timeout=1)
        self.assertEqual(row.version, "python 3.12.4")
        self.assertEqual(row.status, "outdated")
        self.assertNotIn(".venv", row.evidence)

    @mock.patch("status.inventory.probe_command")
    def test_python_runtime_without_venv_reports_absent_command(
        self, probe: mock.Mock
    ) -> None:
        probe.return_value = inventory.Probe(
            "python", inventory.ABSENT, detail="not on PATH"
        )
        row = status.probe_prerequisite(PYTHON_RUNTIME, timeout=1, venv=False)
        self.assertEqual(row.status, "absent")

    @mock.patch("status.inventory.probe_all_versions")
    def test_all_versions_labels_the_active_one_and_sorts_the_rest(
        self, probe_all: mock.Mock
    ) -> None:
        probe_all.return_value = [
            inventory.Probe("python", inventory.INSTALLED, version="3.12.10"),
            inventory.Probe("python", inventory.INSTALLED, version="3.14.7"),
            inventory.Probe("python", inventory.INSTALLED, version="3.13.15"),
        ]
        row = status.probe_prerequisite(
            {**PYTHON_RUNTIME, "all_versions": True},
            timeout=1,
            runtime_version="3.14.7",
            runtime_path=r"C:\repo\.venv\Scripts\python.exe",
            venv=True,
        )
        self.assertEqual(row.version, "3.14.7 (active), 3.13.15, 3.12.10")
        probe_all.assert_called_once_with("python", timeout=1)

    @mock.patch("status.inventory.probe_all_versions")
    def test_all_versions_without_the_flag_is_not_probed(
        self, probe_all: mock.Mock
    ) -> None:
        status.probe_prerequisite(
            PYTHON_RUNTIME,
            timeout=1,
            runtime_version="3.14.7",
            runtime_path=r"C:\repo\.venv\Scripts\python.exe",
            venv=True,
        )
        probe_all.assert_not_called()

    @mock.patch("status.inventory.probe_all_versions")
    def test_no_extra_versions_found_keeps_the_single_version(
        self, probe_all: mock.Mock
    ) -> None:
        probe_all.return_value = []
        row = status.probe_prerequisite(
            {**PYTHON_RUNTIME, "all_versions": True},
            timeout=1,
            runtime_version="3.14.7",
            runtime_path=r"C:\repo\.venv\Scripts\python.exe",
            venv=True,
        )
        self.assertEqual(row.version, "python 3.14.7")


class CollectVenvTests(unittest.TestCase):
    """`collect` decides from the repo whether a .venv exists."""

    def run_collect(self, repo: Path) -> mock.Mock:
        common = {"dependencies": [{"id": "python"}]}
        profile = {"machine": "m", "platform": "macOS"}
        with (
            mock.patch("status.link_config.machine_file", return_value=repo / "m.md"),
            mock.patch("status.load_toml", side_effect=[common, profile]),
            mock.patch("status.inventory.run_inventory", return_value=[]),
            mock.patch("status.inventory.discover_tools", return_value=[]),
            mock.patch("status.probe_prerequisite") as probe,
        ):
            probe.return_value = status.StatusRow(
                "Python", "", "installed", "", "", "—", True, "external"
            )
            status.collect(repo)
        return probe

    def test_repo_with_venv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".venv").mkdir()
            probe = self.run_collect(repo)
        self.assertIs(probe.call_args.kwargs["venv"], True)

    def test_repo_without_venv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            probe = self.run_collect(Path(directory))
        self.assertIs(probe.call_args.kwargs["venv"], False)


class ProgressTests(unittest.TestCase):
    """`collect(progress=True)` prints one counted line per dependency and tool."""

    def run_collect(self, repo: Path, progress: bool) -> str:
        common = {
            "dependencies": [
                {"id": "a", "product": "A"},
                {"id": "b", "product": "B"},
            ]
        }
        profile = {"machine": "m", "platform": "macOS"}
        tool = inventory.Tool("pandoc", "Pandoc", ["pandoc"])
        with (
            mock.patch("status.link_config.machine_file", return_value=repo / "m.md"),
            mock.patch("status.load_toml", side_effect=[common, profile]),
            mock.patch("status.inventory.discover_tools", return_value=[tool]),
            mock.patch("status.inventory.probe_command") as probe_command,
            mock.patch("status.probe_prerequisite") as probe,
            mock.patch("status.tool_row") as tool_row,
            contextlib.redirect_stderr(io.StringIO()) as err,
        ):
            probe_command.return_value = inventory.Probe(
                "pandoc", inventory.INSTALLED, version="3.10.2"
            )
            probe.return_value = status.StatusRow(
                "A", "", "installed", "", "", "—", True, "external"
            )
            tool_row.return_value = status.StatusRow(
                "Pandoc", "", "installed", "", "", "—", False, "workbench"
            )
            status.collect(repo, progress=progress)
        return err.getvalue()

    def test_progress_true_prints_one_counted_line_per_item(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = self.run_collect(Path(directory), progress=True)
        self.assertEqual(
            output.splitlines(),
            [
                "[1/3] Probing A...",
                "[2/3] Probing B...",
                "[3/3] Probing Pandoc...",
            ],
        )

    def test_progress_false_prints_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = self.run_collect(Path(directory), progress=False)
        self.assertEqual(output, "")


class CorrectiveActionTests(unittest.TestCase):
    def test_reads_platform_command_from_install_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "install.md"
            path.write_text(
                "| Platform | Command |\n|---|---|\n"
                "| macOS | `brew install x` |\n"
                "| Windows | `scoop install x` |\n",
                encoding="utf-8",
            )
            self.assertEqual(
                status.platform_install_command(path, "Windows"),
                "scoop install x",
            )

    def tool_row_for(self, frontmatter: str) -> status.StatusRow:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            cli_dir = repo / "workstation" / "cli"
            (cli_dir / "x").mkdir(parents=True)
            (cli_dir / "x" / "install.md").write_text(
                f"---\ntool: x\n{frontmatter}---\n", encoding="utf-8"
            )
            result = inventory.ToolResult("x", "X", inventory.INSTALLED, "1.0")
            return status.tool_row(result, repo, cli_dir, "macOS")

    def test_tool_row_names_the_skills_that_use_it(self) -> None:
        row = self.tool_row_for("used_by: fetch-to-markdown, pdf-deliverable\n")
        self.assertEqual(
            row.requirement, "workstation tool for fetch-to-markdown, pdf-deliverable"
        )

    def test_tool_row_without_used_by_is_plain(self) -> None:
        self.assertEqual(self.tool_row_for("").requirement, "workstation tool")

    def test_every_used_by_names_a_real_skill(self) -> None:
        repo = Path(__file__).resolve().parents[3]
        skill_dirs = (repo / "skills", repo / "workstation" / "agent" / "skills")
        for install in sorted((repo / "workstation" / "cli").glob("*/install.md")):
            for skill in status.used_by(install):
                with self.subTest(install=install.parent.name, skill=skill):
                    self.assertTrue(
                        any((d / skill / "SKILL.md").is_file() for d in skill_dirs)
                    )

    def test_required_failure_makes_machine_not_ready(self) -> None:
        rows = [
            status.StatusRow(
                "Python", ">= 3.14", "absent", "—", "", "install", True, "external"
            )
        ]
        self.assertEqual(status.overall_status(rows), "NOT READY")

    def test_optional_failure_keeps_machine_ready_with_actions(self) -> None:
        rows = [
            status.StatusRow(
                "Typst", "optional", "absent", "—", "", "install", False, "workbench"
            )
        ]
        self.assertEqual(status.overall_status(rows), "READY WITH ACTIONS")

    def test_render_does_not_repeat_optional(self) -> None:
        row = status.StatusRow(
            "Typst",
            "workstation tool",
            "absent",
            "—",
            "",
            "install",
            False,
            "workbench",
        )
        report = {
            "overall": "READY WITH ACTIONS",
            "profile": "profile.toml",
            "dependencies": "dependencies.toml",
            "prerequisites": [],
            "tools": [row.__dict__],
        }
        rendered = status.render(report)
        self.assertIn("workstation tool (optional)", rendered)
        self.assertNotIn("optional workstation tool (optional)", rendered)


class RenderCsvTests(unittest.TestCase):
    def test_header_and_row_match_the_markdown_columns(self) -> None:
        row = status.StatusRow(
            "Typst",
            "workstation tool, has a comma",
            "absent",
            "—",
            "note",
            "install",
            False,
            "workbench",
        )
        report = {
            "overall": "READY WITH ACTIONS",
            "profile": "profile.toml",
            "dependencies": "dependencies.toml",
            "prerequisites": [],
            "tools": [row.__dict__],
        }
        lines = status.render_csv(report).splitlines()
        self.assertEqual(
            lines[0],
            "Capability,Requirement,Status,Version,Evidence,Corrective action",
        )
        self.assertIn('"workstation tool, has a comma (optional)"', lines[1])


class ReportFilenameTests(unittest.TestCase):
    def test_includes_machine_user_timestamp_and_active_format(self) -> None:
        timestamp = datetime(2026, 9, 22, 14, 5, 9).astimezone()
        self.assertEqual(
            status.report_filename("md", "windows-box", "alice", timestamp),
            f"status-windows-box-alice-{timestamp:%Y%m%dT%H%M%S%z}.md",
        )
        self.assertEqual(
            status.report_filename("json", "windows-box", "alice", timestamp),
            f"status-windows-box-alice-{timestamp:%Y%m%dT%H%M%S%z}.json",
        )
        self.assertEqual(
            status.report_filename("csv", "windows-box", "alice", timestamp),
            f"status-windows-box-alice-{timestamp:%Y%m%dT%H%M%S%z}.csv",
        )

    def test_replaces_filename_unsafe_machine_and_user_characters(self) -> None:
        self.assertEqual(
            status.report_filename(
                "md",
                "windows / box",
                "alice@example.com",
                datetime(2026, 9, 22, tzinfo=UTC),
            ),
            "status-windows-box-alice-example.com-20260922T000000+0000.md",
        )


class MainPersistTests(unittest.TestCase):
    def test_persist_writes_the_rendered_report_and_prints_its_path(self) -> None:
        report = {
            "machine": "m",
            "overall": "READY",
            "profile": "profile.toml",
            "dependencies": "dependencies.toml",
            "prerequisites": [],
            "tools": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            with (
                mock.patch("status.collect", return_value=report),
                contextlib.redirect_stdout(io.StringIO()) as out,
            ):
                exit_code = status.main(["--repo", str(repo), "--persist"])
            written = next(repo.glob("status-m-*-*.md"))
            self.assertEqual(exit_code, 0)
            self.assertTrue(written.is_file())
            self.assertIn(f"Report written to {written}", out.getvalue())

    def test_without_persist_writes_nothing(self) -> None:
        report = {
            "machine": "m",
            "overall": "READY",
            "profile": "profile.toml",
            "dependencies": "dependencies.toml",
            "prerequisites": [],
            "tools": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            with (
                mock.patch("status.collect", return_value=report),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                status.main(["--repo", str(repo)])
            self.assertEqual(list(repo.glob("status-*-*-*")), [])

    def test_persist_csv_writes_a_csv_report(self) -> None:
        report = {
            "machine": "m",
            "overall": "READY",
            "profile": "profile.toml",
            "dependencies": "dependencies.toml",
            "prerequisites": [],
            "tools": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            with (
                mock.patch("status.collect", return_value=report),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                exit_code = status.main(["--repo", str(repo), "--persist", "--csv"])
            written = next(repo.glob("status-m-*-*.csv"))
            self.assertEqual(exit_code, 0)
            self.assertEqual(
                written.read_text(encoding="utf-8"),
                "Capability,Requirement,Status,Version,Evidence,Corrective action\n",
            )


class MainQuietTests(unittest.TestCase):
    def run_main(self, argv: list[str]) -> mock.Mock:
        report = {
            "overall": "READY",
            "profile": "profile.toml",
            "dependencies": "dependencies.toml",
            "prerequisites": [],
            "tools": [],
        }
        with (
            mock.patch("status.collect", return_value=report) as collect,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            status.main(argv)
        return collect

    def test_progress_is_on_by_default(self) -> None:
        collect = self.run_main(["--repo", "."])
        self.assertIs(collect.call_args.kwargs["progress"], True)

    def test_quiet_turns_progress_off(self) -> None:
        collect = self.run_main(["--repo", ".", "--quiet"])
        self.assertIs(collect.call_args.kwargs["progress"], False)
