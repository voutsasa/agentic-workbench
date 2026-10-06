"""Regression tests for setup-mcp-servers discovery."""
# pyright: reportMissingImports=false

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import discover


class ParseServicesTest(unittest.TestCase):
    def test_returns_only_internal_system_ai_services(self) -> None:
        payload = {
            "mcp_services": [
                {
                    "name": "mcp-services/system.ai.genie_one_mcp",
                    "config": {"internal": {}},
                },
                {"name": "mcp-services/system.ai.github", "config": {}},
                {
                    "name": "mcp-services/other.ai.ignored",
                    "config": {"internal": {}},
                },
            ]
        }
        self.assertEqual(
            discover.parse_internal_services(json.dumps(payload)),
            ("genie_one_mcp",),
        )


class DiscoveryTest(unittest.TestCase):
    def test_machine_note_resolves_workbench_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            note = Path(temp) / "machine.md"
            note.write_text("---\nrepo: C:\\workbench\n---\n", encoding="utf-8")
            self.assertEqual(discover.machine_repo(note), Path("C:\\workbench"))

    def test_default_note_is_the_assistant_neutral_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            note = home / ".agentic-workbench" / "machine.md"
            note.parent.mkdir()
            note.write_text("repo: x\n", encoding="utf-8")
            (home / ".claude").mkdir()
            (home / ".claude" / "machine.md").write_text("repo: y\n", encoding="utf-8")
            self.assertEqual(discover.default_machine_note(home), note)

    def test_an_old_claude_note_is_never_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / ".claude").mkdir()
            (home / ".claude" / "machine.md").write_text("repo: y\n", encoding="utf-8")
            self.assertEqual(
                discover.default_machine_note(home),
                home / ".agentic-workbench" / "machine.md",
            )

    def test_discovery_does_not_query_databricks_without_a_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = root / "workstation" / "mcp"
            catalog.mkdir(parents=True)
            (catalog / ".mcp.json").write_text(
                '{"mcpServers":{"drawio-mcp":{},"ado-remote-mcp":{}}}',
                encoding="utf-8",
            )

            def forbidden(_: list[str]) -> str:
                raise AssertionError("Databricks query was not requested")

            result = discover.discover(root, databricks_profile=None, run=forbidden)
            self.assertEqual(
                result["servers"]["catalog"], ["ado-remote-mcp", "drawio-mcp"]
            )
            self.assertEqual(result["databricks"]["status"], "not_requested")


if __name__ == "__main__":
    unittest.main()
