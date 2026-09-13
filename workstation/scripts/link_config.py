#!/usr/bin/env python3
"""Report or repair the links that put this repo's agent config in ``~/.claude`` and ``~/.copilot``.

Standard library only, so it runs on a fresh clone before anything is installed.

``--agent claude`` (the default) links the skills, ``CLAUDE.md`` and the machine
note into ``~/.claude``. ``--agent copilot`` links the same skills into
``~/.copilot/skills`` and nothing else: Copilot reaches the instructions through
VS Code's ``chat.useClaudeMdFile``, which is a settings edit and not a link.

Two things make this more than a wrapper around ``ln -s``:

* **``settings.json`` is never touched.** The live ``~/.claude/settings.json``
  carries provider configuration required for compliance, and every link
  primitive replaces rather than merges its target. It is excluded structurally
  here — see ``NEVER_LINK`` — not by remembering to leave it out.
* **A detached link is not the same as a missing one.** On Windows the files are
  hardlinks, and ``git checkout`` replaces a tracked file rather than editing it
  in place. That silently detaches the link and freezes ``~/.claude`` at the old
  content, which is how this repo's config drifted in the first place. Re-running
  with ``--apply`` is the repair, but a detached copy whose content has *diverged*
  is reconciliation work, so it is reported and skipped rather than overwritten.

Default is read-only. Nothing is written without ``--apply``.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Statuses, worst last so the rollup can take a max.
LINKED = "linked"
MISSING = "missing"
DETACHED = "detached"
DIVERGED = "diverged"
OCCUPIED = "occupied"
NO_SOURCE = "no_source"

SEVERITY = {
    LINKED: 0,
    MISSING: 1,
    DETACHED: 2,
    DIVERGED: 3,
    OCCUPIED: 3,
    NO_SOURCE: 4,
}

#: Repaired by ``--apply`` without needing ``--force``. A detached link whose
#: content still matches the repo has lost nothing, so re-linking is safe.
REPAIRABLE = (MISSING, DETACHED)

#: Never linked, never copied, never regenerated, under any flag. The live file
#: is authoritative and is merged by hand; see workstation/agent/README.md.
NEVER_LINK = frozenset({"settings.json"})

SKILLS = ("review", "python-quality", "verify-docs", "fix-findings", "pdf-deliverable",
          "fetch-to-markdown")

#: Agents whose home this script can link into. Claude is the default so every
#: invocation written before ``--agent`` existed keeps its meaning.
AGENTS = ("claude", "copilot")


@dataclass(frozen=True)
class Link:
    """One artefact to be reachable at a fixed path under an agent's home."""

    label: str
    source: Path
    dest: Path
    is_dir: bool


@dataclass
class LinkState:
    link: Link
    status: str
    detail: str = ""
    repaired: bool = False


@dataclass
class Report:
    states: list[LinkState] = field(default_factory=list)

    @property
    def status(self) -> str:
        if not self.states:
            return NO_SOURCE
        return max((s.status for s in self.states), key=lambda s: SEVERITY[s])

    @property
    def ok(self) -> bool:
        return all(s.status == LINKED for s in self.states)


def platform_token(platform: str | None = None) -> str:
    """The token used in ``machines/<platform>-<host>.md`` filenames."""
    plat = platform or sys.platform
    if plat.startswith("win"):
        return "windows"
    if plat == "darwin":
        return "macos"
    return "linux"


def short_hostname(hostname: str | None = None) -> str:
    """Lowercased first label of the hostname, matching the machines/ convention."""
    name = hostname if hostname is not None else socket.gethostname()
    return name.split(".")[0].lower()


def machine_file(repo_root: Path, platform: str | None = None,
                 hostname: str | None = None, machine: str | None = None) -> Path:
    """The ``machines/`` file this box should link as ``~/.claude/machine.md``.

    Resolved rather than derived, because a machine file is *named* by whoever
    writes it and a hostname is not always a name you want in git. In order:

    1. ``--machine <id>``, which always wins.
    2. ``<platform>-<hostname>.md`` if it exists — the documented convention.
    3. The only ``<platform>-*.md`` in the folder, if there is exactly one. A
       machine that has one file for its platform has no ambiguity to resolve,
       whatever that file is called.

    Falling through returns the convention name so the report can say which
    path was looked for. Ambiguity is never guessed at: two files and no
    hostname match is a ``no_source``, and the caller names the candidates.
    """
    machines = repo_root / "workstation" / "machines"
    token = platform_token(platform)
    if machine:
        return machines / (machine if machine.endswith(".md") else f"{machine}.md")
    conventional = machines / f"{token}-{short_hostname(hostname)}.md"
    if conventional.exists():
        return conventional
    candidates = sorted(machines.glob(f"{token}-*.md")) if machines.is_dir() else []
    if len(candidates) == 1:
        return candidates[0]
    return conventional


def copilot_home(home: Path, environ: dict[str, str] | None = None,
                 default_home: Path | None = None) -> Path:
    """Where Copilot keeps its user config: ``$COPILOT_HOME``, else ``<home>/.copilot``.

    ``COPILOT_HOME`` is honoured only when ``home`` is the real home directory.
    A caller that passes ``--home`` is pointing at a scratch tree, and an
    inherited environment variable must not redirect its writes elsewhere.
    """
    env = os.environ if environ is None else environ
    real_home = Path.home() if default_home is None else default_home
    if env.get("COPILOT_HOME") and home == real_home:
        return Path(env["COPILOT_HOME"])
    return home / ".copilot"


def plan(repo_root: Path, home: Path, platform: str | None = None,
         hostname: str | None = None, machine: str | None = None,
         agents: tuple[str, ...] = ("claude",),
         copilot_root: Path | None = None) -> list[Link]:
    """The links this repo expects, in the order they should be applied.

    Skills come first: they are directories, so on Windows they are junctions,
    which no git operation can detach. Getting them in place is never blocked by
    the file-level reconciliation that ``CLAUDE.md`` may need.
    """
    unknown = sorted(set(agents) - set(AGENTS))
    if unknown:
        raise ValueError(f"unknown agent(s): {', '.join(unknown)}")
    agent = repo_root / "workstation" / "agent"
    links: list[Link] = []
    if "claude" in agents:
        links += [
            Link(f"skills/{skill}", agent / "skills" / skill,
                 home / ".claude" / "skills" / skill, is_dir=True)
            for skill in SKILLS
        ]
    if "copilot" in agents:
        root = copilot_root if copilot_root is not None else home / ".copilot"
        links += [
            Link(f"copilot/skills/{skill}", agent / "skills" / skill,
                 root / "skills" / skill, is_dir=True)
            for skill in SKILLS
        ]
    if "claude" in agents:
        # Source and destination names differ on purpose: the repo calls this file
        # AGENT-INSTRUCTIONS.md because more than one agent reads it, but Claude Code
        # only ever loads ``~/.claude/CLAUDE.md``, so the destination name is fixed.
        # Every label here names the destination artefact, not the source.
        links.append(Link("CLAUDE.md", agent / "AGENT-INSTRUCTIONS.md",
                          home / ".claude" / "CLAUDE.md", is_dir=False))
        links.append(Link("machine.md",
                          machine_file(repo_root, platform, hostname, machine),
                          home / ".claude" / "machine.md", is_dir=False))
    for link in links:
        if link.dest.name in NEVER_LINK:
            raise AssertionError(
                f"{link.dest.name} must never be linked; it is merged by hand"
            )
    return links


def same_target(source: Path, dest: Path) -> bool:
    """True if ``dest`` resolves to ``source``.

    ``os.path.samefile`` compares device and inode, which covers every mechanism
    in use: a POSIX symlink, a Windows hardlink, and a Windows directory junction
    all report the inode of their target. Measured on NTFS with Python 3.14:
    a junction and its target share ``st_ino``, and a hardlink pair reports
    ``st_nlink == 2``. A plain copy reports neither.
    """
    try:
        return os.path.samefile(source, dest)
    except OSError:
        return False


def inspect(link: Link) -> LinkState:
    """Classify one link without writing anything."""
    if not link.source.exists():
        return LinkState(link, NO_SOURCE, f"no source at {link.source}")
    if not link.dest.exists():
        # `exists()` follows the link, so a symlink pointing at a path that has
        # since been renamed reads as absent. It is not: the entry is there and
        # blocks `os.symlink`. This repo's config moved from `workstation-agent/`
        # to `workstation/agent/`, so links from that era are exactly this.
        if link.dest.is_symlink():
            return LinkState(link, DETACHED,
                             f"dangling symlink → {os.readlink(link.dest)}")
        return LinkState(link, MISSING, f"not present in {link.dest.parent}")
    if same_target(link.source, link.dest):
        return LinkState(link, LINKED, "")
    if link.is_dir:
        # A directory that is not the target and holds files is somebody's data.
        entries = sorted(p.name for p in link.dest.iterdir())
        if entries:
            return LinkState(link, OCCUPIED,
                             f"real directory holding {len(entries)} entr"
                             f"{'y' if len(entries) == 1 else 'ies'}")
        return LinkState(link, DETACHED, "empty directory, not a link")
    try:
        matches = link.dest.read_bytes() == link.source.read_bytes()
    except OSError as exc:
        return LinkState(link, OCCUPIED, f"unreadable: {exc}")
    if matches:
        return LinkState(link, DETACHED, "plain copy, content still matches")
    return LinkState(link, DIVERGED, "plain copy, content differs — reconcile first")


def inspect_all(links: list[Link]) -> Report:
    return Report([inspect(link) for link in links])


def make_link(link: Link, run=subprocess.run) -> None:
    """Create the link, choosing the mechanism the platform allows unelevated.

    Windows symlinks need either administrator rights or Developer Mode, so
    directories get a junction and files get a hardlink. Both work from a
    standard account; neither needs elevation.
    """
    link.dest.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.symlink(link.source, link.dest, target_is_directory=link.is_dir)
        return
    if link.is_dir:
        run(["cmd", "/c", "mklink", "/J", str(link.dest), str(link.source)],
            check=True, capture_output=True)
    else:
        os.link(link.source, link.dest)


def clear_dest(state: LinkState) -> None:
    """Remove a detached destination so it can be re-linked.

    Only ever called for a destination ``inspect`` classified as safe to replace.
    ``os.rmdir`` on a junction removes the junction and leaves its target alone.
    """
    dest = state.link.dest
    if not dest.exists() and not dest.is_symlink():
        return
    if dest.is_dir() and not dest.is_symlink():
        os.rmdir(dest)
    else:
        dest.unlink()


def apply(report: Report, force: bool = False, run=subprocess.run) -> Report:
    """Repair what can be repaired. Returns the same report, annotated.

    ``DIVERGED`` and ``OCCUPIED`` are skipped unless ``force``, because both mean
    the destination holds content the repo does not have.
    """
    for state in report.states:
        if state.status == LINKED or state.status == NO_SOURCE:
            continue
        if state.status not in REPAIRABLE and not force:
            continue
        try:
            clear_dest(state)
            make_link(state.link, run=run)
        except (OSError, subprocess.CalledProcessError) as exc:
            state.detail = f"could not link: {exc}"
            continue
        state.status = LINKED
        state.detail = "relinked" if not state.repaired else state.detail
        state.repaired = True
    return report


def render(report: Report) -> str:
    rows = [
        "| Artefact | Kind | Status | Detail |",
        "|---|---|---|---|",
    ]
    for state in report.states:
        kind = "dir" if state.link.is_dir else "file"
        detail = state.detail.replace("|", r"\|") or "—"
        rows.append(f"| `{state.link.label}` | {kind} | {state.status} | {detail} |")
    linked = sum(1 for s in report.states if s.status == LINKED)
    rows.append("")
    rows.append(f"**{linked} of {len(report.states)} linked.** "
                "`settings.json` is excluded by design — it is merged by hand.")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2],
                        help="repo root (default: inferred from this file)")
    parser.add_argument("--home", type=Path, default=Path.home(),
                        help="home directory holding .claude (default: your home)")
    parser.add_argument("--agent", action="append", choices=AGENTS, dest="agents",
                        help="agent to link for; repeat for several (default: claude)")
    parser.add_argument("--copilot-home", type=Path, metavar="DIR",
                        help="Copilot config root (default: $COPILOT_HOME when --home "
                             "is your home, else <home>/.copilot)")
    parser.add_argument("--machine", metavar="ID",
                        help="machines/<ID>.md to link as ~/.claude/machine.md "
                             "(default: <platform>-<hostname>.md, else the only "
                             "file for this platform)")
    parser.add_argument("--apply", action="store_true",
                        help="create missing and detached links (default: report only)")
    parser.add_argument("--force", action="store_true",
                        help="with --apply, also replace a diverged or occupied destination")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    # The table uses em-dashes, and a Windows console defaults to cp1252.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    agents = tuple(dict.fromkeys(args.agents or ["claude"]))
    copilot_root = args.copilot_home or copilot_home(args.home)
    report = inspect_all(plan(args.repo, args.home, machine=args.machine,
                              agents=agents, copilot_root=copilot_root))
    if args.apply:
        report = apply(report, force=args.force)

    if args.json:
        print(json.dumps({
            "agents": list(agents),
            "ok": report.ok,
            "status": report.status,
            "links": [
                {
                    "label": s.link.label,
                    "source": str(s.link.source),
                    "dest": str(s.link.dest),
                    "kind": "dir" if s.link.is_dir else "file",
                    "status": s.status,
                    "detail": s.detail,
                    "repaired": s.repaired,
                }
                for s in report.states
            ],
        }, indent=2))
    else:
        print(render(report))
        if not report.ok and not args.apply:
            print("\nRe-run with `--apply` to repair what is missing or detached.")

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
