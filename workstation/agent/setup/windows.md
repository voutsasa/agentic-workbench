# Agent config — setup on Windows

Puts this repo's [`../AGENT-INSTRUCTIONS.md`](../AGENT-INSTRUCTIONS.md) and [`../skills/`](../skills/) in place at
`~/.claude/`, so the config is versioned instead of scattered through a home directory.

**`settings.json` is not in that list, and must not be.** See *Settings: merge, do not link* below.

**Route: junctions for directories, generated copies for files — no symlinks.** `New-Item
-ItemType SymbolicLink` fails with *Administrator privilege required* under a standard account,
and `ln -s` has no unelevated equivalent. **Junctions** need no elevation and resolve a *path*
rather than an inode, so a directory link survives everything below unharmed. A file artefact
(`CLAUDE.md`, `copilot-instructions.md`, `machine.md`, `agentic-workbench/AGENTS.md`) used to be a
**hardlink** instead — the one unelevated file-link primitive — but a hardlink shares an inode
with its source, so it severs the moment anything replaces that inode: `git checkout`, or any
atomic-saving editor (Zed, VS Code, Claude Code's own `Edit` tool). That severance is what
produced this repo's config drift, and is why these are now a **generated copy** instead: written
fresh by `link_config.py --apply`, compared by content rather than by inode, with nothing to
sever. The cost is the one a hardlink already had in practice — re-run `--apply` after editing the
source — not a new one.

**Enabling Developer Mode is still worth asking IT for**, since it permits unelevated symlink
creation and would let these files become real, live-updating links too. Measured 2026-08-25 on
`EMA-PF5N4XE7`: `AllowDevelopmentWithoutDevLicense` under
`HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock` is **unset**, and symlink creation
fails accordingly — but this is no longer blocking anything, just a convenience foregone.

Requires PowerShell 7. A generated copy has no cross-volume restriction, unlike the hardlink it
replaced, so the clone no longer needs to sit on the same volume as `$HOME` for these artefacts.

## Stop: read this before running anything

**`CLAUDE.md` will be overwritten, and the live copy is not a subset of the repo copy.** On
`EMA-PF5N4XE7` the two have drifted in *both* directions. Reconcile them by hand before linking — see
the drift table in
[`../../machines/windows-ema-pf5n4xe7.md`](../../machines/windows-ema-pf5n4xe7.md#claude-code-config--not-installed).
Keep the union rather than picking one.

Nothing below writes `~/.claude/settings.json`. If you are adapting these commands, do not add it.

## Link it

Run from your clone. `link_config.py` takes the repo root from its own location and the skill list from
its `SKILLS` tuple, so nothing below hard-codes a path or a skill name. The hand-written `New-Item` loop
this replaced still named four skills after the tuple had grown to six.

```powershell
Set-Location C:\path\to\your\agentic-workbench
$Root = (git rev-parse --show-toplevel)
python (Join-Path $Root "workstation\scripts\link_config.py") --apply --hooks
```

It uses a junction per global skill in `$HOME\.claude\skills`, and a generated copy for
`$HOME\.claude\CLAUDE.md`, `$HOME\.agentic-workbench\machine.md` and
`$HOME\.agentic-workbench\AGENTS.md` — plus, because of `--hooks`, `hooks/ruff_on_edit.py` into
`$HOME\.claude\hooks\` (opt-in, since a hook acts on every edit; that copy too). A diverged
`CLAUDE.md` is reported and skipped rather than overwritten — reconcile it first, per the section
above. Add `--agent copilot` to link the same skills, `copilot-instructions.md`, and (with
`--hooks`) the Copilot hook registration under `~/.copilot`, and `--project` for this repo's own
skills.

`settings.json` is not among them, and cannot be: the script refuses to plan a link for it, since a
link is a replace and not a merge.

## Settings: merge, do not link

`~/.claude/settings.json` is **edited in place and never replaced**. Follow
[`../README.md` § *The merge procedure*](../README.md#the-merge-procedure); its delta is
`uv run python workstation/scripts/settings_delta.py`.

## The machine note

[`../AGENT-INSTRUCTIONS.md`](../AGENT-INSTRUCTIONS.md) tells the agent to read
`~/.agentic-workbench/machine.md`. The `link_config.py --apply` command in *Link it* creates that
generated copy alongside the skills and resolves the right file in
[`../../machines/`](../../machines/), including an explicitly named `--machine` file or
the sole Windows machine file.

If it reports `no_source`, create the machine file first — see
[`../../machines/README.md`](../../machines/README.md#adding-a-machine). Do not link the macOS file as
a stand-in.

Being a generated copy, this one can go stale after a machine-note edit, but can't sever — see
*Windows traps* below.

## The pre-push gate

**The hook cannot be linked** — git will not run a hook through a junction, and a hardlink to it is
severed by the next editor save. So copy the shim, `pre-push.windows`, which does nothing but run the
tracked `pre-push` from the working tree:

```powershell
Copy-Item (Join-Path $Root "workstation\agent\skills\review\scripts\pre-push.windows") `
          (Join-Path $Root ".git\hooks\pre-push") -Force
```

**Copy it once.** A pull that changes the hook reaches it through the shim, so there is nothing to
re-copy — unlike a copy of the hook itself, which went stale on the first such pull. If the tracked hook
is missing, the shim refuses the push rather than letting it through ungated.

A plain copy is safe **on a clone made after [`.gitattributes`](../../../.gitattributes) landed**, which
pins `eol=lf` on `pre-push` and `pre-push.windows` so both check out with LF and bash can read them.

Confirm it is there rather than assuming — `.git/hooks/` is not tracked, so a fresh clone has only git's
`.sample` files and every push from it is ungated and silent about it:

```powershell
Test-Path .git\hooks\pre-push
```

**On an older working tree it is not, and `git check-attr` will not tell you.** `eol=lf` is applied when
a file is *written* to the working tree, never retroactively, so a file checked out before the attribute
existed keeps its CRLF while `check-attr` cheerfully reports `eol: lf`. Ask about the working tree
instead:

```powershell
git ls-files --eol workstation/agent/skills/review/scripts/pre-push workstation/agent/skills/review/scripts/pre-push.windows
```

`i/lf w/lf` is correct. **`i/lf w/crlf` means the hook will fail** with
`bad interpreter: /usr/bin/env bash^M`, and the fix is to make git rewrite the file:

```powershell
$f = "workstation\agent\skills\review\scripts\pre-push"
Remove-Item $f -Force; git checkout -- $f
```

Nothing is lost — the index already holds LF, which is why the file shows as unmodified throughout. If
it was the shim, copy it again. To catch every affected file at once, not just this one:

```powershell
git ls-files --eol | Select-String "w/crlf" | Where-Object { $_ -match "eol=lf" }
```

## Git HTML help in Copilot sessions

Git for Windows can configure `help.format=html`. In that mode, `git <subcommand> --help` opens the
installed HTML manual in the default browser. A Copilot session that probes several Git subcommands
can therefore create many `file:///.../git-<subcommand>.html` tabs without a Git failure.

Check without opening a manual:

```powershell
git config --show-origin --get help.format
```

**Use `git <subcommand> -h`, not `git <subcommand> --help`, in Copilot instructions, hooks, and
deterministic checks.** `-h` writes concise usage to the terminal and does not invoke the browser.
The tracked `verify_claims.py` verifier follows this rule for Git subjects; use the shim above so a
push runs that current tracked implementation instead of a copied, stale hook.

Do not change `help.format` to `man` as an untested blanket workaround. Some Windows Git
installations do not include a `man` viewer, which turns an unwanted browser tab into a failed help
request. `core.pager` and `GIT_PAGER` do not control the HTML-help browser behavior.

## Windows traps

- **Edit the repo source, then re-run `--apply` — the generated copies don't update themselves.**
  `CLAUDE.md`, `copilot-instructions.md`, `machine.md` and `agentic-workbench/AGENTS.md` are
  written once, from whatever `AGENT-INSTRUCTIONS.md` or the machine note held at the time. An
  edit to the repo source, a `git pull`, a branch switch — anything that changes the source and
  not yet the destination — leaves the destination reading `diverged` until you run:

  ```powershell
  python workstation\scripts\link_config.py --apply
  ```

  idempotent, and it reports what it repaired. This is the one step a *real* link (the skill
  junctions) never needed, and these files don't either, in the sense that matters: nothing can
  silently break them the way the hardlink they replaced could — see *Settled* in
  [`../README.md`](../README.md) for why that was true before 2026-10-12 and isn't now.
- **A `machine.md` reported `diverged` after a repo doc update is usually pure staleness, not a
  conflicting edit.** Diff it against the repo source first; if the only differences trace to the repo
  side, `Copy-Item <repo path> ~/.agentic-workbench/machine.md -Force` is safe. Still diff before copying —
  `link_config.py` cannot tell repo drift apart from a local note you added, so it skips either way.
- **`core.symlinks` is `false`.** A symlink committed to this repo would check out here as a text file
  containing its target path. Nothing in the repo relies on one.

## Verify

One command checks every link and writes nothing:

```powershell
python (Join-Path $Root "workstation\scripts\link_config.py")
```

It checks every Claude link and exits non-zero unless every one is live. If you also linked Copilot,
add `--agent copilot`; use `--agent claude --agent copilot` to check both homes. It distinguishes a
*detached* copy from a *diverged* one and leaves `settings.json` alone. Add `--apply` to repair; a
diverged `CLAUDE.md` is reported and skipped rather than overwritten, because that is reconciliation
work.

The underlying check, if you want it by hand. `LinkType` reports `Junction` for a skill directory;
for `CLAUDE.md`, `copilot-instructions.md`, `machine.md` and `agentic-workbench/AGENTS.md` it is an
**empty string by design** — they are generated copies, not links, so there is no `LinkType` to
report. Content is what actually answers "is this current":

```powershell
Get-ChildItem "$HOME\.claude\skills" | Select-Object Name, LinkType
(Get-FileHash "$HOME\.claude\CLAUDE.md").Hash -eq (Get-FileHash (Join-Path $Root "workstation\agent\AGENT-INSTRUCTIONS.md")).Hash
```

`True` means the copy matches the repo source right now. `link_config.py`'s own report says the
same thing without the manual hash — `linked` is that comparison already done.

Then start a session and confirm every skill is offered.

### `ls` shows only the junctions, and that is not a fault

```
$ ls -la ~/.claude ~/.claude/skills
-rw-r--r-- 1 …  7087 CLAUDE.md                    <- a generated copy, no arrow, link count 1
-rw-r--r-- 1 …   432 settings.json                <- correctly not linked, same look
lrwxrwxrwx 1 …    80 review -> /c/Users/…/review  <- a junction, MSYS `ls` prints it as `->`
```

A generated copy and a plain file you created by hand look **identical** to `ls` — same mode, same
link count. That's expected, not a fault: there's no mechanism difference to show, only content,
which `ls` doesn't check. `link_config.py` or the hash comparison above are what answer the
question; `ls` only tells you something is a junction, never that a file is current.

## Not tracked

Plugins — reinstall with `/plugin`. Currently `pyright-lsp` from the `claude-plugins-official`
marketplace (`anthropics/claude-plugins-official`).

Everything else deliberately left out of git is listed in [`../README.md`](../README.md#deliberately-not-tracked).
