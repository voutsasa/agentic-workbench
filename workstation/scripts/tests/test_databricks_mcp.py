"""Unit tests for `databricks_mcp.py`.

Run from the repo root::

    python -m unittest discover -s workstation/scripts/tests -t workstation/scripts/tests
"""

from __future__ import annotations

import io
import json
import shlex
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import databricks_mcp
from databricks_mcp import (
    SERVICES,
    Workspace,
    claude_config,
    commands,
    main,
    parse_describe,
    resolve_workspace,
)

WS = Workspace("dbc-abc", "https://dbc-abc.cloud.databricks.com", "123")


def no_describe(profile: str) -> tuple[str, str]:
    raise AssertionError("describe must not run when host and workspace ID are given")


def run(argv: list[str], describe=no_describe) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv, describe=describe)
    return code, out.getvalue(), err.getvalue()


class ClaudeConfigTest(unittest.TestCase):
    def test_entry_is_http_with_helper_for_the_profile(self):
        config = claude_config(WS, "dbsql")
        self.assertEqual(config["type"], "http")
        self.assertEqual(
            config["url"],
            "https://dbc-abc.cloud.databricks.com/ai-gateway/mcp-services/system.ai.dbsql?o=123",
        )
        self.assertEqual(
            config["headersHelper"],
            "databricks auth token -p dbc-abc | jq -c "
            "'{Authorization: (\"Bearer \" + .access_token)}'",
        )

    def test_add_command_round_trips_through_the_shell(self):
        [argv] = commands(WS, ["genie_one_mcp"], ["claude"], "local")
        parsed = shlex.split(shlex.join(argv))
        self.assertEqual(parsed[:6], ["claude", "mcp", "add-json", "-s", "local",
                                      "databricks-genie_one_mcp"])  # fmt: skip
        self.assertEqual(json.loads(parsed[6]), claude_config(WS, "genie_one_mcp"))


class CopilotTest(unittest.TestCase):
    def test_add_is_a_ug_proxy_stdio_server(self):
        [argv] = commands(WS, ["web_search"], ["copilot"], "local")
        self.assertEqual(
            argv[:5], ["copilot", "mcp", "add", "databricks-web_search", "--"]
        )
        self.assertEqual(argv[5:7], ["ug", "mcp-proxy"])
        self.assertIn("--profile", argv)
        self.assertEqual(
            argv[argv.index("--url") + 1], databricks_mcp.service_url(WS, "web_search")
        )

    def test_remove(self):
        self.assertEqual(
            commands(WS, ["sandbox"], ["copilot"], "local", remove=True),
            [["copilot", "mcp", "remove", "databricks-sandbox"]],
        )


class MainTest(unittest.TestCase):
    def test_default_prints_every_service_for_both_clients(self):
        code, out, _ = run(
            ["--profile", "dbc-abc", "--host", WS.host, "--workspace-id", "123"]
        )
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(len(lines), 2 * len(SERVICES))
        self.assertEqual(
            sum(line.startswith("claude ") for line in lines), len(SERVICES)
        )
        self.assertEqual(
            sum(line.startswith("copilot ") for line in lines), len(SERVICES)
        )

    def test_filters_and_scope(self):
        code, out, _ = run([
            "--profile", "dbc-abc", "--host", WS.host, "--workspace-id", "123",
            "--client", "claude", "--service", "dbsql", "--claude-scope", "user", "--remove",
        ])  # fmt: skip
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "claude mcp remove databricks-dbsql -s user")

    def test_connection_backed_service_is_rejected(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["--profile", "p", "--service", "github"], describe=no_describe)

    def test_describe_fills_missing_values(self):
        code, out, _ = run(
            ["--profile", "dbc-abc"], describe=lambda p: (WS.host + "/", "123")
        )
        self.assertEqual(code, 0)
        self.assertIn("system.ai.genie_one_mcp?o=123", out)

    def test_unsafe_profile_is_refused(self):
        code, out, err = run(
            ["--profile", "x; rm -rf ~", "--host", WS.host, "--workspace-id", "1"]
        )
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("profile", err)


class ResolveTest(unittest.TestCase):
    def test_bad_host_and_id(self):
        with self.assertRaises(ValueError):
            resolve_workspace("p", "http://insecure.example", "1", no_describe)
        with self.assertRaises(ValueError):
            resolve_workspace("p", WS.host, "12a", no_describe)

    def test_parse_describe(self):
        output = json.dumps({
            "details": {
                "host": "https://h.cloud.databricks.com/",
                "configuration": {"workspace_id": {"value": "42"}},
            }
        })  # fmt: skip
        self.assertEqual(
            parse_describe(output), ("https://h.cloud.databricks.com", "42")
        )


if __name__ == "__main__":
    unittest.main()
