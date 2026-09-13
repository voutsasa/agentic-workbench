# Agent config — setup on macOS

Puts this repo's [`../AGENT-INSTRUCTIONS.md`](../AGENT-INSTRUCTIONS.md) and [`../skills/`](../skills/) in place at
`~/.claude/`, so the config is versioned instead of scattered through a home directory.

**`settings.json` is not in that list, and must not be.** See *Settings: merge, do not link* below.

**Route: symlinks.** `ln -s` needs no elevation on macOS, so all six links are the same kind and the
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

Run from your clone. Nothing below hard-codes a path — the repo root comes from git, so this works
wherever you cloned it.

```sh
cd /path/to/your/agentic-workbench
REPO="$(git rev-parse --show-toplevel)/workstation/agent"

mkdir -p ~/.claude/skills
ln -sfn "$REPO/AGENT-INSTRUCTIONS.md" ~/.claude/CLAUDE.md

for skill in review python-quality verify-docs fix-findings; do
  ln -sfn "$REPO/skills/$skill" ~/.claude/skills/"$skill"
done
```

`-n` matters: without it, re-running turns the second link into `~/.claude/skills/review/review`
instead of replacing it.

`settings.json` is absent from that block on purpose. Adding an `ln -sfn` line for it would replace the
live file, since a symlink is not a merge.

## Settings: merge, do not link

`~/.claude/settings.json` is **edited in place and never replaced**, because Claude Code writes to it
itself and a link or a copy would drop whatever it had written. On a machine that is provider-bound it
also carries an `env` block — `CLAUDE_CODE_USE_BEDROCK`, `AWS_REGION`, `AWS_PROFILE` and the
provider-prefixed model IDs — which this repo does not hold; whether this machine is one of those is in
its file under [`../../machines/`](../../machines/), not here. The repo copy holds only the shared,
non-sensitive keys.

List the keys the live file is missing, then add them by hand:

```sh
python3 -c "import json,pathlib;L=json.loads((pathlib.Path.home()/'.claude/settings.json').read_text());R=json.loads(pathlib.Path('workstation/agent/settings.json').read_text());print('\n'.join(f'add {k}: {json.dumps(v)}' for k,v in R.items() if L.get(k)!=v) or 'in sync')"
```

Leave `env` exactly as it is, and do not move it to `settings.local.json`.

## The machine note

[`../AGENT-INSTRUCTIONS.md`](../AGENT-INSTRUCTIONS.md) closes by telling the agent to read `~/.claude/machine.md`. Point it at
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

Do not assume it worked — `ln -sfn` is quiet on success and on several kinds of near-miss.

```sh
python3 "$(git rev-parse --show-toplevel)/workstation/scripts/link_config.py"
```

That checks all six links, writes nothing, and exits non-zero unless every one is live. `--apply`
repairs what is missing; a destination whose content has diverged from the repo is reported and skipped
rather than overwritten. It never touches `settings.json`.

By hand, every path should print as `->` pointing into your clone:

```sh
ls -l ~/.claude/CLAUDE.md ~/.claude/machine.md ~/.claude/skills/
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
