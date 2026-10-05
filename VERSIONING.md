# Repository versioning: SemVer 2.0.0, Conventional Commits and git-cliff

How this repository versions its releases, and how to adopt the same approach in another
repository. Adapted from `Work/Development/EMA/ea-data-model`'s `docs/repo-versioning-guide.md`,
which was written for exactly that purpose. Two parts:

1. **The standard:** Semantic Versioning 2.0.0 as the versioning policy. What a version number
   promises, what is versioned, and the rules this repository commits to.
2. **The tooling:** Conventional Commits and git-cliff, which apply the policy mechanically — the
   commit history decides the next version and generates the changelog.

This covers the version of the **repository**: workstation scripts, skills, the register schema and
the agent harness, released together. There is nothing else versioned separately here. Four files do
repeat the version number — the Claude Code and Copilot CLI plugin manifests under
`workstation/agent/` — and `workstation/scripts/tests/test_plugin_manifest.py` is their drift test.

# Part 1: the standard

## Why a versioning standard

A version number is a promise to whoever depends on the repository: another engineer cloning it,
an assistant loading its skills, a script calling `workstation/scripts/link_config.py`. Without a
shared rule, "it changed" says nothing about whether that is safe to pick up.
[Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) (SemVer) makes the number itself
say that:

| From → to | Promise to a consumer |
|---|---|
| `0.4.2` → `0.4.3` (PATCH) | a fix only; pick it up without changes on your side |
| `0.4.2` → `0.5.0` (MINOR) | a new capability or a breaking change — see *The 0.x period* below |
| `1.4.2` → `2.0.0` (MAJOR, once past 0.x) | something you may rely on changed or was removed; read the changelog and migrate |

## The SemVer 2.0.0 rules this repository commits to

| SemVer rule | What it says | How this repository applies it |
|---|---|---|
| §1 Public API | software using SemVer must declare a public API | the *public API* table below names every surface a consumer relies on and what breaks each |
| §2 Format | `MAJOR.MINOR.PATCH`, non-negative integers, no leading zeros | `0.1.0`, `0.4.0`; tags add a `v`: `v0.1.0` |
| §3 Immutability | once released, a version's contents must not be modified; changes go in a new version | a release tag is never moved or deleted; a mistake is fixed in the next release |
| §4 Initial development | `0.y.z` is for initial development; the public API may change at any time | this repository starts at `0.1.0`: see *The 0.x period* |
| §5 1.0.0 | `1.0.0` defines the public API; from then on, versions follow how it changes | decided by the repository's owner, not suggested by tooling: see *The road to 1.0.0* |
| §6 PATCH | backward-compatible fixes only | `fix:` commits, and anything neither a feature nor breaking |
| §7 MINOR | new backward-compatible functionality, or a deprecation notice; resets PATCH | `feat:` commits |
| §8 MAJOR | any backward-incompatible change to the public API; resets MINOR and PATCH | commits marked `!` or a `BREAKING CHANGE:` footer |
| §9 Pre-release | a hyphen and identifiers: `0.1.0-rc.1`, lower precedence than `0.1.0` | release candidates: `vX.Y.Z-rc.N` |
| §10 Build metadata | a plus and identifiers; ignored for precedence | not used |
| §11 Precedence | compare MAJOR, MINOR, PATCH numerically, then pre-release | `0.10.0` is later than `0.9.0` |

## What is versioned

**One version for the whole repository.** Workstation scripts, the register schema, repo and global
skills, and the agent harness are released together under one number, `[project] version` in
[`pyproject.toml`](pyproject.toml), and one tag. A skill or a script has no version of its own: it is
"the one in `v0.3.0`." Anyone who needs fixed behaviour pins a tag.

The ingested corpus (`docs/landing-zone/`, `workstation/cli/*/reference.md`,
`workstation/mcp/*/reference.md`) is not versioned by this scheme at all — it is gitignored and
rebuilt on demand from `SOURCES.md`, per [`AGENTS.md` § *The corpus is not in git*](AGENTS.md#the-corpus-is-not-in-git).

## The 0.x period

SemVer §4 makes `0.y.z` a period in which the public API may change at any time. Refined so the
number still carries information, matching `ea-data-model`'s own choice:

- a **breaking change or a new feature** bumps MINOR (`0.1.0` → `0.2.0`);
- **anything else** bumps PATCH (`0.1.0` → `0.1.1`);
- a breaking change is still marked **BREAKING** in the changelog, so readers can tell a break from
  a feature even though both bump MINOR.

## The road to 1.0.0

`1.0.0` is the statement "this public API is stable; from now on, breaking it costs a MAJOR
version." Decided by the repository's owner, not suggested by tooling, when the surfaces in the
public API table have stopped changing shape and something depends on them staying fixed. No date
is set for this yet.

## Who decides a release

| Decision | Made by |
|---|---|
| the kind of each change (`feat`, `fix`, `!`) | the author of the commit |
| the next version number | git-cliff suggests it from the commits; the person cutting the release confirms or overrides it |
| when to release | the repository owner |
| 1.0.0, and every MAJOR after it | the repository owner, explicitly |

# Part 2: the tooling

## The approach in one table

| Element | What this repo does |
|---|---|
| Version scheme | [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html): `MAJOR.MINOR.PATCH` |
| Source of truth | one place: `[project] version` in [`pyproject.toml`](pyproject.toml) |
| Release marker | an **annotated** git tag `vX.Y.Z` on the commit that sets the version |
| Commit messages | [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/): `type(scope)!: summary` |
| Changelog | `CHANGELOG.md`, **generated** by [git-cliff](https://git-cliff.org) from [`cliff.toml`](cliff.toml); never edited by hand |
| Next version | worked out by git-cliff from the commit types since the last tag (`--bumped-version`), then confirmed by a person |
| git-cliff itself | a `dev`-group dependency in `pyproject.toml`, installed by `uv sync` like `pytest`/`ruff`/`pyright` — PyPI ships prebuilt wheels for it, so no separate machine install is needed here |
| What a "breaking change" means | defined per surface in the public API table below |
| Enforcement | none yet. Conventional Commits are followed by convention — reviewers and the assistant check them — not enforced by a hook. Add one later if drift shows up |

The point of the approach: **the commit history is the input.** If every commit says what kind of
change it is, the changelog and the next version number follow from it, and nobody writes or argues
about either by hand.

## Public API table

| Surface | MAJOR (breaking) | MINOR | PATCH |
|---|---|---|---|
| Workstation scripts' CLI (`link_config.py`, `status.py`, `inventory.py`, `repo_check.py`, `verify_claims.py`, `databricks_mcp.py`) | remove/rename a flag or subcommand, change a default, change what a non-zero exit means | add a flag or subcommand | fix behaviour, same interface |
| Register schema (`SOURCES.md`/`SOURCE_CATALOGUE.md` entry format; the `install.md`/`quick_start.md`/`reference.md` and `setup.md`/`reference.md` file contracts) | change the bracket-link convention, rename or remove a required file | add an optional file or section | reword, fix a stale entry |
| Repo and global skills (`skills/*/SKILL.md`, `workstation/agent/skills/*/SKILL.md`) | rename or remove a skill, change its trigger, inputs or outputs | add a skill or a capability | clarify wording, fix a script bug |
| Agent harness (`AGENTS.md`, the `CLAUDE.md`/`copilot-instructions.md` pointer, `workstation/agent/settings.json`, hooks) | remove or invert a rule or gate a session relies on | add a rule, gate or permission | reword without changing behaviour |
| `checks.toml` rule schema (read by `repo_check.py`) | rename or remove a check or a config key | add a check or key | tune a threshold or allowlist |

## Setting it up in another repository

### 1. Install git-cliff

PyPI carries prebuilt wheels for it (`git-cliff` on [pypi.org](https://pypi.org/project/git-cliff/)),
so in a `uv`-managed Python repo it is just another `dev`-group dependency — the route this
repository uses:

```sh
uv add --dev git-cliff
```

`uv sync` then installs it into `.venv` alongside `pytest`/`ruff`/`pyright`; run it with
`uv run git-cliff ...` or the venv's own binary (`.venv\Scripts\git-cliff.exe` on Windows,
`.venv/bin/git-cliff` on macOS).

In a repository with no Python toolchain, it is a standalone binary instead:

| OS | Command |
|---|---|
| macOS | `brew install git-cliff` |
| Windows | `scoop install git-cliff` |

Check: `git-cliff --version` (or `uv run git-cliff --version`).

### 2. Choose the single source of truth

Put the version in one file, and have every other place derive from it or be checked against it.
Here that file is `[project] version` in `pyproject.toml`, set with `uv version X.Y.Z` (also updates
`uv.lock`). No `SKILL.md` repeats it (confirmed by searching for a `version:` field in every one,
unlike `ea-data-model`'s skills), but the Claude Code and Copilot CLI plugin manifests under
`workstation/agent/` do — `workstation/scripts/tests/test_plugin_manifest.py` fails when any of the
four drift from it, the same way `ea-data-model`'s `tests/test_skills.py` does for its skills.

### 3. Add `cliff.toml`

Already in place at the repo root. Its sections, and why:

| Section | Setting | Why |
|---|---|---|
| `[changelog] header` | title and a pointer to this file | written once at the top of `CHANGELOG.md` |
| `[changelog] body` | one `## [x.y.z] - date` section per tag, `## [Unreleased]` for untagged commits, commits grouped by type with scope, a **BREAKING** marker and the short hash | the changelog layout |
| `[git] conventional_commits = true` | parse `type(scope)!: summary` | needed for grouping and bumping |
| `[git] filter_unconventional = false` | keep commits that do not follow the convention | this repository's 201 pre-adoption commits land under *Other* rather than disappearing |
| `[git] commit_parsers` | `feat`→Added, `fix`→Fixed, `perf`→Performance, `refactor`→Changed, `docs`→Documentation, `test`→Tests, `build`/`ci`/`chore`→Maintenance, skip `chore(release)`, rest→Other |
| `[git] tag_pattern = "v[0-9].*"` | which tags are releases | nothing else here uses tags yet |
| `[git] sort_commits = "oldest"` | chronological within a section | |
| `[bump] features_always_bump_minor = true` | a `feat` bumps MINOR even on 0.x | see *Bump rules* |
| `[bump] breaking_always_bump_major = false` | on 0.x a breaking change bumps MINOR, not MAJOR | SemVer §4 |

### 4. Define the public API

Done above. A version number only means something once "breaking" is defined per surface.

### 5. Adopt Conventional Commits

```text
<type>(<scope>)!: <summary>

<body: why, and for a breaking change the migration>

BREAKING CHANGE: <what breaks and how to migrate>     (alternative to the "!")
```

| Part | Values in this repo |
|---|---|
| `type` | `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `build`, `ci`, `chore` |
| `scope` | the area changed: `skills`, `harness`, `register`, `cli`, `mcp`, `scripts`, `machines`, `deps` |
| `!` or `BREAKING CHANGE:` footer | the change breaks a surface in the public API table |

Examples:

- `feat(skills): add the python-quality skill`
- `fix(scripts): read HTML help on Windows instead of opening a browser tab`
- `refactor(register): split MCP servers into Remote and Local`
- `build: adopt SemVer 2.0.0 and a git-cliff changelog`

Nothing enforces the format; reviewers and the assistant follow it. A `commit-msg` hook or a CI
check can enforce it later if needed.

### 6. Document the policy in the README

Done — see `README.md`'s *Versioning* section, which stays short and points here for the full
policy and the release steps below.

### 7. Make the first release

1. Commit the setup with a conventional message: `build: adopt SemVer 2.0.0 and a git-cliff
   changelog`.
2. The first version is `0.1.0` — already set in `pyproject.toml`.
3. Once git-cliff is installed, generate the changelog and tag, as in *Cutting a release* below.

All 201 commits before this one predate the convention and will appear under *Other* in that first
changelog, the same way `ea-data-model`'s own `v0.1.0` shows its pre-adoption history.

## Bump rules

`git-cliff --bumped-version` looks at the commits since the last `v*` tag and suggests the next
version:

| Last tag | Commit since then | Suggested |
|---|---|---|
| v0.1.0 | `fix: …` | v0.1.1 |
| v0.1.0 | `docs: …` (or any other type) | v0.1.1 |
| v0.1.0 | `feat: …` | v0.2.0 |
| v0.1.0 | `feat!: …` (breaking) | v0.2.0 |
| v1.2.0 | `fix: …` | v1.2.1 |
| v1.2.0 | `feat: …` | v1.3.0 |
| v1.2.0 | `feat!: …` or `refactor!: …` (breaking) | v2.0.0 |

In words:

- **While on 0.x,** a feature or a breaking change bumps MINOR, and anything else bumps PATCH. A
  breaking change is still marked **BREAKING** in the changelog, so readers can tell.
- **From 1.0.0,** a breaking change bumps MAJOR, a feature MINOR, and anything else PATCH.
- **1.0.0 is never suggested:** set it by hand when the public API is declared stable.

These rules are `ea-data-model`'s own, carried over with its `cliff.toml`; they have not yet been
re-run against a throwaway repo with *this* repository's `cliff.toml` — that spot-check is `TODO.md`'s
open item for cutting the first release.

The suggestion is only as good as the commit messages. If a change broke a surface in the public API
table but was not committed with `!`, set the version by hand.

## Day to day

```sh
uv run git-cliff --unreleased        # the changelog of what is not yet released
uv run git-cliff --bumped-version    # the version the next release would get
```

Neither writes anything. Run them before a release, or to check that commits are being classified
as intended.

## Cutting a release

From `main`, with a clean working tree and everything to be released merged. This repository has no
`Makefile`; its gate is the same checks the pre-push hook runs — see
[`workstation/agent/skills/review/scripts/repo_check.py`](workstation/agent/skills/review/scripts/repo_check.py)
and [`.pre-push-tests`](.pre-push-tests).

```sh
# the repository's full gate — Windows paths shown; macOS uses .venv/bin/python
.venv\Scripts\python.exe workstation\agent\skills\review\scripts\repo_check.py
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m pyright
# plus every suite named in .pre-push-tests, via
#   .venv\Scripts\python.exe -m unittest discover -s <dir> -t <dir>

NEXT=$(uv run git-cliff --bumped-version)   # e.g. v0.2.0; override by hand if needed
uv version "${NEXT#v}"                      # source of truth, and uv.lock
uv run git-cliff --tag "$NEXT" -o CHANGELOG.md   # regenerates the whole changelog
# Edit the `version` field (an editor task, not a sed one-liner — see VERSIONING.md's own
# pitfalls) to "${NEXT#v}" in all four:
#   workstation/agent/.claude-plugin/plugin.json
#   workstation/agent/.claude-plugin/marketplace.json      (plugins[0].version)
#   workstation/agent/plugin.json
#   workstation/agent/marketplace.json                     (plugins[0].version)
.venv\Scripts\python.exe -m unittest discover -s workstation/scripts/tests -t workstation/scripts/tests
# ^ re-run after the manifest edit: test_plugin_manifest.py now checks the new version
git commit -am "chore(release): $NEXT"
git tag -a "$NEXT" -m "$NEXT"               # annotated, on the release commit
git push --follow-tags origin main
```

| Step | Why |
|---|---|
| `${NEXT#v}` | git tags carry the `v`; `pyproject.toml` does not |
| `--tag "$NEXT"` | git-cliff writes the unreleased commits under the new version, before the tag exists |
| `-o CHANGELOG.md` | regenerates the whole file from history, so a hand edit would be lost: never edit it |
| the four manifest edits | `test_plugin_manifest.py` fails the gate otherwise — these are the files that repeat the version, per *Choose the single source of truth* above |
| `chore(release): …` | the parser skips it, so the release commit does not list itself |
| `git tag -a` | annotated tags carry a tagger and date; `--follow-tags` does not push a lightweight tag |
| `--follow-tags` | pushes the branch and the annotated tags reachable from it in one go |

### Pre-releases

For a release candidate, set the version by hand: `--bumped-version` does not produce one.

```sh
NEXT=v0.2.0-rc.1
uv version 0.2.0-rc.1        # stored in PEP 440 form: 0.2.0rc1
uv run git-cliff --tag "$NEXT" -o CHANGELOG.md
```

The tag keeps the SemVer form (`v0.2.0-rc.1`); Python packaging stores the normalised form
(`0.2.0rc1`) in `pyproject.toml`.

## Checklist for another repository

- [ ] SemVer 2.0.0 adopted in a commit of its own, and the policy written down: scheme, source of
      truth, public API, 0.x rule, 1.0.0 criteria, immutability of releases
- [ ] what is versioned decided: one version for the repository, and any separate tracks
- [ ] git-cliff installed (`git-cliff --version`)
- [ ] one source of truth for the version; a test for every file that repeats it, if any do
- [ ] `cliff.toml` copied; scopes, groups and `tag_pattern` adapted
- [ ] public API table written
- [ ] Conventional Commits adopted (and, optionally, enforced by a hook or CI)
- [ ] a *Versioning* section with the release steps, in the README or a dedicated file
- [ ] first release tagged `v0.1.0` (annotated), `CHANGELOG.md` generated
- [ ] `git-cliff --bumped-version` gives the expected answer after the next `feat` and `fix`

## Pitfalls seen adopting this (from `ea-data-model`'s guide, carried over)

| Pitfall | Avoid it by |
|---|---|
| Expecting a `feat` on 0.x to bump PATCH | it bumps MINOR (`features_always_bump_minor = true`) |
| A breaking change committed without `!` | the suggestion is then too low; set the version by hand and note the break in the next release commit's body |
| Editing `CHANGELOG.md` by hand | the next `git-cliff -o` overwrites it; fix the commit messages' effect in `cliff.toml` instead |
| A commit on the default branch with a wrong message | rewording it would rewrite shared history; add a `commit_preprocessors` entry to `cliff.toml` that matches only that message |
| Forgetting a file that repeats the version | add a test that compares it with the source of truth |
| Assuming the remote is `origin` | this repository's is; use the configured name, or `@{upstream}`, if that ever changes |
