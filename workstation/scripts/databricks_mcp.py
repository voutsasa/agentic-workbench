#!/usr/bin/env python3
"""Print the commands that register Databricks MCP services with Claude Code and Copilot CLI.

Covers the currently available ``system.ai`` services that need nothing beyond
the Databricks CLI login. The script discovers those internal services through
the read-only Unity Catalog MCP-services API, then generates rather than copies
commands per service and per client.

Writes nothing and registers nothing: registering an MCP server is the user's
step (``AGENTS.md`` § *The user installs; the agent records*). The one command
it may run is the read-only ``databricks auth describe``, to resolve the host
and workspace ID when they are not passed.

Standard library only. Run from anywhere::

    python workstation/scripts/databricks_mcp.py --profile <profile>
    python workstation/scripts/databricks_mcp.py --profile <profile> --client copilot
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
PROFILE_RE = re.compile(r"^[A-Za-z0-9._-]+$")
HOST_RE = re.compile(r"^https://[A-Za-z0-9.-]+$")
WORKSPACE_ID_RE = re.compile(r"^[0-9]+$")
SERVICE_RE = re.compile(r"^[A-Za-z0-9_]+$")


@dataclass(frozen=True)
class Workspace:
    profile: str
    host: str
    workspace_id: str


def server_name(service: str) -> str:
    return f"{NAME_PREFIX}{service}"


def service_url(ws: Workspace, service: str) -> str:
    return f"{ws.host}/ai-gateway/mcp-services/system.ai.{service}?o={ws.workspace_id}"


def headers_helper(profile: str) -> str:
    return (
        f"databricks auth token -p {profile}"
        " | jq -c '{Authorization: (\"Bearer \" + .access_token)}'"
    )


def claude_config(ws: Workspace, service: str) -> dict[str, str]:
    """The Claude Code server entry: native HTTP, token fetched per connection."""
    return {
        "type": "http",
        "url": service_url(ws, service),
        "headersHelper": headers_helper(ws.profile),
    }


def claude_add(ws: Workspace, service: str, scope: str) -> list[str]:
    config = json.dumps(claude_config(ws, service))
    return ["claude", "mcp", "add-json", "-s", scope, server_name(service), config]


def claude_remove(service: str, scope: str) -> list[str]:
    return ["claude", "mcp", "remove", server_name(service), "-s", scope]


def copilot_add(ws: Workspace, service: str) -> list[str]:
    """The Copilot CLI entry: a stdio bridge, since Copilot has no header helper."""
    return [
        "copilot", "mcp", "add", server_name(service), "--",
        "ug", "mcp-proxy",
        "--url", service_url(ws, service),
        "--host", ws.host,
        "--profile", ws.profile,
    ]  # fmt: skip


def copilot_remove(service: str) -> list[str]:
    return ["copilot", "mcp", "remove", server_name(service)]


def commands(
    ws: Workspace | None,
    services: Sequence[str],
    clients: Sequence[str],
    claude_scope: str,
    remove: bool = False,
) -> list[list[str]]:
    out: list[list[str]] = []
    for client in clients:
        for service in services:
            if client == "claude":
                if remove:
                    out.append(claude_remove(service, claude_scope))
                else:
                    if ws is None:
                        raise ValueError("a workspace is required to add MCP services")
                    out.append(claude_add(ws, service, claude_scope))
            else:
                if remove:
                    out.append(copilot_remove(service))
                else:
                    if ws is None:
                        raise ValueError("a workspace is required to add MCP services")
                    out.append(copilot_add(ws, service))
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
    if not PROFILE_RE.match(profile):
        raise ValueError(
            f"profile {profile!r}: use letters, digits, '.', '_' or '-' only"
        )
    if not host or not workspace_id:
        described_host, described_id = describe(profile)
        host = host or described_host
        workspace_id = workspace_id or described_id
    host = host.rstrip("/")
    if not HOST_RE.match(host):
        raise ValueError(f"host {host!r}: expected https://<workspace-hostname>")
    if not WORKSPACE_ID_RE.match(workspace_id):
        raise ValueError(f"workspace ID {workspace_id!r}: expected digits only")
    return Workspace(profile, host, workspace_id)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print Claude Code / Copilot CLI commands that register "
        "Databricks system.ai MCP services. Runs none of them."
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
        if not PROFILE_RE.match(args.profile):
            raise ValueError(
                f"profile {args.profile!r}: use letters, digits, '.', '_' or '-' only"
            )
        requested = list(dict.fromkeys(args.service or []))
        if args.remove:
            if not requested:
                raise ValueError("--remove requires at least one --service")
            services = requested
            ws = None
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

    clients = list(dict.fromkeys(args.client or CLIENTS))
    assert ws is not None or args.remove
    for argv_out in commands(ws, services, clients, args.claude_scope, args.remove):
        print(shlex.join(argv_out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
