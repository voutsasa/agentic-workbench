#!/usr/bin/env python3
"""Read-only discovery for the setup-mcp-servers skill."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

MCP_SERVICES_PATH = (
    "/api/2.1/unity-catalog/mcp-services?parent=schemas/system.ai&view=BASIC"
)
SERVICE_RE = re.compile(r"^[A-Za-z0-9_]+$")
MACHINE_NOTE = Path(".agentic-workbench") / "machine.md"
LEGACY_MACHINE_NOTE = Path(".claude") / "machine.md"


def default_machine_note(home: Path) -> tuple[Path, str | None]:
    """The machine note to read, and a warning when only the legacy one exists."""
    note, legacy = home / MACHINE_NOTE, home / LEGACY_MACHINE_NOTE
    if not note.exists() and legacy.exists():
        return legacy, (
            f"read the legacy {legacy}; run workstation/scripts/link_config.py "
            f"--apply to link {note}"
        )
    return note, None


def machine_repo(note: Path) -> Path:
    """Return the workbench root recorded in a linked machine note."""
    text = note.read_text(encoding="utf-8")
    match = re.search(r"^repo:\s*(.+?)\s*$", text, re.MULTILINE)
    if not match:
        raise ValueError(f"{note} has no `repo:` frontmatter value")
    return Path(match.group(1))


def parse_internal_services(output: str) -> tuple[str, ...]:
    """Return internal ``system.ai`` MCP service names from API JSON."""
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ValueError("MCP-services response was not valid JSON") from exc
    entries = payload.get("mcp_services")
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


def command_output(argv: list[str]) -> str:
    """Run a read-only command and return stdout or a bounded error."""
    result = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode:
        raise ValueError((result.stderr or result.stdout).strip())
    return result.stdout


def discover(
    root: Path,
    *,
    databricks_profile: str | None,
    run: Callable[[list[str]], str] = command_output,
) -> dict[str, object]:
    """Collect setup facts without registering, authenticating, or writing."""
    catalog_path = root / "workstation" / "mcp" / ".mcp.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog_servers = sorted(catalog.get("mcpServers", {}))
    project_path = root / ".mcp.json"
    project_servers: list[str] = []
    if project_path.is_file():
        project = json.loads(project_path.read_text(encoding="utf-8"))
        project_servers = sorted(project.get("mcpServers", {}))

    databricks: dict[str, object] = {"status": "not_requested"}
    if databricks_profile:
        try:
            output = run(
                [
                    "databricks",
                    "api",
                    "get",
                    MCP_SERVICES_PATH,
                    "-p",
                    databricks_profile,
                    "-o",
                    "json",
                ]
            )
            databricks = {
                "status": "available",
                "profile": databricks_profile,
                "internal_services": list(parse_internal_services(output)),
            }
        except (OSError, ValueError) as exc:
            databricks = {"status": "unavailable", "detail": str(exc)}

    return {
        "repo": str(root),
        "servers": {"catalog": catalog_servers, "project": project_servers},
        "clients": {
            name: shutil.which(name) is not None for name in ("claude", "copilot")
        },
        "tools": {
            name: shutil.which(name) is not None
            for name in ("npx", "databricks", "jq", "ug")
        },
        "databricks": databricks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", type=Path, help="workbench root; defaults to machine note"
    )
    parser.add_argument(
        "--machine-note",
        type=Path,
        help="linked machine note used when --repo is omitted "
        "(default: ~/.agentic-workbench/machine.md, else the legacy "
        "~/.claude/machine.md)",
    )
    parser.add_argument(
        "--databricks-profile",
        help="opt into one read-only Databricks MCP-service catalog query",
    )
    args = parser.parse_args(argv)
    note: Path | None = args.machine_note
    if note is None and args.repo is None:
        note, warning = default_machine_note(Path.home())
        if warning:
            print(f"setup-mcp-servers: warning: {warning}", file=sys.stderr)
    try:
        root: Path = args.repo or machine_repo(note or Path())
        result = discover(root, databricks_profile=args.databricks_profile)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"setup-mcp-servers: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
