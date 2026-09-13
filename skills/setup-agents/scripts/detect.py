#!/usr/bin/env python3
"""Identify this machine and the AI coding assistants installed on it.

Read-only: it runs ``--version`` probes and reads settings files, and writes
nothing. Standard library only, like ``workstation/scripts/``, so it runs on a
fresh clone before any venv exists.

Assistants are reported in two kinds:

* **Configurable** — Claude Code, the Copilot CLI and VS Code. A route for each
  is recorded in ``workstation/agent/setup/README.md``, so the setup-agents
  skill can act on them.
* **Report only** — anything else found on ``PATH``. No route is recorded, so
  they are named and nothing is set up.

Nothing secret is printed: provider variables are reported by name and by where
they were set, never by value; settings drift is reported by key name only.

    python3 skills/setup-agents/scripts/detect.py            # markdown
    python3 skills/setup-agents/scripts/detect.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import json
import os
import platform as platform_mod
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "workstation" / "scripts"))

# E402: sys.path has to be extended before this import, so it cannot move to the top.
import link_config

REPO_ROOT = Path(__file__).resolve().parents[3]

#: First dotted number in the probe output — what every assistant here prints.
VERSION = re.compile(r"\d+\.\d+(?:\.\d+)?")
PROBE_TIMEOUT = 15

#: Provider switches Claude Code reads, in precedence order for the report.
PROVIDER_VARS = ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "ANTHROPIC_API_KEY")


@dataclass(frozen=True)
class Spec:
    id: str
    name: str
    command: str
    configurable: bool


ASSISTANTS = (
    Spec("claude", "Claude Code CLI", "claude", True),
    Spec("copilot", "GitHub Copilot CLI", "copilot", True),
    Spec("vscode", "VS Code", "code", True),
    Spec("gemini", "Gemini CLI", "gemini", False),
    Spec("codex", "OpenAI Codex CLI", "codex", False),
    Spec("cursor", "Cursor", "cursor", False),
    Spec("opencode", "opencode", "opencode", False),
    Spec("aider", "Aider", "aider", False),
)


@dataclass
class Found:
    id: str
    name: str
    command: str
    configurable: bool
    path: str | None
    version: str | None
    detail: str


def probe(spec: Spec, which: Callable[[str], str | None] = shutil.which,
          run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> Found:
    """Resolve one assistant on ``PATH`` and read its version."""
    base = (spec.id, spec.name, spec.command, spec.configurable)
    path = which(spec.command)
    if path is None:
        return Found(*base, None, None, "not on PATH")
    try:
        done = run([path, "--version"], capture_output=True, text=True,
                   timeout=PROBE_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Found(*base, path, None, f"version probe failed: {type(exc).__name__}")
    match = VERSION.search(f"{done.stdout or ''}\n{done.stderr or ''}")
    if match is None:
        return Found(*base, path, None, "ran, printed no version")
    return Found(*base, path, match.group(0), "")


def _switched_on(value: object) -> bool:
    return str(value).strip().lower() not in ("", "0", "false", "no", "none")


def read_json(path: Path) -> tuple[str, dict]:
    """``("absent" | "read" | "unreadable: <why>", data)`` — never raises."""
    if not path.exists():
        return "absent", {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"unreadable: {type(exc).__name__}", {}
    return ("read", data) if isinstance(data, dict) else ("unreadable: not an object", {})


def claude_provider(home: Path, environ: Mapping[str, str]) -> dict:
    """Which provider Claude Code is configured for, and where that was set.

    ``subscription-or-unset`` means no provider variable is set anywhere; it
    does not prove a login, which only ``/status`` inside a session can show.
    """
    state, data = read_json(home / ".claude" / "settings.json")
    block = data.get("env", {}) if isinstance(data.get("env"), dict) else {}
    set_vars: dict[str, str] = {}
    for var in PROVIDER_VARS:
        if _switched_on(block.get(var, "")):
            set_vars[var] = "settings.json env"
        elif _switched_on(environ.get(var, "")):
            set_vars[var] = "process environment"
    if "CLAUDE_CODE_USE_BEDROCK" in set_vars:
        provider = "bedrock"
    elif "CLAUDE_CODE_USE_VERTEX" in set_vars:
        provider = "vertex"
    elif "ANTHROPIC_API_KEY" in set_vars:
        provider = "api-key"
    else:
        provider = "subscription-or-unset"
    return {"provider": provider, "settings_state": state, "set_vars": set_vars}


def settings_drift(home: Path, repo: Path) -> dict:
    """Keys in the repo's reference settings whose live value differs.

    Key names only. ``env`` is never compared: it is machine-local by design.
    """
    live_state, live = read_json(home / ".claude" / "settings.json")
    ref_state, ref = read_json(repo / "workstation" / "agent" / "settings.json")
    differs = sorted(k for k, v in ref.items() if k != "env" and live.get(k) != v)
    return {"live": live_state, "reference": ref_state, "differs": differs}


def vscode_user_settings(platform: str, home: Path, environ: Mapping[str, str]) -> Path | None:
    """VS Code's user ``settings.json``, on the platforms a route records it for."""
    token = link_config.platform_token(platform)
    if token == "macos":
        return home / "Library" / "Application Support" / "Code" / "User" / "settings.json"
    if token == "windows" and environ.get("APPDATA"):
        return Path(environ["APPDATA"]) / "Code" / "User" / "settings.json"
    return None


def jsonc_flag(path: Path | None, key: str) -> bool | None:
    """A boolean from a JSONC file, skipping ``//`` lines. ``None`` when unset.

    VS Code settings allow comments and trailing commas, so ``json`` cannot
    parse them; a line match is enough for one boolean key.
    """
    if path is None:
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    pattern = re.compile(rf'"{re.escape(key)}"\s*:\s*(true|false)\b')
    for line in lines:
        if line.lstrip().startswith("//"):
            continue
        match = pattern.search(line)
        if match:
            return match.group(1) == "true"
    return None


def link_summary(repo: Path, home: Path, agents: tuple[str, ...], copilot_root: Path,
                 platform: str | None, hostname: str | None, project: bool = False) -> dict:
    report = link_config.inspect_all(link_config.plan(
        repo, home, platform=platform, hostname=hostname,
        agents=agents, copilot_root=copilot_root, project=project))
    linked = sum(1 for s in report.states if s.status == link_config.LINKED)
    return {"linked": linked, "total": len(report.states), "status": report.status}


def collect(repo: Path, home: Path, environ: Mapping[str, str] | None = None,
            platform: str | None = None, hostname: str | None = None,
            which: Callable[[str], str | None] = shutil.which,
            run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> dict:
    env = os.environ if environ is None else environ
    plat = platform or sys.platform
    note = link_config.machine_file(repo, plat, hostname)
    copilot_root = link_config.copilot_home(home, env)
    vscode_settings = vscode_user_settings(plat, home, env)
    return {
        "machine": {
            "platform": link_config.platform_token(plat),
            "os": platform_mod.platform(),
            "hostname": link_config.short_hostname(hostname),
            "shell": env.get("SHELL") or env.get("COMSPEC") or "",
            "repo": str(repo),
            "machine_note": str(note.relative_to(repo)) if note.is_relative_to(repo) else str(note),
            "machine_note_exists": note.exists(),
        },
        "assistants": [asdict(probe(spec, which, run)) for spec in ASSISTANTS],
        "claude": {
            **claude_provider(home, env),
            "settings_drift": settings_drift(home, repo),
            "links": link_summary(repo, home, ("claude",), copilot_root, plat, hostname),
        },
        "copilot": {
            "home": str(copilot_root),
            "links": link_summary(repo, home, ("copilot",), copilot_root, plat, hostname),
        },
        "project": {
            "links": link_summary(repo, home, (), copilot_root, plat, hostname, project=True),
        },
        "vscode": {
            "user_settings": str(vscode_settings) if vscode_settings else None,
            "user_settings_exists": bool(vscode_settings and vscode_settings.exists()),
            "chat.useClaudeMdFile": jsonc_flag(vscode_settings, "chat.useClaudeMdFile"),
        },
    }


def _tilde(path: str, home: Path) -> str:
    return "~" + path[len(str(home)):] if path.startswith(str(home)) else path


def _flag(value: bool | None) -> str:
    return "not set" if value is None else str(value).lower()


def render(facts: dict, home: Path) -> str:
    m, c, cp, vs = facts["machine"], facts["claude"], facts["copilot"], facts["vscode"]
    pr = facts["project"]
    note = f"`{m['machine_note']}` ({'present' if m['machine_note_exists'] else '**absent**'})"
    out = [
        "## Machine", "",
        "| What | Value |", "|---|---|",
        f"| Platform | {m['platform']} (`{m['os']}`) |",
        f"| Hostname | {m['hostname']} |",
        f"| Shell | `{m['shell'] or 'unknown'}` |",
        f"| Machine note | {note} |",
        "", "## Assistants", "",
        "| Assistant | Path | Version | This skill |", "|---|---|---|---|",
    ]
    found = [a for a in facts["assistants"] if a["path"]]
    for a in found:
        version = a["version"] or f"— ({a['detail']})"
        route = "configurable" if a["configurable"] else "report only — no route recorded"
        out.append(f"| {a['name']} | `{_tilde(a['path'], home)}` | {version} | {route} |")
    if not found:
        out.append("| _none found on PATH_ | — | — | — |")
    absent = [a["command"] for a in facts["assistants"] if not a["path"]]
    if absent:
        out += ["", "Not on PATH: " + ", ".join(f"`{cmd}`" for cmd in absent) + "."]
    drift = c["settings_drift"]
    drift_text = (", ".join(f"`{k}`" for k in drift["differs"]) or "none"
                  if drift["live"] == "read" else f"live file {drift['live']}")
    set_vars = ", ".join(f"`{k}` ({v})" for k, v in c["set_vars"].items()) or "no provider variable set"
    settings = vs["user_settings"]
    vs_text = (f"{_flag(vs['chat.useClaudeMdFile'])} in `{_tilde(settings, home)}`"
               if settings and vs["user_settings_exists"]
               else "no user settings file" if settings else "no route for this platform")
    out += [
        "", "## Current configuration", "",
        "| What | State |", "|---|---|",
        f"| Claude provider | **{c['provider']}** — {set_vars} |",
        f"| Claude global links (`~/.claude`) | {c['links']['linked']} of {c['links']['total']} linked |",
        f"| Claude settings keys differing from `workstation/agent/settings.json` | {drift_text} |",
        (f"| Copilot global skill links (`{_tilde(cp['home'], home)}/skills`) | "
         f"{cp['links']['linked']} of {cp['links']['total']} linked |"),
        (f"| This repo's skills (`.claude/skills`, project scope) | "
         f"{pr['links']['linked']} of {pr['links']['total']} linked |"),
        f"| VS Code `chat.useClaudeMdFile` | {vs_text} |",
    ]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=REPO_ROOT,
                        help="repo root (default: inferred from this file)")
    parser.add_argument("--home", type=Path, default=Path.home(),
                        help="home directory to inspect (default: your home)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    facts = collect(args.repo, args.home)
    print(json.dumps(facts, indent=2) if args.json else render(facts, args.home))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
