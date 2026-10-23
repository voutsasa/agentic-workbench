---
name: verify-docs
description: Audit a repo's documentation for claims that are no longer true, by executing a command that proves or refutes each one. Use when asked to verify, de-stale, or fact-check docs, to check install instructions and CLI flags against reality, or to find drift between what the docs say and what the tools, paths, registries and git state actually do. Produces an evidence table; fixes only what the evidence makes unambiguous.
author: Achilleas Voutsas
version: 0.3.0
---

# Verify docs

Documentation rots silently. A flag gets renamed, a package moves registries, a
file is relocated, a branch is merged — and the doc keeps asserting the old
thing until someone acts on it and loses an afternoon. This skill finds those
claims and settles each one with a command.

## The hard rule

**Never state a fact about an installation command, a CLI flag, a file path, git
state, or API behaviour without first executing a command that proves it. Record
the command and its real output as evidence.**

This is not a style preference. It applies to every line of the report and every
sentence you write to the user while running this skill.

- If a command cannot be run — no network, no credentials, tool not installed —
  the verdict is `UNVERIFIABLE`. It is never `VERIFIED`, and never a guess.
- If you have already asserted something and later output contradicts it, say so
  explicitly and correct the record in the same reply.
- The doc agreeing with itself is not evidence: two docs can be stale in the same
  direction.

## Run the deterministic pass first

```bash
<venv-python> <skill>/scripts/verify_claims.py --repo <repo-root>            # offline
<venv-python> <skill>/scripts/verify_claims.py --repo <repo-root> --online   # + URLs, registries
```

`<venv-python>` is the project's venv interpreter — `.venv/bin/python` on macOS,
`.venv\Scripts\python.exe` on Windows — never a global `python3`.

`verify_claims.py` settles every claim a command can settle *without a model*:
paths resolved from the correct base directory, flags found on a bounded help
ladder, versions diffed against `install.md` frontmatter or against
`pyproject.toml`/`package.json`, and — under `--online` — URLs and package
registries. It prints the same `VERIFIED`/`REFUTED`/`UNVERIFIABLE` verdicts this
skill reports, with the evidence, and exits non-zero on any `REFUTED`. It also
runs in the pre-push hook, scoped to the markdown being pushed.

Start there, always. It is free, it is reproducible, and it takes the mechanical
claims off your plate so the phases below can be spent on the ones that actually
need reading. Its README documents the tiers, the exit codes, and the two
attribution rules that keep a claim bound to the right tool:
[`scripts/README.md`](scripts/README.md).

**What it deliberately leaves to you**: every claim it marks `UNVERIFIABLE`, and
every claim the extractor cannot see at all — counts, behavioural assertions,
ordering and precedence, "X requires Y". Those are the phases below.

## Phases

Run these in order. Phase 2 is a hard stop.

### Phase 1 — Build the claims manifest

```bash
<venv-python> <skill>/scripts/extract_claims.py --repo <repo-root> --out claims.jsonl --summary
```

The corpus is `git ls-files '*.md'` minus `docs/landing-zone/` — tracked, authored
documents only. Ingested third-party pages describe someone else's tool and are
not this repo's claims to defend. Override with `--files` for a narrow run or
`--include-sources` when the user asks for everything.

Each record is one line of JSON:

| field | meaning |
| --- | --- |
| `id` | stable `C0001`-style handle used throughout the report |
| `file`, `line` | where the claim is asserted |
| `kind` | `install`, `cli_flag`, `cli_invocation`, `path`, `version`, `url`, `git` |
| `claim` | the assertion, as written |
| `verification_method` | how it will be settled |
| `verification_command` | the command to run, from the repo root |
| `status` | `PENDING` until phase 3 |

The extractor is deliberately mechanical — it finds candidates and proposes
commands, it never judges. Read the manifest yourself and add the claims it
cannot see: counts ("51 input formats"), behavioural assertions ("defaults to
LaTeX"), ordering and precedence claims, and anything asserting that one tool is
required for another. Add them as extra rows with a verification method you can
actually execute.

### Phase 2 — Show the manifest and stop

Present the manifest summary — totals by kind and by file, the claims you added
by hand, and anything you judge unverifiable before trying. **Do not run a single
verification command until the user approves the manifest.** They may want the
scope cut, and verification is the expensive half. The one exemption is the
deterministic pass above (`verify_claims.py`): it writes nothing and runs only
local `--help`/`--version` probes — plus reads, under `--online` — so it has
already run by now.

### Phase 3 — Verify

Run every approved command from the repo root. Capture stdout, stderr and exit
code verbatim; truncate long output to the decisive lines and mark the
truncation.

| kind | how it is settled |
| --- | --- |
| `install` | live registry lookup — `npm view <pkg> version`, `brew info --json=v2 <formula>`, `pip index versions <pkg>` |
| `cli_flag` | `<bin> --help` and grep for the flag; if `--help` is thin, try the man page before declaring it absent |
| `cli_invocation` | `command -v <bin>`, then run the invocation itself when it is safe and side-effect-free |
| `version` | `<bin> --version` |
| `path` | `test -e` |
| `url` | `curl -sSI -L -o /dev/null -w '%{http_code}'` |
| `git` | `git log`, `git branch --merged`, `git ls-files` |
| API behaviour | a real call against the real endpoint |

Rules that matter more than they look:

- **Re-bind before you refute.** The extractor infers which binary a document
  is about from its code blocks, and gets it wrong when a document names several
  — a `mermaid-cli` page ships `mmdc`, a PlantUML page mentions `scoop`. If a
  command fails with "not found", check whether the binary was misattributed and
  re-run against the right one before recording a verdict.
- **A missing tool refutes nothing.** If `pandoc` is not installed, a flag claim
  is `UNVERIFIABLE`, not `REFUTED`. Distinguish "the doc is wrong" from "this
  machine cannot check".
- **Never make a network or API call that writes.** Reads only. If settling a
  claim needs a write, mark it `UNVERIFIABLE` and say why.
- **A non-zero exit is evidence, not a failure.** Record it and move on; do not
  retry in a loop or route around it.
- Respect the user's scope. Do not scan outside the repo root, and never install
  anything to settle a claim.

### Phase 4 — Report

One row per claim. The table is the reply and **overrides `MAX_REPLY_CEILING`**, which is defined in
`~/.claude/CLAUDE.md`.

```markdown
| id | claim | file:line | status | evidence command | actual output |
| --- | --- | --- | --- | --- | --- |
| C0007 | pandoc supports `--wrap` | workstation/cli/pandoc/quick_start.md:34 | VERIFIED | `pandoc --help \| grep -F -- '--wrap'` | `--wrap=[auto\|none\|preserve]` |
```

`VERIFIED` — the output proves the claim. `REFUTED` — the output contradicts it.
`UNVERIFIABLE` — no command could settle it here; state the blocker.

Lead with the `REFUTED` rows. Close with counts per status, and name every file
you read so the scope is unambiguous.

### Phase 5 — Fix, narrowly

**Auto-fix only `REFUTED` claims whose correct value the evidence makes
unambiguous** — a renamed flag that `--help` names exactly, a moved path that
`git ls-files` locates uniquely, a version string printed verbatim, a redirected
URL whose target `curl` reports.

Everything else goes on a list for the user: anything needing a judgement call,
a rewrite rather than a substitution, a choice between two plausible values, or
a change to what the document is arguing. Prose is not a lookup table — if the
fix changes the meaning of a sentence rather than a token in it, propose, don't
apply.

Keep each fix to the smallest edit that makes the claim true, cite the claim id
in the change, and never batch an unrelated tidy-up into the same pass.

## Running headlessly

`scripts/verify-docs.sh` in the target repo drives this via `claude -p` with a
read-only tool set, writes `DOCS-VERIFICATION.md`, and applies no fixes. That is
the CI path — phase 5 stays interactive, because "unambiguous" is a judgement
worth a human on the other end of a pull request.

## Scripts

| script | purpose |
| --- | --- |
| `scripts/extract_claims.py` | phase 1 — markdown to JSONL claims manifest |
| `scripts/verify_claims.py` | the deterministic pass — phase 3 done mechanically, run before phase 1: one verifier per claim, a verdict each. Exits non-zero on any `REFUTED`, which is what makes it usable in the pre-push hook. |
| `tests/test_extract_claims.py` | extractor tests. `<venv-python> -m unittest discover -s tests -t tests` from the skill root — stdlib only, no dependencies |
| `tests/test_verify_claims.py` | verifier tests, same command |
