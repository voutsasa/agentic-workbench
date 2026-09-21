# verify-docs/scripts

Stdlib-only Python. **No model is called from here**, and no claim's text ever
reaches a shell — verifiers are built from structured fields and run with
`shell=False`, so a command example in a document cannot execute itself.

| File | Purpose |
|---|---|
| `extract_claims.py` | Finds candidate claims and *proposes* a command for each. Decides nothing. |
| `verify_claims.py` | Executes a verifier per claim and returns a verdict. Exits non-zero on any `REFUTED`. |
| `../tests/test_extract_claims.py` | 35 tests. `python3 -m unittest discover -s tests` from the skill root. |
| `../tests/test_verify_claims.py` | 125 tests, including both regression classes below. |

## verify_claims.py

```bash
python3 verify_claims.py --repo .                      # offline tier, whole repo
python3 verify_claims.py --repo . --files a.md b.md    # just these documents
python3 verify_claims.py --repo . --kind version       # one claim kind
python3 verify_claims.py --repo . --online             # add URLs and registries
python3 verify_claims.py --repo . --strict             # UNVERIFIABLE fails too
python3 verify_claims.py --repo . --json               # machine-readable
python3 verify_claims.py --repo . --no-allow-file      # ignore both allow files
```

### The two tiers

| Tier | Kinds | Needs | Runtime here |
|---|---|---|---|
| offline (default) | `path`, `cli_flag`, `cli_invocation`, `version` | local filesystem and binaries | scoped runs are typically sub-second; full runs vary by corpus and toolchain |
| online (`--online`) | `url`, `install` | the network | minutes, and someone else's uptime |

The split is the reason this can gate a push at all. A pre-push hook that fetches
179 URLs fails when GitHub has a bad minute, and a gate that fails for reasons
unrelated to the change is one people learn to bypass.

**A subprocess probe waits 120 seconds** (`HELP_TIMEOUT`, `VERSION_TIMEOUT`), which is
deliberately far more than any tool needs. A timeout is indistinguishable from *the tool
printed no help*, so a slow binary turns a true claim into a refuted one: at the former
20-second limit, `docling` — 17s for `--version`, 20s for `--help` on Windows — gave the
same claim different verdicts from one run to the next. The ceiling is only ever paid by a
tool that is actually hung, and each binary is probed once per run and cached.

### Verdicts and exit codes

| Verdict | Meaning | Effect |
|---|---|---|
| `VERIFIED` | a command proved the claim | — |
| `REFUTED` | a command contradicted it | **exit 1** |
| `UNVERIFIABLE` | no command could settle it here | counted, printed, does not fail — unless `--strict` |

| Code | Meaning |
|---|---|
| `0` | nothing refuted |
| `1` | at least one `REFUTED` (or, under `--strict`, one `UNVERIFIABLE`) |
| `2` | the gate could not run — empty scope, no claims extracted, unreadable tree |

`2` is deliberately separate from `1`, matching `repo_check.py`. A gate that
reports success because the checker broke is worse than no gate.

`UNVERIFIABLE` must not fail by default. A tool that is simply not installed on
this machine says nothing about whether the documentation is right, and blocking
a push over it teaches people to reach for `--no-verify`.

### Determinism

Same inputs, same output, every run:

- No model, at any step.
- Claim order is sorted by `(file, line, kind, claim)` before ids are assigned.
- `--workers` changes only the wall clock. Every claim's verdict depends on that
  claim alone, so `--workers 1` and the default 8 produce byte-identical output;
  the test suite and a `cmp` of two `--json` runs both hold this.
- Exit status of a verifier subprocess is ignored on purpose. Many tools print
  help and exit 1; what is under test is the text, not the status.

## Two regressions worth knowing about

Both are silent failures — a wrong answer looks exactly like a right one until
someone follows the document and it does not work.

### 1. Which directory a relative path resolves from

A link written inside `workstation/cli/pandoc/quick_start.md` means the file
beside that document, and nothing else:

```text
./NOTES.md   ->  workstation/cli/pandoc/NOTES.md      correct
             ->  NOTES.md at the repo root            wrong, and it passes
```

A resolver that also tries the repo root finds an unrelated file there and
passes a link that is dead in a browser and dead on GitHub.

So an anchored path — `./` or `../` — resolves against its own document's
directory and is given **no fallback**. Only an unanchored token, this repo's
house style for naming a path in prose, may try the repo root first and the
document's directory second; the evidence column names which base resolved it.

One exception, and it is not a weakening: an anchored path *inside a fenced
shell block* is `UNVERIFIABLE`, because the working directory it assumes is
established in prose rather than in data. `ln -sf ../../…/pre-push .git/hooks/`
is relative to the link, not to the page.

An **unanchored** path carries a second question — whether its root is knowable
at all. `workstation/mcp/README.md` links correctly to `workstation/cli/README.md`
but labels the link `cli/README.md`, written relative to `workstation/`. The
label resolves from neither base. Refuting it blames the document for an implicit base it never
claimed, and inventing the base would pass a broken path in any repo where `cli/`
means something else. So when the first segment exists at neither base, the
verdict is `UNVERIFIABLE`. This is `repo_check.py`'s rule too — its `bare_paths`
check is scoped by `prefixes` for the same reason: a path is checkable only when
its root is known. A path under a root that *does* exist is still refuted.

### 2. Binding a claim to the right tool when two look alike

Version numbers collide — three binaries here sit on `10.1.1` — and a page about
one tool routinely mentions another. Two rules keep attributions honest:

- **Versions bind to frontmatter, never to prose.** `install.md` declares
  `command:` and `version_observed:`; the verifier uses those. Inferring the
  subject from the prose mis-binds three of twelve tools in this repo:
  `mermaid-cli` ships `mmdc` not `mermaid`, `dbml-cli` ships three binaries and
  none is `dbml`, and `plantuml-cli`'s install page mentions `scoop` often enough
  that PlantUML's version gets attributed to the installer.
- **An inferred subject may be confirmed, never refuted.** A flag named in prose
  rather than in an invocation has no certain owner. The `pdf-deliverable` skill
  compares pandoc with WeasyPrint, so WeasyPrint's `--pdf-variant` is attributed
  to pandoc — whose help has never listed it. That is `UNVERIFIABLE`. A flag that
  appears in a real command line on the line is refutable.

## Finding the flag a document names

`--help` is not universal, so the verifier climbs a bounded ladder before
refuting anything: `--help`, then `-h` (`git diff --help` opens a man page and
lists nothing, while `git diff -h` prints the flags), then `--help-extra` (where
tesseract keeps `--psm`), then the subcommands the tool advertises in its own
help — capped at six, and only those it actually names. That last rung is what
finds `--from` under `docling convert` after docling moved its options down a
level.

On each rung the flag is matched plainly first, then in git's optional-negation
bracket form: `git status -h` prints `--[no-]porcelain[=<version>]`, and a
substring search for `--porcelain` misses a flag that plainly exists and exits 0.
Only that one form is tolerated, and only for the flag's own stem — `--porcelain`
and `--no-porcelain` both match that line, `--porcelainish` does not — so a flag
absent in every form is still refuted.

`npx` and its siblings are never run: answering the question would install a
package, and a push gate must not change the machine.

## Exempting a path: `.verify-claims-allow`

Some paths are *meant* not to exist. `python-quality/SKILL.md` tabulates the
files it writes into a target project against the templates that generate them;
`drawio-mcp/setup.md` quotes upstream's `.claude/settings.json` snippet in order
to say do not follow it. Neither asserts that the path is here.

Those go in `.verify-claims-allow` at the repo root — one glob per line, `#` for
comments:

```text
# Files python-quality writes into a TARGET project, not this repo's files.
.github/**
```

The file is repo-local and tracked deliberately. The pre-push hook lives in the
globally symlinked skills tree, so **one copy of it serves every repo that links
it** — a glob hard-coded in the hook would silently exempt paths in unrelated
repos. Keeping globs here means they show up in a diff, apply to one repo, and
are inherited by nothing. No file means no globs.

`verify_claims.py` reads it by default; `--allow GLOB` adds to it, and
`--no-allow-file` ignores it — along with `.verify-flags-allow` below. Running
with `--no-allow-file` is the way to see what the exemptions are actually hiding.
The number it uncovers is not worth writing down here: most of the globs cover the
gitignored corpus, so it tracks how much of `SOURCES.md` this machine has ingested
rather than anything about the checker.

Only exempt a path that is meant not to exist. A path that should exist and does
not is a defect to fix.

## Exempting a flag: `.verify-flags-allow`

A sibling file, same repo-local reasoning, different question. `--staged` is a
working synonym of `git diff --cached`, but `git diff -h` never prints the string
and the full `git diff --help` is a man page — so no rung of the ladder can reach
it, and the verifier refuses a push over a command that works.

One `<command> <flag>` per line, `#` for comments:

```text
# A working synonym of --cached that no abbreviated help prints.
git diff --staged
```

It is deliberately not part of `.verify-claims-allow`: that file is pinned to
paths *meant not to exist here* ([`AGENTS.md`](../../../../../AGENTS.md)
§ *Invariants*), and a flag that exists and works is the opposite case.

Three properties keep it honest:

- **Bound to the whole command.** `git diff --staged` exempts nothing under
  `git log`. The key is the same help subject the verifier resolved, so a
  subcommand's exemption never travels.
- **It only downgrades a refutation.** The check is the last rung, after every
  probe. A flag the help does document stays `VERIFIED`, listed or not.
- **A line naming no flag exempts nothing**, so a typo fails closed rather than
  silencing a command's whole surface.

Only exempt a flag that **works** but that no help text documents. A flag the tool
does not have is a defect in the document.

## Saying what a run is waiving

Every run announces both files before it starts, one block per source:

```
verify_claims: 2 exemption(s) from .verify-claims-allow:
               .agents/skills/**
               docs/landing-zone/**
verify_claims: 1 exemption(s) from .verify-flags-allow:
               git diff --staged
```

The counts are this repo's shape, not its current totals — it has more path globs
than the two shown.

On stderr, so it does not enter a report; suppressed by `--quiet` and `--json`,
which scripts read; silent under `--no-allow-file`, which waives nothing.

**Keyed by source, not flattened.** A glob given as `--allow` gets its own block,
because reporting it under the repo's file name would be a small lie of exactly
the kind this notice exists to prevent.

The pre-push hook used to parse `.verify-claims-allow` itself and pass each glob
back as `--allow`, and printed its own count. It no longer does either: one piece
of code reads the policy, applies it, and announces it, so the report and the
notice cannot disagree. The hook keeps *scope* — which markdown is in the push —
and this script owns exemptions end to end.

### Two refutations that are meant to stand

`--online` reports two, both in documentation warning *against* a command:

```
skills/ingest-source/references/workstation-tooling.md:124 brew install sem   ->  Homebrew has no package sem
workstation/cli/sem-cli/install.md:29                     brew install sem   ->  Homebrew has no package sem
```

The evidence is correct — `sem` is not a core formula, `sem-cli` is — and so is
the documentation, which says exactly that: *"`brew install sem` installs
`schema-evolution-manager`, an unrelated Postgres migration tool."* The extractor
cannot tell an instruction from a warning; both read as `brew install sem` in a
code span.

These are accepted, not exempted. An exemption that hides a true negative is
worse than a report someone has read once, and nothing is gated by them: install
claims are online-tier only, and the pre-push hook is offline. If a mechanism for
this is ever wanted, it should mark the *claim* as a documented anti-pattern at
extraction time, not silence the verifier downstream.

## The pre-push hook

Wired in [`../../review/scripts/pre-push`](../../review/scripts/pre-push),
alongside `repo_check.py`. It verifies **only the markdown being pushed** —
under a second for a typical change. A claim
you did not touch is a claim you did not break; run the full sweep on demand.

```bash
# edit .verify-claims-allow     # exempt a path that is meant not to exist
# edit .verify-flags-allow      # exempt a flag no help text documents
SKIP_VERIFY_CLAIMS=1 git push   # skip claim verification, keep repo_check
SKIP_REPO_CHECK=1 git push      # skip both checks in this hook
git push --no-verify            # skip every hook in the repository
```

Reach for the narrowest one that unblocks you.
