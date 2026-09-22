#!/usr/bin/env python3
"""Probe this machine for the workstation CLI toolchain.

Reads every ``workstation/cli/<tool>/install.md`` for the command(s) that tool
provides, runs each command's version probe, and prints the inventory table
that belongs in ``workstation/machines/<id>.md``.

Why this exists: ``install.md`` records *how to install* a tool, which is the
same on every machine of a given platform. Whether the command actually runs
*here* is per-machine state with a shelf life, so it is measured rather than
written down by hand. See ``workstation/machines/README.md``.

Standard library only. Run from anywhere::

    python workstation/scripts/inventory.py
    python workstation/scripts/inventory.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_VERSION_FLAG = "--version"
DEFAULT_TIMEOUT = 120

# Four statuses, deliberately. "Not usable here" collapses three situations
# that call for three different responses: install it, get it allow-listed, or
# investigate. Collapsing them is how a blocked tool gets mistaken for a
# missing one and reinstalled pointlessly.
INSTALLED = "installed"  # ran, and reported a version
BLOCKED = "blocked"  # resolved on PATH, but the OS refused to run it
ABSENT = "absent"  # nothing of that name on PATH
ERROR = "error"  # ran, but produced no usable version output

# Worst-wins ordering, for a tool that ships more than one command.
SEVERITY = {INSTALLED: 0, ERROR: 1, BLOCKED: 2, ABSENT: 3}

VERSION_RE = re.compile(r"\d+(?:\.\d+)+(?:[.+-][\w-]+)*")


@dataclass
class Tool:
    """A tool as declared by its ``install.md`` frontmatter."""

    folder: str
    product: str
    commands: list[str]
    version_flag: str = DEFAULT_VERSION_FLAG


@dataclass
class Probe:
    """The result of running one command's version flag."""

    command: str
    status: str
    version: str = ""
    path: str = ""
    detail: str = ""


@dataclass
class ToolResult:
    """A tool's rolled-up status across all the commands it provides."""

    folder: str
    product: str
    status: str
    version: str = ""
    detail: str = ""
    probes: list[Probe] = field(default_factory=list)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Return the ``key: value`` pairs of a leading ``---`` fenced block.

    Not a YAML parser: these files carry flat scalars only, and a dependency
    would have to be installed on every machine that runs this.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    pairs: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, separator, value = line.partition(":")
        if separator:
            pairs[key.strip()] = value.strip()
    return pairs


def discover_tools(cli_dir: Path) -> list[Tool]:
    """Build the tool list from ``<cli_dir>/*/install.md`` frontmatter."""
    tools: list[Tool] = []
    for install in sorted(cli_dir.glob("*/install.md")):
        frontmatter = parse_frontmatter(install.read_text(encoding="utf-8"))
        commands = [
            c.strip() for c in frontmatter.get("command", "").split(",") if c.strip()
        ]
        if not commands:
            continue
        tools.append(
            Tool(
                folder=install.parent.name,
                product=frontmatter.get("product", install.parent.name),
                commands=commands,
                version_flag=frontmatter.get("version_flag", DEFAULT_VERSION_FLAG),
            )
        )
    return tools


def extract_version(output: str) -> str:
    """Pull the first dotted version number out of a tool's version output."""
    for line in output.splitlines():
        match = VERSION_RE.search(line)
        if match:
            return match.group(0)
    return ""


def first_line(output: str) -> str:
    """The first non-empty line, for the table's Detail column."""
    for line in output.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _run_probe(
    command_label: str,
    resolved: str,
    version_flag: str,
    timeout: int,
    run,
) -> Probe:
    """Run ``resolved``'s version flag and classify the result.

    Shared by ``probe_command`` (one name, resolved via ``which``) and
    ``probe_all_versions`` (every matching path found on ``PATH``).
    """
    try:
        completed = run(
            [resolved, version_flag],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return Probe(
            command_label, ERROR, path=resolved, detail=f"no response in {timeout}s"
        )
    except OSError as exc:
        # PermissionError is an OSError. A binary that resolves on PATH but
        # cannot be launched is the signature of an endpoint-security
        # quarantine, not of a bad install.
        return Probe(
            command_label,
            BLOCKED,
            path=resolved,
            detail=f"{type(exc).__name__}: {exc}",
        )

    output = (completed.stdout or "") + (completed.stderr or "")
    version = extract_version(output)
    if version:
        return Probe(
            command_label,
            INSTALLED,
            version=version,
            path=resolved,
            detail=first_line(output),
        )
    detail = first_line(output) or f"exit {completed.returncode}, no version output"
    return Probe(command_label, ERROR, path=resolved, detail=detail)


def probe_command(
    command: str,
    version_flag: str = DEFAULT_VERSION_FLAG,
    timeout: int = DEFAULT_TIMEOUT,
    which=shutil.which,
    run=subprocess.run,
) -> Probe:
    """Resolve ``command`` on PATH and run its version flag.

    ``which`` and ``run`` are injectable so the classification logic can be
    tested without depending on what happens to be installed.
    """
    resolved = which(command)
    if resolved is None:
        return Probe(command=command, status=ABSENT, detail="not on PATH")
    return _run_probe(command, resolved, version_flag, timeout, run)


def discover_on_path(pattern: re.Pattern, environ: dict | None = None) -> list[Path]:
    """Return every unique executable on ``PATH`` whose name matches ``pattern``.

    Resolves each match so the same binary reachable through two ``PATH``
    entries (a shim and its target, say) is reported once. ``environ`` is
    injectable for tests.
    """
    path_value = (environ if environ is not None else os.environ).get("PATH", "")
    seen: set[Path] = set()
    found: list[Path] = []
    for directory in path_value.split(os.pathsep):
        if not directory:
            continue
        directory_path = Path(directory)
        try:
            entries = list(directory_path.iterdir())
        except OSError:
            continue
        for candidate in entries:
            if not pattern.match(candidate.name):
                continue
            try:
                if not candidate.is_file():
                    continue
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(resolved)
    return found


def probe_all_versions(
    stem: str,
    version_flag: str = DEFAULT_VERSION_FLAG,
    timeout: int = DEFAULT_TIMEOUT,
    run=subprocess.run,
    environ: dict | None = None,
) -> list[Probe]:
    """Probe every installed version of ``stem`` found anywhere on ``PATH``.

    Matches ``stem`` itself, ``stem`` plus a trailing version number
    (``python3``, ``python3.12``), and the Windows executable/shim suffixes
    (``.exe``, ``.cmd``, ``.ps1``) — not e.g. ``pythonw`` or ``npm-cli.js``.
    """
    name_pattern = re.compile(
        rf"^{re.escape(stem)}(\d+(\.\d+)?)?(\.exe|\.cmd|\.ps1)?$", re.IGNORECASE
    )
    return [
        _run_probe(stem, str(path), version_flag, timeout, run)
        for path in discover_on_path(name_pattern, environ=environ)
    ]


def roll_up(tool: Tool, probes: list[Probe]) -> ToolResult:
    """Reduce a tool's per-command probes to one status: worst wins."""
    worst = max(probes, key=lambda p: SEVERITY[p.status])
    version = next((p.version for p in probes if p.version), "")
    return ToolResult(
        folder=tool.folder,
        product=tool.product,
        status=worst.status,
        version=version,
        detail="" if worst.status == INSTALLED else worst.detail,
        probes=probes,
    )


def run_inventory(
    tools: list[Tool], timeout: int = DEFAULT_TIMEOUT, **probe_kwargs
) -> list[ToolResult]:
    """Probe every command of every tool."""
    results = []
    for tool in tools:
        probes = [
            probe_command(command, tool.version_flag, timeout=timeout, **probe_kwargs)
            for command in tool.commands
        ]
        results.append(roll_up(tool, probes))
    return results


def machine_facts() -> dict[str, str]:
    """The identity of the machine being probed."""
    return {
        "node": platform.node(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }


def suggested_id(facts: dict[str, str]) -> str:
    """A filename slug for ``workstation/machines/<id>.md``."""
    system = facts["system"].lower()
    if system == "darwin":
        system = "macos"
    elif system == "windows":
        # `platform.release()` is "10" for Windows 11; the build number is the
        # only reliable discriminator, so keep the marketing name out of it.
        system = "windows"
    # First label only. `platform.node()` returns an FQDN on macOS
    # ("host.local") and a bare name on Windows, and link_config.py matches on
    # the short form — an id carrying ".local" names a file nothing looks for.
    return f"{system}-{facts['node'].split('.')[0].lower()}"


def render_markdown(
    results: list[ToolResult], facts: dict[str, str], host: str | None = None
) -> str:
    """The inventory table, ready to paste into a machine file.

    ``host`` replaces the probed node name in the provenance line. A machine
    file is committed, and a hostname can be a person's name; the file is
    identified by the id in its frontmatter, not by what DNS calls the box.
    """
    usable = sum(1 for r in results if r.status == INSTALLED)
    lines = [
        (
            f"Probed on `{host or facts['node']}` "
            f"({facts['system']} {facts['version']}, Python {facts['python']}) "
            f"by `workstation/scripts/inventory.py`."
        ),
        "",
        f"**{usable} of {len(results)} usable.**",
        "",
        "| Command | Product | Status | Version | Detail |",
        "|---|---|---|---|---|",
    ]
    for result in results:
        commands = ", ".join(f"`{p.command}`" for p in result.probes)
        detail = result.detail.replace("|", r"\|")
        lines.append(
            f"| {commands} | {result.product} | {result.status} "
            f"| {result.version or '—'} | {detail or '—'} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    default_cli = Path(__file__).resolve().parents[1] / "cli"
    parser.add_argument(
        "--cli-dir",
        type=Path,
        default=default_cli,
        help=f"directory holding <tool>/install.md (default: {default_cli})",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit JSON instead of a markdown table"
    )
    parser.add_argument(
        "--host",
        metavar="LABEL",
        help="name to print instead of the probed hostname, for a machine file "
        "that is committed under a chosen id rather than a DNS name",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"seconds to wait for a version probe (default: {DEFAULT_TIMEOUT})",
    )
    args = parser.parse_args(argv)

    # The table contains em-dashes, and a Windows console defaults to cp1252,
    # which turns them into replacement characters on the way out. Redirecting
    # to a file inherits the same codec, so this has to be set here.
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")

    if not args.cli_dir.is_dir():
        parser.error(f"no such directory: {args.cli_dir}")

    tools = discover_tools(args.cli_dir)
    if not tools:
        parser.error(
            f"no <tool>/install.md with a `command:` field under {args.cli_dir}"
        )

    facts = machine_facts()
    results = run_inventory(tools, timeout=args.timeout)

    if args.json:
        if args.host:
            facts = facts | {"node": args.host}
        payload = {
            "machine": facts,
            "suggested_id": suggested_id(facts),
            "tools": [asdict(r) for r in results],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render_markdown(results, facts, host=args.host))
    return 0


if __name__ == "__main__":
    sys.exit(main())
