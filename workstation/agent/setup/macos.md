# Agent config — setup on macOS

Puts this repo's [`../AGENT-INSTRUCTIONS.md`](../AGENT-INSTRUCTIONS.md) and [`../skills/`](../skills/) in place at
`~/.claude/`, so the config is versioned instead of scattered through a home directory.

**`settings.json` is not in that list, and must not be.** See *Settings: merge, do not link* below.

**Route: symlinks.** `ln -s` needs no elevation on macOS, so every link is the same kind and the
Windows junction/hardlink workaround — and its severed-link failure mode — does not apply here. macOS
has its own: a symlink whose target has been *renamed* still exists but resolves to nothing. See
*Verify*.

**`python3`, not `python`.** macOS ships no `python` on `PATH`, so every command here that the other
platform writes as `python` is `python3`. These two scripts are stdlib-only and are the deliberate
exception to the venv rule — see [`../../scripts/README.md`](../../scripts/README.md).

## Before you start

**Linking overwrites `~/.claude/CLAUDE.md`.** If the live copy has been edited directly it is not a
subset of the repo copy, so compare the two and keep the union before running anything:

```sh
diff ~/.claude/CLAUDE.md "$(git rev-parse --show-toplevel)/workstation/agent/AGENT-INSTRUCTIONS.md"
```

Nothing below writes `~/.claude/settings.json`. If you are adapting these commands, do not add it.

## Link it

Run from your clone. `link_config.py` takes the repo root from its own location and the skill list from
its `SKILLS` tuple, so nothing below hard-codes a path or a skill name. The hand-written `ln -sfn` loop
this replaced still named four skills after the tuple had grown to six.

```sh
cd /path/to/your/agentic-workbench
python3 workstation/scripts/link_config.py --apply --hooks
```

It creates one symlink per global skill in `~/.claude/skills/`, `AGENT-INSTRUCTIONS.md` →
`~/.claude/CLAUDE.md`, the same file → `~/.agentic-workbench/AGENTS.md` (the one assistant-neutral
copy, for an integration with no agent-specific route yet), the machine note →
`~/.agentic-workbench/machine.md` (see *The machine note*), and — because of `--hooks` —
`hooks/ruff_on_edit.py` into `~/.claude/hooks/` (opt-in, since a hook acts on every edit).
Re-running is safe: a live link is left alone, a stale one is replaced, and a destination holding content
the repo lacks is reported and skipped. Add `--agent copilot` to link the same skills,
`copilot-instructions.md`, and (with `--hooks`) the Copilot hook registration under `~/.copilot`, and
`--project` for this repo's own skills.

`settings.json` is not among them, and cannot be: the script refuses to plan a link for it, since a
symlink is not a merge.

## Settings: merge, do not link

`~/.claude/settings.json` is **edited in place and never replaced**. Follow
[`../README.md` § *The merge procedure*](../README.md#the-merge-procedure); its delta is
`uv run python workstation/scripts/settings_delta.py`.

## The machine note

[`../AGENT-INSTRUCTIONS.md`](../AGENT-INSTRUCTIONS.md) tells the agent to read `~/.agentic-workbench/machine.md`. Point it at
this machine's file in [`../../machines/`](../../machines/) — `link_config.py` will do it, and finds the
right file without being told when there is only one for this platform:

```sh
python3 workstation/scripts/link_config.py --apply
```

Name the file explicitly when the folder holds more than one macOS machine:

```sh
python3 workstation/scripts/link_config.py --apply --machine macos-workstation
```

If no such file exists yet, create it first — see
[`../../machines/README.md`](../../machines/README.md#adding-a-machine). Do not link the Windows file
as a stand-in.

## The pre-push gate

The `review` skill ships a pre-push documentation gate. Link it from each repo that should run it:

```sh
cd /path/to/your/agentic-workbench
ln -sfn ../../workstation/agent/skills/review/scripts/pre-push .git/hooks/pre-push
```

The path is relative to `.git/hooks/`, which is why it climbs two levels. In a repo other than this
one, use an absolute path to the script instead.

## Verify

Do not assume it worked — re-run the report, which writes nothing.

```sh
python3 "$(git rev-parse --show-toplevel)/workstation/scripts/link_config.py"
```

That checks every Claude link, writes nothing, and exits non-zero unless every one is live. If you
also linked Copilot, add `--agent copilot`; use `--agent claude --agent copilot` to check both homes.
`--apply` repairs what is missing; a destination whose content has diverged from the repo is reported
and skipped rather than overwritten. It never touches `settings.json`.

By hand, every path should print as `->` pointing into your clone:

```sh
ls -l ~/.claude/CLAUDE.md ~/.agentic-workbench/machine.md ~/.claude/skills/
```

**A symlink into a renamed directory still prints, but resolves to nothing.** This repo's config used to
live in `workstation-agent/`; if this machine carries links from that era they are dangling. `ls -l`
shows the stale target, and `link_config.py` reports `detached`, naming it — then `--apply` replaces it.
See [`../../machines/macos-workstation.md`](../../machines/macos-workstation.md#claude-code-config).

Then run `python3 workstation/scripts/inventory.py` to record the toolchain, and start a session to
confirm the skills are offered.

## Not tracked

Plugins — reinstall with `/plugin`. Currently `pyright-lsp` from the `claude-plugins-official`
marketplace (`anthropics/claude-plugins-official`).

Everything else deliberately left out of git is listed in [`../README.md`](../README.md#deliberately-not-tracked).
