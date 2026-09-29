#!/usr/bin/env python3
"""Print the commands that register Databricks MCP services with Claude Code and Copilot CLI.

Covers the currently available ``system.ai`` services that need nothing beyond
the Databricks CLI login. The script discovers those internal services through
the read-only Unity Catalog MCP-services API, then generates rather than copies
commands per service and per client. It also covers the managed ``/api/2.0/mcp/``
servers whose resource path the user names: Genie Agents (``--genie-space``), AI
Search indexes or schemas (``--ai-search``) and, only when asked, Databricks SQL
(``--sql``), which writes. These need no catalog query.

Writes nothing and registers nothing: registering an MCP server is the user's
step (``AGENTS.md`` § *The user installs; the agent records*). Unless
``--remove`` is passed, it runs the read-only ``databricks api get
.../unity-catalog/mcp-services...`` to discover the profile's current internal
services, and the read-only ``databricks auth describe`` to resolve the host
and workspace ID when they are not passed. Neither command registers or
changes anything.

Standard library only. Run from anywhere::

    python workstation/scripts/databricks_mcp.py --profile <profile>
    python workstation/scripts/databricks_mcp.py --profile <profile> --client copilot
    python workstation/scripts/databricks_mcp.py --profile <profile> --genie-space <id>
    python workstation/scripts/databricks_mcp.py --profile <profile> --remove --service <service>
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

CLIENTS = ("claude", "copilot")
CLAUDE_SCOPES = ("local", "user")
NAME_PREFIX = "databricks-"
MCP_SERVICES_PATH = (
    "/api/2.1/unity-catalog/mcp-services?parent=schemas/system.ai&view=BASIC"
)

# The profile and host are interpolated into a shell command (the Claude
# headersHelper), so only characters that cannot break out of it are accepted.
#: Matched with ``fullmatch``, not ``match``: ``$`` alone tolerates one trailing
#: ``\n``, which would otherwise let a profile or host slip past this check.
PROFILE_RE = re.compile(r"^[A-Za-z0-9._-]+$")
HOST_RE = re.compile(r"^https://[A-Za-z0-9.-]+$")
WORKSPACE_ID_RE = re.compile(r"^[0-9]+$")
SERVICE_RE = re.compile(r"^[A-Za-z0-9_]+$")
#: The REST API types a space ID as a UUID, so hyphens are allowed.
GENIE_SPACE_RE = re.compile(r"^[A-Za-z0-9-]+$")
#: ``catalog.schema`` or ``catalog.schema.index``; unquoted identifiers only.
AI_SEARCH_RE = re.compile(r"^[A-Za-z0-9_]+\.[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)?$")
SQL_WARNING = (
    "databricks-sql runs any SQL the agent writes, writes included, as the"
    " profile's identity; no service policy applies to it"
)

#: Shown under ``--help`` and by the ``setup-mcp-servers`` skill, which prints
#: this text rather than keeping its own copy.
PARAMETER_GUIDE = """\
Where each Databricks value comes from (every command below is read-only):

  --profile PROFILE
    The Databricks CLI profile holding your OAuth login. Required.
    Get it: databricks auth profiles
      Use a Name whose Valid column is YES.
    None yet, or Valid NO: databricks auth login --host <workspace-url>

  --host HOST
    The workspace URL, https://adb-<workspace-id>.<n>.azuredatabricks.net,
    with no trailing slash. Optional: read from the profile when omitted.
    Get it: databricks auth describe -p <profile> -o json
      Field details.host, or the browser's address bar in the workspace.

  --workspace-id WORKSPACE_ID
    The numeric workspace ID, sent as ?o=<id>. Optional, like --host.
    Get it: databricks auth describe -p <profile> -o json
      Field details.configuration.workspace_id.value. On Azure it is also
      the digits after adb- in the host.

  --service SERVICE
    A system.ai MCP Service, e.g. genie_one_mcp. Default: every internal
    one the workspace offers. Note that dbsql writes unless its policy
    sets disallow_writes.
    Get it: databricks api get '/api/2.1/unity-catalog/mcp-services?parent=schemas/system.ai&view=BASIC' -p <profile> -o json
      Names mcp-services/system.ai.<service> whose config has an internal
      key; or, in the workspace, AI Gateway > MCPs.

  --genie-space ID
    A Genie Agent's space ID. The space must be shared with you; the
    server is read-only.
    Get it: databricks genie list-spaces -p <profile> -o json
      Field spaces[].space_id, matched by spaces[].title. An empty list
      means no space is shared with this identity.

  --ai-search CATALOG.SCHEMA[.INDEX]
    An AI Search (Vector Search) index, or a schema for all its indexes.
    The index must use Databricks managed embeddings.
    Get it: databricks vector-search-endpoints list-endpoints -p <profile>
      then: databricks vector-search-indexes list-indexes <endpoint-name> -p <profile>
      Field vector_indexes[].name is catalog.schema.index; or Catalog
      Explorer > the index.

  --sql
    Databricks SQL. Takes no value, but the profile's identity needs a
    SQL warehouse it can use, and it writes: pick a profile that holds
    only USE CATALOG, USE SCHEMA and SELECT.
    Get it: databricks warehouses list -p <profile>
      Fields id, name and state; the server picks the warehouse itself.
"""


@dataclass(frozen=True)
class Workspace:
    profile: str
    host: str
    workspace_id: str


def server_name(service: str) -> str:
    return f"{NAME_PREFIX}{service}"


def service_url(ws: Workspace, service: str) -> str:
    return f"{ws.host}/ai-gateway/mcp-services/system.ai.{service}?o={ws.workspace_id}"


def managed_url(ws: Workspace, path: str) -> str:
    return f"{ws.host}/api/2.0/mcp/{path}"


def genie_server(space_id: str) -> tuple[str, str]:
    """Name and ``/api/2.0/mcp/`` path of a Genie Agent server."""
    if not GENIE_SPACE_RE.fullmatch(space_id):
        raise ValueError(
            f"genie-space {space_id!r}: use letters, digits and hyphens only"
        )
    return f"{NAME_PREFIX}genie-{space_id}", f"genie/{space_id}"


def ai_search_server(target: str) -> tuple[str, str]:
    """Name and path of an AI Search server for one index or a whole schema."""
    if not AI_SEARCH_RE.fullmatch(target):
        raise ValueError(
            f"ai-search {target!r}: expected catalog.schema or catalog.schema.index"
        )
    parts = target.split(".")
    return f"{NAME_PREFIX}ai-search-{'-'.join(parts)}", "ai-search/" + "/".join(parts)


SQL_SERVER = (f"{NAME_PREFIX}sql", "sql")


def headers_helper(profile: str) -> str:
    return (
        f"databricks auth token -p {profile}"
        " | jq -c '{Authorization: (\"Bearer \" + .access_token)}'"
    )


def http_entry(ws: Workspace, url: str) -> dict[str, str]:
    """The Claude Code server entry: native HTTP, token fetched per connection."""
    return {"type": "http", "url": url, "headersHelper": headers_helper(ws.profile)}


def claude_config(ws: Workspace, service: str) -> dict[str, str]:
    return http_entry(ws, service_url(ws, service))


def claude_add(ws: Workspace, name: str, url: str, scope: str) -> list[str]:
    config = json.dumps(http_entry(ws, url))
    return ["claude", "mcp", "add-json", "-s", scope, name, config]


def claude_remove(name: str, scope: str) -> list[str]:
    return ["claude", "mcp", "remove", name, "-s", scope]


def copilot_add(ws: Workspace, name: str, url: str) -> list[str]:
    """The Copilot CLI entry: a stdio bridge, since Copilot has no header helper."""
    return [
        "copilot", "mcp", "add", name, "--",
        "ug", "mcp-proxy",
        "--url", url,
        "--host", ws.host,
        "--profile", ws.profile,
    ]  # fmt: skip


def copilot_remove(name: str) -> list[str]:
    return ["copilot", "mcp", "remove", name]


def commands(
    ws: Workspace | None,
    services: Sequence[str],
    clients: Sequence[str],
    claude_scope: str,
    remove: bool = False,
    managed: Sequence[tuple[str, str]] = (),
) -> list[list[str]]:
    """Commands per client: ``system.ai`` services first, then managed servers.

    ``managed`` holds ``(name, path)`` pairs for paths under ``/api/2.0/mcp/``.
    """
    if ws is None and not remove:
        raise ValueError("a workspace is required to add MCP services")
    names = [server_name(service) for service in services]
    names += [name for name, _ in managed]
    urls: list[str] = []
    if ws is not None:
        urls = [service_url(ws, service) for service in services]
        urls += [managed_url(ws, path) for _, path in managed]

    out: list[list[str]] = []
    for client in clients:
        for i, name in enumerate(names):
            if remove:
                if client == "claude":
                    out.append(claude_remove(name, claude_scope))
                else:
                    out.append(copilot_remove(name))
            elif ws is not None:
                if client == "claude":
                    out.append(claude_add(ws, name, urls[i], claude_scope))
                else:
                    out.append(copilot_add(ws, name, urls[i]))
    return out


def describe_profile(profile: str) -> tuple[str, str]:
    """Host and workspace ID of a CLI profile, from ``databricks auth describe``."""
    result = subprocess.run(
        ["databricks", "auth", "describe", "-p", profile, "-o", "json"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            f"`databricks auth describe -p {profile}` failed: "
            f"{(result.stderr or result.stdout).strip()}"
        )
    return parse_describe(result.stdout)


def parse_describe(output: str) -> tuple[str, str]:
    details = json.loads(output).get("details", {})
    host = str(details.get("host", "")).rstrip("/")
    workspace_id = str(
        details.get("configuration", {}).get("workspace_id", {}).get("value", "")
    )
    return host, workspace_id


def parse_internal_services(output: str) -> tuple[str, ...]:
    """Internal ``system.ai`` services from a Unity Catalog API response."""
    try:
        response = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ValueError("MCP-services response was not valid JSON") from exc

    entries = response.get("mcp_services")
    if not isinstance(entries, list):
        raise TypeError("MCP-services response has no `mcp_services` list")

    prefix = "mcp-services/system.ai."
    services: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        config = entry.get("config")
        name = entry.get("name")
        if not isinstance(config, dict) or "internal" not in config:
            continue
        if not isinstance(name, str) or not name.startswith(prefix):
            continue
        service = name.removeprefix(prefix)
        if SERVICE_RE.fullmatch(service):
            services.append(service)

    return tuple(dict.fromkeys(services))


def discover_internal_services(profile: str) -> tuple[str, ...]:
    """Read the current internal service catalog for a Databricks CLI profile."""
    result = subprocess.run(
        [
            "databricks",
            "api",
            "get",
            MCP_SERVICES_PATH,
            "-p",
            profile,
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            "could not list internal MCP services: "
            f"{(result.stderr or result.stdout).strip()}"
        )
    services = parse_internal_services(result.stdout)
    if not services:
        raise ValueError(
            "the workspace has no internally backed system.ai MCP services"
        )
    return services


def resolve_workspace(
    profile: str,
    host: str | None,
    workspace_id: str | None,
    describe: Callable[[str], tuple[str, str]] = describe_profile,
) -> Workspace:
    if not PROFILE_RE.fullmatch(profile):
        raise ValueError(
            f"profile {profile!r}: use letters, digits, '.', '_' or '-' only"
        )
    if not host or not workspace_id:
        described_host, described_id = describe(profile)
        host = host or described_host
        workspace_id = workspace_id or described_id
    host = host.rstrip("/")
    if not HOST_RE.fullmatch(host):
        raise ValueError(f"host {host!r}: expected https://<workspace-hostname>")
    if not WORKSPACE_ID_RE.match(workspace_id):
        raise ValueError(f"workspace ID {workspace_id!r}: expected digits only")
    return Workspace(profile, host, workspace_id)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print Claude Code / Copilot CLI commands that register "
        "Databricks MCP servers. Runs none of them.",
        epilog=PARAMETER_GUIDE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--profile", required=True, help="Databricks CLI profile")
    parser.add_argument(
        "--host", help="workspace URL; default: from `databricks auth describe`"
    )
    parser.add_argument(
        "--workspace-id",
        help="numeric workspace ID; default: from `databricks auth describe`",
    )
    parser.add_argument(
        "--service",
        action="append",
        help="repeatable; additions must be currently internal system.ai services",
    )
    parser.add_argument(
        "--genie-space",
        action="append",
        metavar="ID",
        help="repeatable; a Genie Agent, /api/2.0/mcp/genie/<ID>",
    )
    parser.add_argument(
        "--ai-search",
        action="append",
        metavar="CATALOG.SCHEMA[.INDEX]",
        help="repeatable; one AI Search index, or every index in a schema",
    )
    parser.add_argument(
        "--sql",
        action="store_true",
        help="Databricks SQL, /api/2.0/mcp/sql; it writes, so never by default",
    )
    parser.add_argument(
        "--client", action="append", choices=CLIENTS, help="repeatable; default: both"
    )
    parser.add_argument(
        "--claude-scope", choices=CLAUDE_SCOPES, default="local", help="default: local"
    )
    parser.add_argument(
        "--remove", action="store_true", help="print the removal commands instead"
    )
    return parser


def main(
    argv: list[str] | None = None,
    describe: Callable[[str], tuple[str, str]] = describe_profile,
    discover: Callable[[str], tuple[str, ...]] = discover_internal_services,
) -> int:
    args = build_parser().parse_args(argv)

    try:
        if not PROFILE_RE.fullmatch(args.profile):
            raise ValueError(
                f"profile {args.profile!r}: use letters, digits, '.', '_' or '-' only"
            )
        requested = list(dict.fromkeys(args.service or []))
        managed = [genie_server(s) for s in dict.fromkeys(args.genie_space or [])]
        managed += [ai_search_server(t) for t in dict.fromkeys(args.ai_search or [])]
        if args.sql:
            managed.append(SQL_SERVER)
        if args.remove:
            if not requested and not managed:
                raise ValueError(
                    "--remove requires at least one --service, --genie-space,"
                    " --ai-search or --sql"
                )
            services = requested
            ws = None
        elif managed and not requested:
            services = []
            ws = resolve_workspace(args.profile, args.host, args.workspace_id, describe)
        else:
            available = discover(args.profile)
            services = requested or list(available)
            unavailable = sorted(set(services).difference(available))
            if unavailable:
                raise ValueError(
                    "service(s) unavailable as internal system.ai MCP services: "
                    + ", ".join(unavailable)
                )
            ws = resolve_workspace(args.profile, args.host, args.workspace_id, describe)
    except (TypeError, ValueError) as exc:
        print(f"databricks_mcp: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(
            f"databricks_mcp: could not run the `databricks` CLI: {exc}",
            file=sys.stderr,
        )
        return 2
    except subprocess.TimeoutExpired as exc:
        print(
            f"databricks_mcp: `databricks` CLI call timed out: {exc}", file=sys.stderr
        )
        return 2

    clients = list(dict.fromkeys(args.client or CLIENTS))
    assert ws is not None or args.remove
    if args.sql and not args.remove:
        print(f"databricks_mcp: warning: {SQL_WARNING}", file=sys.stderr)
    out = commands(ws, services, clients, args.claude_scope, args.remove, managed)
    for argv_out in out:
        print(shlex.join(argv_out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
