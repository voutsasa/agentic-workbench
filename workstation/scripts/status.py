#!/usr/bin/env python3
"""Report whether this workstation meets its recorded prerequisites."""

from __future__ import annotations

import argparse
import csv
import io
import json
import platform as platform_mod
import re
import sys
import tomllib
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

import inventory
import link_config

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSION_PARTS = re.compile(r"\d+")


@dataclass
class StatusRow:
    capability: str
    requirement: str
    status: str
    version: str
    evidence: str
    corrective_action: str
    required: bool
    provisioning: str


def version_key(version: str) -> tuple[int, ...]:
    """Return numeric version components for minimum-version comparisons."""
    return tuple(int(part) for part in VERSION_PARTS.findall(version))


def meets_minimum(observed: str, minimum: str) -> bool:
    """Compare dotted versions, padding the shorter side with zeroes."""
    left, right = version_key(observed), version_key(minimum)
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)) >= right + (0,) * (width - len(right))


def prerequisite_file(machine_note: Path) -> Path:
    return machine_note.with_suffix(".prerequisites.toml")


def load_toml(path: Path, list_key: str | None = None) -> dict:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    if data.get("schema_version") != 1:
        raise ValueError(f"unsupported schema_version in {path}")
    if list_key is not None:
        entries = data.get(list_key)
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"no [[{list_key}]] entries in {path}")
    return data


def merge_dependencies(common: dict, profile: dict) -> list[dict]:
    """Apply a machine's keyed overrides to the shared dependency list."""
    overrides = profile.get("overrides", {})
    if not isinstance(overrides, dict):
        raise TypeError("machine profile `overrides` must be a table")
    dependencies = common["dependencies"]
    ids = [entry.get("id") for entry in dependencies]
    if len(ids) != len(set(ids)) or any(not item for item in ids):
        raise ValueError("dependency ids must be present and unique")
    unknown = sorted(set(overrides) - set(ids))
    if unknown:
        raise ValueError(f"unknown dependency overrides: {', '.join(unknown)}")
    return [entry | overrides.get(entry["id"], {}) for entry in dependencies]


def probe_prerequisite(
    entry: dict,
    timeout: int,
    runtime_version: str | None = None,
    runtime_path: str | None = None,
    venv: bool = True,
) -> StatusRow:
    """Probe one dependency.

    A ``python-runtime`` entry reports the interpreter running this script when
    the repo has a ``.venv`` — that is the one the workbench's Python runs on.
    Without one, the bootstrap scripts run on whatever the named command
    resolves to, so that command is probed on PATH like any other.
    """
    commands = entry.get("commands", [])
    mode = entry.get("mode", "all")
    if not commands or mode not in {"all", "any"}:
        raise ValueError(f"invalid prerequisite {entry.get('id', '<unknown>')}")

    if entry.get("probe") == "python-runtime" and venv:
        path = runtime_path or sys.executable
        probes = [
            inventory.Probe(
                commands[0],
                inventory.INSTALLED,
                version=runtime_version or platform_mod.python_version(),
                path=path,
                detail=f"running interpreter {path}",
            )
        ]
    else:
        probes = [
            inventory.probe_command(
                command, entry.get("version_flag", "--version"), timeout=timeout
            )
            for command in commands
        ]
    installed = [probe for probe in probes if probe.status == inventory.INSTALLED]
    present = bool(installed) if mode == "any" else len(installed) == len(probes)
    minimum = entry.get("minimum_version", "")
    version = ", ".join(f"{probe.command} {probe.version}" for probe in installed)
    evidence = "; ".join(
        f"{probe.command}: {probe.detail or probe.status}" for probe in probes
    )

    if (
        present
        and minimum
        and not all(meets_minimum(probe.version, minimum) for probe in installed)
    ):
        status = "outdated"
    elif present:
        status = "installed"
    elif any(probe.status == inventory.BLOCKED for probe in probes):
        status = "blocked"
    elif any(probe.status == inventory.ERROR for probe in probes):
        status = "error"
    else:
        status = "absent"

    requirement = (
        f">= {minimum}"
        if minimum
        else ("one of " if mode == "any" else "") + ", ".join(commands)
    )

    if entry.get("all_versions"):
        stem = re.sub(r"\d+(\.\d+)*$", "", commands[0])
        active_version = installed[0].version if installed else ""
        distinct = sorted(
            {
                probe.version
                for probe in inventory.probe_all_versions(stem, timeout=timeout)
                if probe.status == inventory.INSTALLED and probe.version
            },
            key=version_key,
            reverse=True,
        )
        if distinct:
            version = ", ".join(
                f"{v} (active)" if v == active_version else v for v in distinct
            )

    return StatusRow(
        capability=entry["product"],
        requirement=requirement,
        status=status,
        version=version or "—",
        evidence=evidence,
        corrective_action=(
            "—" if status == "installed" else entry["corrective_action"]
        ),
        required=bool(entry.get("required", True)),
        provisioning=entry.get("provisioning", "workbench"),
    )


def platform_install_command(install_file: Path, platform: str) -> str:
    """Read one platform command from an install.md table."""
    pattern = re.compile(
        rf"^\|\s*{re.escape(platform)}\s*\|\s*`(?P<command>[^`]+)`\s*\|$",
        re.MULTILINE,
    )
    match = pattern.search(install_file.read_text(encoding="utf-8"))
    return match.group("command") if match else ""


def used_by(install_file: Path) -> list[str]:
    """Return the skills named by an install.md's ``used_by`` frontmatter."""
    frontmatter = inventory.parse_frontmatter(install_file.read_text(encoding="utf-8"))
    return [
        name.strip()
        for name in frontmatter.get("used_by", "").split(",")
        if name.strip()
    ]


def tool_row(
    result: inventory.ToolResult, repo: Path, cli_dir: Path, platform: str
) -> StatusRow:
    install_file = cli_dir / result.folder / "install.md"
    command = platform_install_command(install_file, platform)
    skills = used_by(install_file)
    if result.status == inventory.INSTALLED:
        action = "—"
    elif result.status == inventory.ABSENT and command:
        action = command
    else:
        action = (
            f"Read `{install_file.relative_to(repo)}` and "
            f"`{(install_file.parent / 'quick_start.md').relative_to(repo)}`; "
            "do not reinstall until the failure is diagnosed."
        )
    evidence = result.detail or "; ".join(
        f"{probe.command}: {probe.detail}" for probe in result.probes
    )
    return StatusRow(
        capability=result.product,
        requirement="workstation tool"
        + (f" for {', '.join(skills)}" if skills else ""),
        status=result.status,
        version=result.version or "—",
        evidence=evidence or "version probe succeeded",
        corrective_action=action,
        required=False,
        provisioning="workbench",
    )


def overall_status(rows: list[StatusRow]) -> str:
    failed_required = any(
        row.required and row.status != inventory.INSTALLED for row in rows
    )
    if failed_required:
        return "NOT READY"
    return (
        "READY WITH ACTIONS"
        if any(row.status != inventory.INSTALLED for row in rows)
        else "READY"
    )


def collect(
    repo: Path,
    machine: str | None = None,
    timeout: int = inventory.DEFAULT_TIMEOUT,
    platform: str | None = None,
    hostname: str | None = None,
    progress: bool = False,
) -> dict:
    note = link_config.machine_file(repo, platform, hostname, machine)
    profile_path = prerequisite_file(note)
    dependencies_path = repo / "workstation" / "dependencies.toml"
    common = load_toml(dependencies_path, "dependencies")
    profile = load_toml(profile_path)
    dependencies = merge_dependencies(common, profile)
    venv = (repo / ".venv").is_dir()
    cli_dir = repo / "workstation" / "cli"
    declared_tools = inventory.discover_tools(cli_dir)

    total = len(dependencies) + len(declared_tools)
    seen = 0

    def report(label: str) -> None:
        nonlocal seen
        if progress:
            seen += 1
            print(f"[{seen}/{total}] Probing {label}...", file=sys.stderr)

    prerequisites = []
    for entry in dependencies:
        report(entry.get("product", entry.get("id", "?")))
        prerequisites.append(probe_prerequisite(entry, timeout, venv=venv))

    tools = inventory.run_inventory(declared_tools, timeout=timeout, on_progress=report)
    tool_rows = [
        tool_row(result, repo, cli_dir, profile["platform"]) for result in tools
    ]
    rows = prerequisites + tool_rows
    return {
        "machine": profile["machine"],
        "profile": str(profile_path.relative_to(repo)),
        "dependencies": str(dependencies_path.relative_to(repo)),
        "overall": overall_status(rows),
        "prerequisites": [asdict(row) for row in prerequisites],
        "tools": [asdict(row) for row in tool_rows],
    }


def escape(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", " ")


HEADERS = (
    "Capability",
    "Requirement",
    "Status",
    "Version",
    "Evidence",
    "Corrective action",
)


def row_values(row: dict) -> tuple[str, str, str, str, str, str]:
    """The six report columns for one row, requirement folded with its qualifiers."""
    qualifiers = ["required" if row["required"] else "optional"]
    if row["provisioning"] == "external":
        qualifiers.append("external provisioning")
    requirement = f"{row['requirement']} ({'; '.join(qualifiers)})"
    return (
        row["capability"],
        requirement,
        row["status"],
        row["version"],
        row["evidence"],
        row["corrective_action"],
    )


def render(report: dict) -> str:
    rows = report["prerequisites"] + report["tools"]
    lines = [
        f"# Workstation status: {report['overall']}",
        "",
        f"Machine profile: `{report['profile']}`",
        f"Common dependencies: `{report['dependencies']}`",
        "",
        "| " + " | ".join(HEADERS) + " |",
        "|" + "---|" * len(HEADERS),
    ]
    for row in rows:
        lines.append(
            "| " + " | ".join(escape(value) for value in row_values(row)) + " |"
        )
    return "\n".join(lines)


def render_csv(report: dict) -> str:
    rows = report["prerequisites"] + report["tools"]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADERS)
    for row in rows:
        writer.writerow(row_values(row))
    return buffer.getvalue()


def report_filename(format_: str, today: date | None = None) -> str:
    extension = {"json": "json", "csv": "csv"}.get(format_, "md")
    return f"workstation-status-{(today or datetime.now().astimezone().date()):%Y%m%d}.{extension}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--machine", help="machine id or machine-note filename")
    formats = parser.add_mutually_exclusive_group()
    formats.add_argument("--json", action="store_true")
    formats.add_argument("--csv", action="store_true")
    parser.add_argument("--timeout", type=int, default=inventory.DEFAULT_TIMEOUT)
    parser.add_argument(
        "--persist",
        action="store_true",
        help="also write the report to workstation-status-YYYYMMDD.<ext> under --repo",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress the '[n/total] Probing ...' progress lines on stderr",
    )
    args = parser.parse_args(argv)

    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")
    try:
        report = collect(args.repo, args.machine, args.timeout, progress=not args.quiet)
    except (OSError, TypeError, ValueError, tomllib.TOMLDecodeError) as exc:
        parser.error(str(exc))

    format_ = "json" if args.json else "csv" if args.csv else "md"
    rendered = {
        "json": lambda: json.dumps(report, indent=2),
        "csv": lambda: render_csv(report),
        "md": lambda: render(report),
    }[format_]()
    print(rendered)

    if args.persist:
        destination = args.repo / report_filename(format_)
        destination.write_text(rendered, encoding="utf-8")
        print(f"Report written to {destination}")

    return 0 if report["overall"] != "NOT READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
