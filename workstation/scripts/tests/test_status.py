"""Unit tests for workstation/scripts/status.py."""

from __future__ import annotations

import sys
import tempfile
import unittest
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

    def test_python_runtime_uses_active_interpreter_not_path(self) -> None:
        row = status.probe_prerequisite(
            {
                "id": "python",
                "product": "Python",
                "commands": ["python"],
                "probe": "python-runtime",
                "minimum_version": "3.14",
                "required": True,
                "provisioning": "external",
                "corrective_action": "upgrade",
            },
            timeout=1,
            runtime_version="3.14.7",
            runtime_path=r"C:\repo\.venv\Scripts\python.exe",
        )
        self.assertEqual(row.status, inventory.INSTALLED)
        self.assertEqual(row.version, "python 3.14.7")
        self.assertIn(".venv", row.evidence)


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
