"""Unit tests for `databricks_mcp.py`.

Run from the repo root::

    python -m unittest discover -s workstation/scripts/tests -t workstation/scripts/tests
"""

from __future__ import annotations

import io
import json
import shlex
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import databricks_mcp
from databricks_mcp import (
    Workspace,
    claude_config,
    commands,
    main,
    parse_describe,
    parse_internal_services,
    resolve_workspace,
)

WS = Workspace("dbc-abc", "https://dbc-abc.cloud.databricks.com", "123")


def no_describe(profile: str) -> tuple[str, str]:
    raise AssertionError("describe must not run when host and workspace ID are given")


def internal_services(profile: str) -> tuple[str, ...]:
    assert profile == "dbc-abc"
    return ("genie_one_mcp", "dbsql")


def run(
    argv: list[str],
    describe=no_describe,
    discover=internal_services,
) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv, describe=describe, discover=discover)
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
    def test_default_prints_every_available_service_for_both_clients(self):
        code, out, _ = run(
            ["--profile", "dbc-abc", "--host", WS.host, "--workspace-id", "123"]
        )
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(sum(line.startswith("claude ") for line in lines), 2)
        self.assertEqual(sum(line.startswith("copilot ") for line in lines), 2)

    def test_filters_and_scope(self):
        code, out, _ = run([
            "--profile", "dbc-abc", "--host", WS.host, "--workspace-id", "123",
            "--client", "claude", "--service", "dbsql", "--claude-scope", "user", "--remove",
        ])  # fmt: skip
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "claude mcp remove databricks-dbsql -s user")

    def test_unavailable_service_is_rejected(self):
        code, out, err = run(
            [
                "--profile",
                "dbc-abc",
                "--host",
                WS.host,
                "--workspace-id",
                "123",
                "--service",
                "github",
            ]
        )
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("unavailable", err)

    def test_remove_requires_explicit_service_without_discovery(self):
        code, out, err = run(
            ["--profile", "dbc-abc", "--remove"],
            discover=lambda _: (_ for _ in ()).throw(AssertionError("unexpected")),
        )
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("--remove requires", err)

    def test_remove_allows_a_service_no_longer_in_the_catalog(self):
        code, out, _ = run(
            [
                "--profile",
                "dbc-abc",
                "--remove",
                "--client",
                "copilot",
                "--service",
                "dbsql",
            ],
            discover=lambda _: (_ for _ in ()).throw(AssertionError("unexpected")),
        )
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "copilot mcp remove databricks-dbsql")

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

    def test_profile_with_trailing_newline_is_refused(self):
        code, out, err = run(
            ["--profile", "dbc-abc\n", "--host", WS.host, "--workspace-id", "123"]
        )
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("profile", err)

    def test_missing_databricks_cli_is_reported_not_raised(self):
        def discover_missing_cli(_profile: str) -> tuple[str, ...]:
            raise FileNotFoundError("databricks")

        code, out, err = run(
            ["--profile", "dbc-abc", "--host", WS.host, "--workspace-id", "123"],
            discover=discover_missing_cli,
        )
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("databricks", err)

    def test_discovery_timeout_is_reported_not_raised(self):
        def discover_timeout(_profile: str) -> tuple[str, ...]:
            raise subprocess.TimeoutExpired(cmd="databricks", timeout=60)

        code, out, err = run(
            ["--profile", "dbc-abc", "--host", WS.host, "--workspace-id", "123"],
            discover=discover_timeout,
        )
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("timed out", err.lower())


def no_discover(_profile: str) -> tuple[str, ...]:
    raise AssertionError("the system.ai catalog must not be read for managed servers")


ADD = ["--profile", "dbc-abc", "--host", WS.host, "--workspace-id", "123"]


class ManagedServerTest(unittest.TestCase):
    def test_genie_space_prints_both_clients_without_discovery(self):
        code, out, _ = run([*ADD, "--genie-space", "01ef"], discover=no_discover)
        self.assertEqual(code, 0)
        claude, copilot = (shlex.split(line) for line in out.splitlines())
        self.assertEqual(claude[5], "databricks-genie-01ef")
        entry = json.loads(claude[6])
        self.assertEqual(entry["url"], WS.host + "/api/2.0/mcp/genie/01ef")
        self.assertEqual(
            entry["headersHelper"], claude_config(WS, "x")["headersHelper"]
        )
        self.assertEqual(copilot[3], "databricks-genie-01ef")
        self.assertEqual(
            copilot[copilot.index("--url") + 1], WS.host + "/api/2.0/mcp/genie/01ef"
        )

    def test_ai_search_index_and_schema(self):
        code, out, _ = run(
            [*ADD, "--client", "claude", "--ai-search", "main.docs.chunks",
             "--ai-search", "main.docs"],
            discover=no_discover,
        )  # fmt: skip
        self.assertEqual(code, 0)
        index, schema = (shlex.split(line) for line in out.splitlines())
        self.assertEqual(index[5], "databricks-ai-search-main-docs-chunks")
        self.assertEqual(
            json.loads(index[6])["url"],
            WS.host + "/api/2.0/mcp/ai-search/main/docs/chunks",
        )
        self.assertEqual(schema[5], "databricks-ai-search-main-docs")
        self.assertEqual(
            json.loads(schema[6])["url"], WS.host + "/api/2.0/mcp/ai-search/main/docs"
        )

    def test_sql_is_opt_in_and_warns_that_it_writes(self):
        code, out, err = run(
            [*ADD, "--client", "copilot", "--sql"], discover=no_discover
        )
        self.assertEqual(code, 0)
        argv = shlex.split(out)
        self.assertEqual(argv[3], "databricks-sql")
        self.assertEqual(argv[argv.index("--url") + 1], WS.host + "/api/2.0/mcp/sql")
        self.assertIn("writes", err)

    def test_default_run_registers_no_managed_server(self):
        _, out, _ = run(ADD)
        self.assertNotIn("/api/2.0/mcp/", out)

    def test_services_and_managed_servers_combine(self):
        code, out, _ = run(
            [*ADD, "--client", "claude", "--service", "genie_one_mcp",
             "--genie-space", "01ef"]
        )  # fmt: skip
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 2)

    def test_remove_managed_servers_needs_no_workspace(self):
        code, out, _ = run(
            ["--profile", "dbc-abc", "--remove", "--client", "copilot",
             "--genie-space", "01ef", "--ai-search", "main.docs", "--sql"],
            describe=no_describe, discover=no_discover,
        )  # fmt: skip
        self.assertEqual(code, 0)
        self.assertEqual(
            out.splitlines(),
            [
                "copilot mcp remove databricks-genie-01ef",
                "copilot mcp remove databricks-ai-search-main-docs",
                "copilot mcp remove databricks-sql",
            ],
        )

    def test_uuid_genie_space_is_accepted(self):
        space = "01ef2b3c-4d5e-6f70-8192-a3b4c5d6e7f8"
        code, out, _ = run(
            [*ADD, "--client", "copilot", "--genie-space", space], discover=no_discover
        )
        self.assertEqual(code, 0)
        self.assertIn(f"/api/2.0/mcp/genie/{space}", out)

    def test_unsafe_ids_are_refused(self):
        for flag, value in [
            ("--genie-space", "01ef; rm -rf ~"),
            ("--genie-space", "01ef\n"),
            ("--ai-search", "main"),
            ("--ai-search", "a.b.c.d"),
            ("--ai-search", "main.do$cs"),
        ]:
            with self.subTest(flag=flag, value=value):
                code, out, err = run([*ADD, flag, value], discover=no_discover)
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn(flag.removeprefix("--"), err)


class HelpTest(unittest.TestCase):
    def help_text(self) -> str:
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as exit_:
            main(["--help"], describe=no_describe, discover=no_discover)
        self.assertEqual(exit_.exception.code, 0)
        return out.getvalue()

    def test_help_explains_where_every_databricks_value_comes_from(self):
        guide = databricks_mcp.PARAMETER_GUIDE
        self.assertIn(guide, self.help_text())
        for flag, lookup in [
            ("--profile", "databricks auth profiles"),
            ("--host", "details.host"),
            ("--workspace-id", "workspace_id"),
            ("--service", "AI Gateway > MCPs"),
            ("--genie-space", "databricks genie list-spaces"),
            ("--ai-search", "databricks vector-search-indexes list-indexes"),
            ("--sql", "databricks warehouses list"),
        ]:
            with self.subTest(flag=flag):
                [section] = [
                    block
                    for block in guide.split("\n\n")
                    if block.startswith("  --") and block.split()[0] == flag
                ]
                self.assertIn(lookup, section)

    def test_guide_keeps_its_line_breaks(self):
        self.assertIn("\n  --genie-space ID\n", self.help_text())


class ResolveTest(unittest.TestCase):
    def test_bad_host_and_id(self):
        with self.assertRaises(ValueError):
            resolve_workspace("p", "http://insecure.example", "1", no_describe)
        with self.assertRaises(ValueError):
            resolve_workspace("p", WS.host, "12a", no_describe)

    def test_profile_with_trailing_newline_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_workspace("dbc-abc\n", WS.host, "123", no_describe)

    def test_host_with_trailing_newline_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_workspace("dbc-abc", WS.host + "\n", "123", no_describe)

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


class CatalogTest(unittest.TestCase):
    def test_only_internal_system_ai_services_are_returned(self):
        response = {
            "mcp_services": [
                {
                    "name": "mcp-services/system.ai.genie_one_mcp",
                    "config": {"internal": {}},
                },
                {
                    "name": "mcp-services/system.ai.github",
                    "config": {},
                },
                {
                    "name": "mcp-services/other.ai.ignored",
                    "config": {"internal": {}},
                },
            ]
        }
        self.assertEqual(
            parse_internal_services(json.dumps(response)), ("genie_one_mcp",)
        )

    def test_missing_catalog_list_is_rejected(self):
        with self.assertRaisesRegex(TypeError, "mcp_services"):
            parse_internal_services("{}")


if __name__ == "__main__":
    unittest.main()
