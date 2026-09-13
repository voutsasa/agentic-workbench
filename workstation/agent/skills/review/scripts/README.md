# review/scripts

Repeatable actions for the `review` skill. Stdlib-only Python and POSIX shell —
nothing to install, and **no model is called from here**.

| File | Purpose |
|---|---|
| `repo_check.py` | Deterministic documentation gate. Exits non-zero on any violation. |
| `checks.toml` | The rules it enforces — glossary terms, header schema, scope. Tune this, not the script. |
| `pre-push` | Git hook wrapper around `repo_check.py` **and** `verify-docs`'s `verify_claims.py`. Versioned here; symlinked into `.git/hooks/`. |
| `../tests/test_repo_check.py` | `python3 -m unittest discover -s tests` from the skill root. 92 tests, no network. |

## repo_check.py

```bash
python3 repo_check.py                 # check the repo containing this script
python3 repo_check.py --json          # machine-readable violations
python3 repo_check.py --list-files    # what is in scope, then stop
```

Four checks, each toggled in `checks.toml`:

1. **`links`** — every relative markdown link, image and reference definition resolves to
   a file on disk. Percent escapes are decoded (`Non-functional%20requirements.md` is a
   real file), targets inside fenced code are skipped, and placeholders (`<tool>/`, `...`,
   `{name}`) are not treated as paths. External `http(s)` links are never fetched: a push
   must not depend on someone else's uptime.
2. **`bare_paths`** — a repo path written in prose, or far more often in backticks,
   still resolves on disk. `links` only ever sees `[text](target)`, so a folder named
   in a sentence reaches no check at all — which is how a document ends up sending a
   reader to a directory renamed a month ago. Scoped by `prefixes` rather than applied
   to every slash-bearing token, because a path is checkable only when its root is
   known; `allow_globs` exempts the gitignored `reference.md` pages, which are absent
   on a fresh clone by design. Link *targets* are left to `links` — one broken path
   reported twice helps nobody — but link *text* is checked, since a label naming a
   stale path is a defect even when the target beside it resolves.
3. **`terminology`** — house glossary, word-boundary and case-insensitive, including
   inflections. Code fences and inline code are exempt. Per-rule `allow_context` phrases
   carve out legitimate uses, and are matched against the **whole original line**,
   including link targets — a `[Download]` pointing at `imagemagick.org` names their page,
   not ours.
4. **`metadata_header`** — required frontmatter fields, validated rather than merely
   present, one violation per file rather than per field. Schemas are per document
   family — `cli/*/install.md`, `cli/*/quick_start.md`, `mcp/*/setup.md`, the key
   documents, and `skills/*/SKILL.md`. A file matching no schema is not checked, so a
   family opts **in** by being named and there is no exemption list to keep in sync.
   On by default, like every other check — see below.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | every enabled check passed |
| `1` | violations found |
| `2` | the check could not run — bad config, empty scope, unreadable file |

`2` is deliberately separate from `1`. A gate that reports success because the checker
broke is worse than no gate, so the hook refuses the push on both.

### Scope

Only tracked markdown, via `git ls-files -z`, minus `scope.exclude_globs`. The ingested
corpus under `docs/landing-zone/` and the `reference.md` files are machine-written and
gitignored by design — not this repo's prose to hold to a house style.

## What is deliberately not here

**"Does this document contradict the code?"** That cannot be settled by reading files; it
needs a command executed per claim. Two things now answer it, and they are not the same
thing:

- **`verify_claims.py`**, in the `verify-docs` skill, executes a *mechanical* verifier per
  claim — a path resolved, a `--help` searched, a version diffed against frontmatter or a
  manifest. No model, so it is cheap and repeatable enough to sit in the push gate, scoped
  to the markdown being pushed. See [`../../verify-docs/scripts/README.md`](../../verify-docs/scripts/README.md).
- **The `verify-docs` skill itself** handles the claims no command settles on its own —
  where the evidence needs reading, or the fix turns on a judgement call. That is minutes
  of work and costs tokens, so it stays on demand; `scripts/verify-docs.sh` at the repo
  root drives it headlessly.

Enabling a `readme_claims` key in `checks.toml` still raises an error rather than silently
doing nothing: claim verification lives in its own script, not in this one.

| | `repo_check.py` | `verify_claims.py` | the `verify-docs` skill |
|---|---|---|---|
| Question | is the prose internally consistent? | is each claim still true? | what should be done about it? |
| Method | reads the files | executes a verifier per claim | reads the evidence |
| Runtime | **~0.065s** over 47 files | ~0.3s scoped, ~18s for all 644 claims | minutes |
| Cost | none | none | tokens |
| Fits | every push | every push, scoped to the change | on demand, or CI |

## Every check ships on

Two rules once shipped disabled, pending a decision the script could not make. Both are
settled:

- **`metadata_header`** is enforced, per document family rather than as one schema for
  all. A file matching no schema is not checked, so families opt **in** by being named and
  there is no exemption list to keep in sync.
- **The `workbench` → `workstation` rule is deleted**, not merely off. In this repo those
  are two different things, not a preferred and a disfavoured spelling: "SDD Workbench" is
  the product name, and `CLAUDE.md` defines the split — *`docs/` is what the workbench
  reads; `workstation/` is what it runs on.* Enforced as written it flagged 54 correct
  uses, and no narrower phrasing was worth keeping.

The `download` → `export` rule ships **on**, carved out: fetching a third-party artefact
over the network genuinely is a download, and the corpus is mostly that.

## The pre-push hook

```bash
cd "$(git rev-parse --show-toplevel)"
ln -sf ../../workstation/agent/skills/review/scripts/pre-push .git/hooks/pre-push
```

A symlink rather than a copy, because `.git/hooks` is not tracked — a copied hook rots
silently and never reaches a fresh clone.

The hook runs two checks in order, and stops at the first refusal:

1. `repo_check.py` over the whole repo, unconditionally. At 0.065s there is nothing to
   optimise around.
2. `verify_claims.py` over **only the markdown in this push**, worked out from the refs
   git feeds the hook on stdin. Scoped that way it is under a second; the whole repo
   would be ~18s, because it executes `--help` for every documented tool. A claim you did
   not touch is a claim you did not break.

Path exemptions come from `.verify-claims-allow` in the repo being pushed, never
from the hook. The hook is shared by every repo that links it, so a glob written
into it would silently exempt paths elsewhere; the hook prints the exemptions in
force before it runs. See
[`../../verify-docs/scripts/README.md`](../../verify-docs/scripts/README.md).

Bypasses, narrowest first:

```bash
SKIP_VERIFY_CLAIMS=1 git push   # skip claim verification, keep repo_check
SKIP_REPO_CHECK=1 git push      # skip both checks in this hook
git push --no-verify            # skip every hook in the repository
```

A tool that is simply absent here reports `UNVERIFIABLE` and does not block. A `REFUTED`
row means the documentation and reality disagree, so prefer fixing it to bypassing it.
