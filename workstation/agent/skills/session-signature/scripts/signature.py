"""Print a session signature as JSON.

The model ID is a required argument: only the running agent knows which model it is,
and the configured env.ANTHROPIC_MODEL can differ from the model actually serving the session.

Usage:
    python signature.py --model eu.anthropic.claude-opus-5-5               # id only
    python signature.py --model <id> --extended                            # full JSON
    python signature.py --model <id> --harness github-copilot
    python signature.py --model <id> --harness kiro-cli --harness-command kiro-cli
    python signature.py --model <id> --harness kiro --harness-version 0.5.0
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_MANIFEST = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
AGENT_NAME = "agentic-workbench"

# The id is these attribute values, in this order, joined with "_".
ID_FIELDS = ("workstation", "username", "harness", "agent", "model", "timestamp")

# Known harness labels -> the CLI whose `--version` gives the version. Any other label
# works too, given --harness-command or --harness-version.
KNOWN_HARNESSES = {"claude-cli": "claude", "github-copilot": "copilot"}
# No "_" in a label: it separates the id's fields.
HARNESS_LABEL = re.compile(r"^[a-z0-9][a-z0-9.-]*$")


def hostname() -> str:
    return os.environ.get("COMPUTERNAME") or socket.gethostname()


def username() -> str:
    return getpass.getuser()


def harness_version(label: str, command: str | None = None) -> str:
    command = command or KNOWN_HARNESSES.get(label)
    if not command:
        raise ValueError(
            f"unknown harness {label!r}: pass --harness-command or --harness-version"
        )
    # which() resolves claude.cmd on Windows, which subprocess alone cannot.
    exe = shutil.which(command)
    if not exe:
        raise FileNotFoundError(f"`{command}` not on PATH")
    out = subprocess.run(
        [exe, "--version"], capture_output=True, text=True, timeout=30, check=True
    ).stdout
    match = re.search(r"\d+\.\d+\.\d+", out)
    if not match:
        raise ValueError(f"no version in `{command} --version` output: {out!r}")
    return f"{label}-{match.group(0)}"


def agent_version(manifest: Path = PLUGIN_MANIFEST) -> str:
    version = json.loads(manifest.read_text(encoding="utf-8"))["version"]
    return f"{AGENT_NAME}-{version}"


def timestamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")


def build(attrs: dict[str, str]) -> dict:
    return {
        "signature": {
            "id": "_".join(attrs[field] for field in ID_FIELDS),
            **{field: attrs[field] for field in ID_FIELDS},
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print a session signature as JSON.")
    parser.add_argument("--model", required=True, help="model ID serving this session")
    parser.add_argument(
        "--harness",
        default="claude-cli",
        help="AI assistant label, e.g. claude-cli, github-copilot, kiro (default: claude-cli)",
    )
    parser.add_argument(
        "--harness-command", help="CLI to probe with --version, for an unlisted harness"
    )
    parser.add_argument(
        "--harness-version", help="version to use as-is instead of probing"
    )
    parser.add_argument(
        "--extended", action="store_true", help="print the full JSON, not just the id"
    )
    args = parser.parse_args(argv)
    if not HARNESS_LABEL.match(args.harness):
        parser.error(
            f"--harness {args.harness!r}: use lowercase letters, digits, '.', '-'"
        )
    try:
        if args.harness_version:
            harness = f"{args.harness}-{args.harness_version}"
        else:
            harness = harness_version(args.harness, args.harness_command)
        agent = agent_version()
    except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
        print(f"signature: {exc}", file=sys.stderr)
        return 1
    sig = build(
        {
            "workstation": hostname(),
            "username": username(),
            "harness": harness,
            "agent": agent,
            "model": args.model,
            "timestamp": timestamp(),
        }
    )
    print(json.dumps(sig, indent=2) if args.extended else sig["signature"]["id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
