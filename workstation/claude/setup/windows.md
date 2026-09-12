# Claude Code config — setup on Windows

Puts this repo's [`../CLAUDE.md`](../CLAUDE.md) and [`../skills/`](../skills/) in place at
`~/.claude/`, so the config is versioned instead of scattered through a home directory.

**`settings.json` is not in that list, and must not be.** See *Settings: merge, do not link* below.

**Route: junctions and hardlinks, not symlinks.** `New-Item -ItemType SymbolicLink` fails with
*Administrator privilege required* under a standard account, and `ln -s` has no unelevated equivalent.
The two link types that need no elevation are **junctions** for directories and **hardlinks** for
files. Both were confirmed working non-elevated on 24 August 2026.

**Enabling Developer Mode would be a real improvement, and is the one thing worth asking IT for.** It
permits unelevated symlink creation, and a symlink resolves a *path* rather than an inode, which makes
it immune to the severance trap below — the trap that produced this repo's config drift. Measured
2026-08-25 on `EMA-PF5N4XE7`: `AllowDevelopmentWithoutDevLicense` under
`HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock` is **unset**, and symlink creation
fails accordingly. Until that changes, hardlinks are the only option for files and they need
re-applying.

Requires PowerShell 7. `$Repo` must be on the **same volume as `$HOME`** — a hardlink cannot cross
volumes.

## Stop: read this before running anything

**`CLAUDE.md` will be overwritten, and the live copy is not a subset of the repo copy.** On
`EMA-PF5N4XE7` the two have drifted in *both* directions. Reconcile them by hand before linking — see
the drift table in
[`../../machines/windows-ema-pf5n4xe7.md`](../../machines/windows-ema-pf5n4xe7.md#claude-code-config--not-installed).
Keep the union rather than picking one.

Nothing below writes `~/.claude/settings.json`. If you are adapting these commands, do not add it.

## Link it

Run from your clone. The repo root comes from git, so no path below is hard-coded.

```powershell
Set-Location C:\path\to\your\sdd-workbench
$Root = (git rev-parse --show-toplevel)
$Repo = Join-Path $Root "workstation\claude"

New-Item -ItemType Directory -Force -Path "$HOME\.claude\skills" | Out-Null

New-Item -ItemType HardLink -Force -Path "$HOME\.claude\CLAUDE.md" -Target "$Repo\CLAUDE.md"

foreach ($s in "review","python-quality","verify-docs","fix-findings") {
  New-Item -ItemType Junction -Force -Path "$HOME\.claude\skills\$s" -Target "$Repo\skills\$s"
}
```

`settings.json` is absent from that block on purpose. Adding a `New-Item -Force` line for it would
overwrite the live file, `-Force` being a replace and not a merge.

## Settings: merge, do not link

`~/.claude/settings.json` **must keep its `env` block** — `CLAUDE_CODE_USE_BEDROCK`, `AWS_REGION`,
`AWS_PROFILE` and the Bedrock-prefixed model IDs. Running under Bedrock is a compliance requirement
here, so that file is edited in place and never replaced. The repo copy holds only the shared,
non-sensitive keys, and the two are expected to differ permanently.

List the keys the live file is missing, then add them by hand:

```powershell
python -c "import json,pathlib;L=json.loads((pathlib.Path.home()/'.claude/settings.json').read_text());R=json.loads(pathlib.Path('workstation/claude/settings.json').read_text());print('\n'.join(f'add {k}: {json.dumps(v)}' for k,v in R.items() if L.get(k)!=v) or 'in sync')"
```

Leave `env` exactly as it is, and do not move it to `settings.local.json`.

## The machine note

[`../CLAUDE.md`](../CLAUDE.md) closes by telling the agent to read `~/.claude/machine.md`. Point it at
this machine's file in [`../../machines/`](../../machines/):

```powershell
$Machine = Join-Path $Root "workstation\machines\windows-$($env:COMPUTERNAME.ToLower()).md"
New-Item -ItemType HardLink -Force -Path "$HOME\.claude\machine.md" -Target $Machine
```

If no such file exists yet, create it first — see
[`../../machines/README.md`](../../machines/README.md#adding-a-machine). Do not link the macOS file as
a stand-in.

Being a hardlink, this one is subject to the severance trap below.

## The pre-push gate

**The hook cannot be linked** — git will not run a hook through a junction, and a hardlink to it is
severed by the next editor save. Copy it instead:

```powershell
Copy-Item (Join-Path $Root "workstation\claude\skills\review\scripts\pre-push") `
          (Join-Path $Root ".git\hooks\pre-push") -Force
```

A plain copy is safe **on a clone made after [`.gitattributes`](../../../.gitattributes) landed**, which
pins `eol=lf` on `pre-push` so it checks out with LF and `#!/usr/bin/env bash` resolves.

**On an older working tree it is not, and `git check-attr` will not tell you.** `eol=lf` is applied when
a file is *written* to the working tree, never retroactively, so a file checked out before the attribute
existed keeps its CRLF while `check-attr` cheerfully reports `eol: lf`. Ask about the working tree
instead:

```powershell
git ls-files --eol workstation/claude/skills/review/scripts/pre-push
```

`i/lf w/lf` is correct. **`i/lf w/crlf` means the hook will fail** with
`bad interpreter: /usr/bin/env bash^M`, and the fix is to make git rewrite the file:

```powershell
$f = "workstation\claude\skills\review\scripts\pre-push"
Remove-Item $f -Force; git checkout -- $f
```

Nothing is lost — the index already holds LF, which is why the file shows as unmodified throughout. Then
re-copy the hook. To catch every affected file at once, not just this one:

```powershell
git ls-files --eol | Select-String "w/crlf" | Where-Object { $_ -match "eol=lf" }
```

Because it is a copy, **re-run it after pulling a change to the hook.** Nothing detects that for you.

## Windows traps

- **`git checkout` severs a hardlink, and freezes the copy at the old content.** This is the trap that
  matters most, because it fires during ordinary work rather than during editing. Measured in a scratch
  repo on 2026-08-25:

  ```
  before checkout: LinkType=[HardLink] content=v1
  after  checkout: LinkType=[]         f.md=v2  linked.md=v1
  ```

  git replaces a tracked file rather than writing through it, so the new content lands on a new inode
  and `~/.claude/CLAUDE.md` keeps pointing at the old one. Nothing warns you, and the stale copy still
  looks like a valid config file. **Any `git pull`, branch switch or `git stash` that touches
  `CLAUDE.md` or a machine note detaches it.** Re-run the two hardlink commands afterwards, or just run
  `python ..\..\scripts\link_config.py --apply` from the repo root, which is idempotent and reports
  what it repaired. Junctions are immune — they resolve a path, not an inode — so the skill directories
  never need this.
- **A hardlink is severed by any writer that saves atomically — and which side you edit makes no
  difference.** Zed, VS Code and Claude Code's own `Edit` tool all write a temp file and rename it over
  the target. A hardlink is two names for one inode, so whichever name is rewritten that way gets a
  *new* inode and stops tracking the other. Editing through the repo path does not protect you; that is
  how `machine.md` was severed on `EMA-PF5N4XE7` on 2026-08-26, minutes after being linked.

  So **do not try to avoid this by choosing where to edit — re-link after editing instead:**

  ```powershell
  python ..\..\scripts\link_config.py --apply
  ```

  Junctions are immune, so the skill directories never need it. `settings.json` is exempt because it is
  never linked — edit that one in `~/.claude/` only.
- **Assume both hardlinks are broken and check.** Between git operations and atomic saves, they detach
  during routine work rather than exceptionally. This is why the *Verify* step below is not optional,
  and why `link_config.py` exists instead of a one-time setup command.
- **`core.symlinks` is `false`.** A symlink committed to this repo would check out here as a text file
  containing its target path. Nothing in the repo relies on one.

## Verify

One command checks every link and writes nothing:

```powershell
python (Join-Path $Root "workstation\scripts\link_config.py")
```

It exits non-zero unless all six are live, distinguishes a *detached* copy from a *diverged* one, and
leaves `settings.json` alone. Add `--apply` to repair; a diverged `CLAUDE.md` is reported and skipped
rather than overwritten, because that is reconciliation work.

The underlying checks, if you want them by hand. `LinkType` reports `HardLink` or `Junction` when a link
is live and an **empty string** when the path is a plain copy — that empty string is exactly what a
severed hardlink looks like, and is how the drift above was found.

```powershell
foreach ($p in "$HOME\.claude\CLAUDE.md","$HOME\.claude\machine.md") {
  "{0,-45} LinkType=[{1}]" -f $p, (Get-Item $p -ErrorAction SilentlyContinue).LinkType
}
Get-ChildItem "$HOME\.claude\skills" | Select-Object Name, LinkType
```

Content is the real test, since a link can be live and still point at the wrong file:

```powershell
(Get-FileHash "$HOME\.claude\CLAUDE.md").Hash -eq (Get-FileHash "$Repo\CLAUDE.md").Hash
```

Then start a session and confirm the four skills are offered.

### `ls` shows only half of this, and that is not a fault

Unlike the macOS route, where all six are symlinks and every one prints `->`, the two link kinds here
look completely different to `ls`:

```
$ ls -la ~/.claude ~/.claude/skills
-rw-r--r-- 2 …  7087 CLAUDE.md                    <- linked, no arrow
-rw-r--r-- 2 … 16019 machine.md                   <- linked, no arrow
-rw-r--r-- 1 …   432 settings.json                <- correctly not linked
lrwxrwxrwx 1 …    80 review -> /c/Users/…/review  <- linked, with arrow
```

**A hardlink can never print an arrow.** It is a second *name* for one inode, not a pointer to a path, so
there is no target for `ls` to show. The column that matters is the **link count** immediately after the
permissions: `2` means linked, `1` means a plain file. Junctions do print `->`, because MSYS `ls` maps
them onto symlinks.

So *"I ran `ls` and saw no symlinks"* is the expected result at the top level and proves nothing either
way. `link_config.py`, `LinkType`, or the link count are the checks that answer the question.

## Not tracked

Plugins — reinstall with `/plugin`. Currently `pyright-lsp` from the `claude-plugins-official`
marketplace (`anthropics/claude-plugins-official`).

Everything else deliberately left out of git is listed in [`../README.md`](../README.md#deliberately-not-tracked).
