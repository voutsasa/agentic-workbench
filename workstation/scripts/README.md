# Workstation scripts

Scripts that maintain the `workstation/` tree itself. Standard library only, with no install step —
they can run on a fresh clone of any machine, where nothing is set up yet.

**Use the repository's `.venv` interpreter when it is available.** These scripts import nothing outside
the standard library and can instead use the bootstrap interpreter before a venv exists: `python3` on
macOS, `python` on Windows. Every command below is written `python`, which is what the interpreter is
called on Windows and inside an activated venv; **on macOS outside a venv it is `python3`** — plain
`python` is not on `PATH` there at all. Anything else in this repo follows the venv rule.

| Script | Job |
|---|---|
| [`inventory.py`](inventory.py) | Probe this machine for the CLI toolchain and print the inventory table for [`../machines/`](../machines/) |
| [`status.py`](status.py) | Check the resolved machine's prerequisite profile and CLI toolchain, then report corrective actions |
| [`link_config.py`](link_config.py) | Report — or repair — the links that put [`../agent/`](../agent/) in `~/.claude`, and its skills in `~/.copilot/skills` |

Tests live in [`tests/`](tests/) and use `unittest`, matching the skill scripts under
`../agent/skills/*/tests/`. Two of them test no script in this folder: `test_readme_skills.py` fails when the skill
table in the root `README.md` stops matching `link_config.py`'s `SKILLS` tuple and the `skills/`
folders, and `test_python_version.py` fails when `.python-version` stops satisfying
`requires-python` in `pyproject.toml`. The pre-push hook runs this folder on every push, because the root `.pre-push-tests`
names it. Run them by hand from the repo root:

```
python -m unittest discover -s workstation/scripts/tests -t workstation/scripts/tests
```

## `inventory.py`

```
python workstation/scripts/inventory.py                   # markdown table
python workstation/scripts/inventory.py --json            # machine-readable, plus suggested_id
python workstation/scripts/inventory.py --host workstation  # print a chosen name, not the DNS one
```

`--host` exists because the output is pasted into a **committed** file and a hostname is often a
person's name. It changes the provenance line and `suggested_id`; it changes nothing that was probed.

Reads `../cli/*/install.md` frontmatter for each tool's `command` (comma-separated if it ships more than
one) and optional `version_flag`, resolves each command on `PATH`, and runs its version probe. Adding a
tool folder is enough; there is no list here to keep in sync.

**Four statuses, not two.** "Not usable here" collapses situations that call for different responses,
and collapsing them is how a quarantined binary gets reinstalled pointlessly:

| Status | Meaning | What to do |
|---|---|---|
| `installed` | ran, and reported a version | nothing |
| `absent` | nothing of that name on `PATH` | give the user the command from `install.md` |
| `blocked` | resolves on `PATH`, but the OS refused to launch it | endpoint security or a broken shim — **do not reinstall**, and do not substitute a route |
| `error` | ran, but produced no version output | wrong `version_flag`, or a genuinely broken install |

A tool providing several commands takes the **worst** status of the set, so `dbml-cli` with one of its
three commands missing does not report as installed.

### Reading the output

- The version reported is the **first dotted number** in the output, which is what every tool in the
  toolchain happens to print first. A tool that leads with something else needs its own case here
  rather than a hand-edited table downstream.
- A version *lower* than the one in `install.md`'s history is a stale local install. **Record it, tell
  the user, and stop** — see [the version-currency rule](../cli/README.md#version-currency--raise-it-dont-fix-it).
  The script deliberately cannot upgrade anything.
- `--timeout` defaults to 120s because `plantuml` and `mmdc` start a JVM and a Node runtime, and
  Docling can take longer to initialise. A timeout reports `error`, not `absent`.

## `status.py`

```
python workstation/scripts/status.py
python workstation/scripts/status.py --json
python workstation/scripts/status.py --machine macos-workstation
```

Resolves the same machine note as `link_config.py`, loads common requirements from
`../dependencies.toml`, applies its `<machine>.prerequisites.toml` companion's overrides, and combines
those dependency probes with `inventory.py`. It exits non-zero only when a required dependency fails.
Authentication is deliberately not probed.

## `link_config.py`

```
python workstation/scripts/link_config.py                       # report only — writes nothing
python workstation/scripts/link_config.py --apply               # create what is missing or detached
python workstation/scripts/link_config.py --machine macos-workstation  # pick the machine note
python workstation/scripts/link_config.py --json                # machine-readable
python workstation/scripts/link_config.py --agent copilot       # instructions + skills under ~/.copilot
python workstation/scripts/link_config.py --agent claude --agent copilot  # both
python workstation/scripts/link_config.py --project             # this repo's skills, into .claude/skills
python workstation/scripts/link_config.py --hooks --agent claude --agent copilot  # also the post-edit hooks
```

**`--agent` picks whose home is linked**, repeatable, default `claude`. `copilot` links the `SKILLS`
directories into `$COPILOT_HOME/skills` and `AGENT-INSTRUCTIONS.md` as
`$COPILOT_HOME/copilot-instructions.md` (default root `~/.copilot`). VS Code reaches the same source
through `~/.claude/CLAUDE.md` when `chat.useClaudeMdFile` is enabled.
`COPILOT_HOME` is honoured only when `--home` is your real home, so a test pointing `--home` at a
scratch tree cannot be redirected by an inherited variable; `--copilot-home` overrides both.

**`--project` links this repo's own skills** — every `skills/<name>/SKILL.md` — into
`<repo>/.claude/skills/`, where Claude Code and Copilot both load them at project scope. `.claude/` is
gitignored, so a fresh clone has none. On its own it links only those; `--agent` flags alongside it add
their homes.

**`--claude-md` writes the root `CLAUDE.md`** — one line, `@AGENTS.md` — for clones where Claude Code
runs. It is a generated file, not a link, so it cannot detach: `linked` means the content matches, and
any other content reads `diverged` and is kept unless `--force`. The file is gitignored because Copilot
CLI reads `AGENTS.md` and `CLAUDE.md` both; a Copilot-only clone leaves the flag out. Like `--project`,
on its own it touches the repo only.

**`--hooks` adds the post-edit hooks**, opt-in because a hook acts on every edit. For each name in
`HOOKS` it links `workstation/agent/hooks/<name>.py` into each selected agent's `hooks/`, and for
Copilot also `<name>.copilot.json` as `hooks/<name>.json`, which is Copilot's registration. Claude's
registration is the `hooks` block in `workstation/agent/settings.json`, merged by hand — this script
never writes a settings file.

Checks every link the agent config needs: each skill named in the script's `SKILLS` tuple,
`CLAUDE.md`, and the machine note at `~/.claude/machine.md`. Exits non-zero unless all of them are
live, so it works as a check as well as a fixer. Adding a skill means adding it to `SKILLS` and
nothing else — the count is derived, never written down.

**The machine note is resolved, not derived**, so a machine file need not be named after a hostname:
`--machine <id>` wins; failing that `<platform>-<hostname>.md` if it exists; failing that the only
`<platform>-*.md` in [`../machines/`](../machines/), since one file for a platform leaves nothing to
disambiguate. Two candidates and no hostname match is reported as `no_source` rather than guessed at.

**`settings.json` is excluded structurally.** The live file carries provider configuration required for
compliance, and every link primitive replaces its target rather than merging. It is held in a
`NEVER_LINK` constant that `plan()` asserts against, so adding it back raises rather than quietly
linking it. See [`../agent/README.md`](../agent/README.md#settings-are-merged-never-linked).

### Six statuses, because "not linked" hides the dangerous case

| Status | Meaning | `--apply` |
|---|---|---|
| `linked` | destination resolves to the repo file | nothing to do |
| `missing` | nothing at the destination | creates it |
| `detached` | plain copy whose **content still matches**, or a **dangling symlink** whose target was renamed away — either way nothing has been lost | re-links it |
| `diverged` | plain copy, **content differs** — the destination holds edits the repo lacks | **skipped**; needs `--force` |
| `occupied` | destination is a real directory with files in it | **skipped**; needs `--force` |
| `no_source` | the repo has no such file, e.g. no machine note for this host | never linked |

The `detached`/`diverged` split is the point of the script. Both look identical to anything comparing
link type alone, but one is safe to overwrite and the other is reconciliation work — and getting that
wrong is how a hand-edited `~/.claude/CLAUDE.md` gets silently discarded.

### Why a script rather than the commands in `setup/`

On Windows the files are **hardlinks**, and `git checkout` replaces a tracked file instead of writing
through it. The new content lands on a new inode and the link detaches, silently, frozen at the old
content. Measured 2026-08-25:

```
before checkout: LinkType=[HardLink] content=v1
after  checkout: LinkType=[]         f.md=v2  linked.md=v1
```

So the Windows route is not one-and-done: every pull or branch switch touching those files needs
re-linking. A one-off command sequence cannot tell you it has come undone, which is what this reports.
Junctions resolve a path rather than an inode and are immune, so the skill directories never need it.

Link detection is `os.path.samefile`, which compares device and inode. Measured on NTFS with Python
3.14, that covers all three mechanisms in use: a POSIX symlink, a Windows hardlink (`st_nlink == 2`),
and a Windows directory junction all report their target's inode, while a plain copy reports neither.
One predicate, both platforms.

### Why measured rather than written

`install.md` used to carry `version_observed` and `status` in frontmatter. Both are single-valued, so on
a repo spanning several machines they can only describe whichever was looked at last — a defect the old
`cli/README.md` documented rather than fixed. Every one of the twelve claimed `status: installed` while
four were unusable on this machine. The count in a machine file is now the output of a command, which
means it can be re-derived instead of trusted.
