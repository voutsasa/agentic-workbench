---
role: Open work carried between sessions — committed new work and unproven existing gaps
updated: 2026-10-05
verified: never
author: Achilleas Voutsas
version: 0.1.0
---

# TODO

Work that is known-outstanding rather than merely imagined. The list holds two kinds of item: **new
work** that has been committed to but not yet built, and **existing gaps** — something already written
that no run has proven. Each item says what would close it, so a cold session can act without
reconstructing the reasoning.

**An item earns a place here if it is committed new work or an unproven gap.** An idea nobody has
committed to belongs in a conversation. Delete an item when its evidence exists — a passing command, a
converted file, a pipeline run — and not when it merely feels handled.

## Open

### 50. `session-signature` has not probed a harness other than Claude CLI and Copilot live

Opened 2026-10-06. `--harness <label> --harness-command <cli>` is covered only by a unit test with
the CLI mocked; no non-Claude, non-Copilot assistant (e.g. Kiro) is installed on either machine.
Closed by a run on a machine that has one, quoting the id, e.g.
`python workstation/agent/skills/session-signature/scripts/signature.py --model <id> --harness kiro --harness-command <kiro-cli>`.

### 48. Frontmatter on `AGENTS.md` and `AGENT-INSTRUCTIONS.md` is unverified live

Opened 2026-10-05. Both files gained an `author`/`version` frontmatter block for the first time, so
that every applicable skill, guide, machine note, key document and the harness itself carries the
same metadata. Every other file this applies to has a schema in `checks.toml` and passing tests;
these two have neither, since they are read as live instructions, not documents a schema checks.
Unverified: whether Claude Code's `@AGENTS.md` import and Copilot CLI's direct read of
`AGENT-INSTRUCTIONS.md` (as `copilot-instructions.md`) load the content after a leading `---`
frontmatter block the same as before — plain text is the overwhelmingly likely case, but no fresh
session has confirmed it since the edit landed in the same session that made it.

**Closes when:** a fresh Claude Code session's `/context` shows `AGENTS.md` loaded with its real
content (not truncated or mis-rendered), and a fresh Copilot CLI session shows the same for
`copilot-instructions.md`.

### 46. The bump rule has not been spot-checked against this repo's own cliff.toml

Opened 2026-10-05, with `cliff.toml` and `VERSIONING.md`; narrowed 2026-10-05 once `v0.1.0` shipped.
`CHANGELOG.md` is generated and `v0.1.0` is tagged (annotated) and pushed — `6cc7a39..e6d33e7`,
`[new tag] v0.1.0`. One real bug found and fixed along the way: `git-cliff --bumped-version` errors
with no prior tag (`WARN ... using 0.1.0 as the next version` then `ERROR: Next version (0.1.0) does
not match the tag pattern: v[0-9].*`, since it suggests the bare number but validates it against the
`v`-prefixed pattern) — the first release was tagged directly instead, bypassing `--bumped-version`.
Still unproven: whether `--bumped-version` behaves correctly for the *next* release, where a prior
`v*` tag exists and the bug's precondition no longer holds.

**Closes when:** a throwaway `feat:`/`fix:` commit after `v0.1.0` makes
`uv run git-cliff --bumped-version` suggest the expected `v0.1.1`/`v0.2.0`.

### 45. Eight Fabric-family MCP entries are registered but not ingested

Opened 2026-09-30. `SOURCES.md` → *MCP servers* gained ten entries; the pilot ingested two
(`fabric-iq-mcp`, `powerbi-modeling-mcp`). These eight have no `reference.md`, no `setup.md` and no
row in `workstation/mcp/README.md`: remote `fabric-mcp-overview`, `fabric-ontology-mcp`,
`fabric-warehouse-mcp`, `fabric-data-agent-mcp`, `powerbi-remote-mcp`; local `fabric-onelake-mcp`,
`sql-mcp-server`, `cosmos-db-shell-mcp`. Each local `setup.md` must carry its install route as well as
the Claude and Copilot registration. Held for the user's review of the pilot.

**Closes when:** `repo_check.py --corpus` lists all eight as ingested and each has a `setup.md` and a
README row.

### 44. The fabric-iq-mcp and powerbi-modeling-mcp setups are intended, not observed

Opened 2026-09-30. Both `setup.md` files were written from the ingested docs and the npm registry;
nothing has been installed, registered or run. Unproven: the `X-Variants` header on both CLIs'
`mcp add`; Claude's `--client-id`/`--callback-port` flow against a Power BI Service app registration;
that `npx -y @microsoft/powerbi-modeling-mcp@latest --start --readonly` starts on Windows and blocks
until the EULA is accepted.

**Closes when:** each server answers one read-only tool call from Claude Code and from Copilot CLI,
recorded in the machine note, and each `setup.md` drops its *Intended setup* banner.

### 41. No `/api/2.0/mcp/` Databricks server has connected yet

Opened 2026-09-29. `workstation/scripts/databricks_mcp.py` now prints these servers
(`--genie-space`, `--ai-search`, `--sql`), unit-tested, but no printed command has been run. Two
assumptions are unproven: that these URLs need no `?o=` query string, and that the CLI login's
`all-apis` scope covers `genie` and `ai-search`.

Blocked on 2026-09-29, on the Windows machine: `databricks auth profiles` showed both profiles for
`adb-1279343764318407` as `Valid NO`. `genie list-spaces` and `vector-search-endpoints list-endpoints`
both failed with `Unauthorized network access to workspace: 1279343764318407`. On 2026-09-30, after
re-login, both profiles were `Valid YES` for the same user; `genie list-spaces` returned `{}` and
`vector-search-endpoints list-endpoints` returned `[]`. Nothing to register until a Genie space is
shared with this identity or an AI Search index exists.

**Closes when:** one Genie Agent and one AI Search server each answer a read-only tool call from
Claude Code and from Copilot CLI, and the generator is corrected for whatever that run shows.

### 37. A first push whose tip is already on the default branch verifies nothing

Opened 2026-09-29. The pre-push hook diffs a new branch against the remote default branch, else `main`,
else `master`. When the pushed tip is that branch's tip — `main` to a new, empty remote — the diff is
empty, so `verify_claims.py` never runs. Measured in a throwaway repo pushing to a local bare remote.

**Closes when:** the hook checks the pushed markdown in that case too, with a test in
`workstation/agent/skills/review/tests/test_pre_push.py`.

### 36. The Copilot ruff hook may never run on Windows

Opened 2026-09-29. `workstation/agent/hooks/ruff-on-edit.copilot.json` has only a `bash` command.
If Copilot CLI on Windows runs the `powershell` field, the hook is silently inactive there. Unverified:
no Copilot session has been observed editing a `.py` file on Windows.

**Closes when:** a Windows Copilot CLI edit to a `.py` file shows ruff running, or the registration
gains a `powershell` entry that is observed running.

### 35. The macOS link table is stale

Opened 2026-09-29. `workstation/machines/macos-workstation.md` still shows the 15-row table; `SKILLS`
now has nine skills, and the Windows re-run on 2026-09-29 reported 21 of 21.

**Closes when:** `workstation/scripts/link_config.py --agent claude --agent copilot` is run on the macOS
machine and its output replaces that table.

### 34. The symlinked pre-push hook path is untested

Opened 2026-09-29. The hook now finds `repo_check.py` and `verify_claims.py` beside its own real
location, following symlinks. `test_symlinked_hook_resolves_to_its_real_location` skips on the Windows
machine, which has no symlink privilege; the Windows shim path is tested and was run end to end.

**Closes when:** that test runs unskipped and passes on macOS, and one real `git push` from a repo other
than the workbench runs the linked hook there.

### 33. Claude has not validated the Windows drawio-mcp connection

Opened 2026-09-29. The catalog entry is linked, but Claude's `drawio-mcp` connection timed out after
30 seconds. This is independent of the Azure DevOps MCP OAuth requirement in item 28.

Also 2026-09-29, in a later Windows Claude Code session: `drawio-mcp` connected and its tools were
offered, while `ado-remote-mcp` failed to connect with "Incompatible auth server: does not support
dynamic client registration" — the same failure item 28 already tracks. No Draw.io tool was actually
invoked in that session, so the connection is observed but unproven.

**Closes when:** Claude successfully invokes one Draw.io tool from the Windows setup — a reported
connection alone does not close this.

### 30. The DPACT attended-assistant adoption plan has not been ratified or implemented

Opened 2026-09-29. The DPACT review identifies this workbench as an attended command-line assistant
environment, not an identity platform. Adoption therefore begins with a local governance profile and
evidence model rather than claiming DPACT compliance or adding more prompt rules. The staged plan is:

1. Define the attended-assistant profile: principals, agent identities, task purpose, effect classes,
   approval rules, expiry, retention, and the boundary between repository and production-platform
   controls (1–2 engineer-days).
2. Inventory Claude, Copilot, MCP servers, CLI tools, credential sources, owners, data classes, and
   permitted effects (1–2 engineer-days).
3. Specify and test a minimal task/grant and redacted audit-event schema, without retaining
   chain-of-thought or secrets (2–3 engineer-days).
4. Run an observe-only MCP policy and audit pilot; item 29 supplies the Entra OAuth
   on-behalf-of gateway route for one read-only external call (4–7 engineer-days).
5. Enforce explicit approval and task expiry for write, external-disclosure, configuration, and other
   high-impact effects only after the pilot supplies evidence (5–10 engineer-days).
6. Assess an identity-provider and tool-gateway production architecture for regulated, production, or
   autonomous workloads; this requires IAM, platform, security, and vendor ownership (3–6 weeks,
   excluding approvals).

**Closes when:** the scope and owners are recorded in a versioned architecture decision; stages 1–3
have passing schema and inventory checks; the item 29 pilot produces allow, deny, and audit evidence;
the decision to enforce stage 5 or defer it is recorded with its risk rationale; and production-only
controls are explicitly assigned or excluded.

### 29. A DPACT-compatible Entra OBO policy-gateway proof of concept has not run

Opened 2026-09-29. The DPACT review recommends a repo-local, read-only proof of concept before any
global assistant enforcement: Microsoft Entra ID remains the identity provider; an open-source
gateway evaluates the inbound delegated user token, performs the Entra OAuth on-behalf-of exchange
for one downstream MCP/API, and keeps its confidential-client credential outside the agent runtime.
OPA is the proposed policy decision point and decision-log source. This does not by itself create a
verifiable agent identity or task-scoped authority, so the gateway must also hold and audit a trusted
task, effect, approval, and expiry record rather than trust agent-supplied headers. No component has
been selected, installed, or configured.

**Closes when:** a versioned architecture decision selects the gateway and audit store; a read-only
route accepts a valid Entra token and obtains only its required downstream delegated token; a
resource-, operation-, effect-, and expiry-aware policy allows and denies representative calls; one
correlated audit trace reconstructs the principal, agent, task, policy decision, token exchange, and
outcome; and a security review confirms that neither the agent nor its prompts can access the
gateway's confidential-client credential.

### 28. Claude has not validated ado-remote-mcp from Windows

Opened 2026-09-28. `status.py` reports **READY WITH ACTIONS**: all required prerequisites are present;
the latest observed versions are Claude Code 2.1.284 and GitHub Copilot CLI 1.0.89. The 29 September
`link_config.py --project --agent claude --agent copilot --mcp --apply` report has **24 of 24** links
live and both catalog servers linked in `.mcp.json`. Claude cannot connect to ado-remote-mcp because
its Entra server does not support dynamic client registration;
`workstation/mcp/ado-remote-mcp/setup.md` requires an org-wide Entra app registration and the project's
OAuth client ID.

**Closes when:** the Entra app registration, delegated permissions, and Claude project OAuth client
configuration are in place; and Claude successfully invokes an Azure DevOps MCP tool from the Windows
setup.

### 20. The corpus is not fully ingested on every machine

Opened 2026-09-21 at **0 of 76**, with `docs/landing-zone/` absent. On 2026-09-27
`repo_check.py --corpus` reported 93 of the register's then-94 entries on this machine, after
`ado-remote-mcp` was ingested through the server-rendered route (`div.content`, the page's second
one; markup-noise 0, no relative links). The register has grown since — per-machine and register
counts are not tracked here, because both drift independently and this file is not the ledger for
either. The known-outstanding gap is `confluence-sync-md`, blocked on the Azure DevOps sign-in in
item 28.

**Closes when:** every entry is ingested on each machine — `repo_check.py --corpus` reports N of N.

### 9. The Azure DevOps pipeline has never run

Opened 2026-09-14: the only pipeline was `.github/workflows/verify-docs.yml`, which never runs for this
repo's only remote, `https://euemadev@dev.azure.com/euemadev/EA/_git/agentic-workbench`, an
Azure DevOps repo. The remote's *name* differs per clone — see each machine note. **Written 2026-09-19** as
`azure-pipelines/verify-docs.yml`, applying every counterpart below; checked only locally — the YAML
parses into the ten intended steps, and the pull-request step passes `bash -n`. Its header carries
the three one-time setup steps in ADO, which are the user's. The counterparts were checked against
Microsoft Learn on 2026-09-14; none has run yet:

| GitHub-specific | ADO counterpart, as written |
|---|---|
| `actions/checkout` with `fetch-depth: 0` | `checkout: self` with `fetchDepth: 0` (fetches all history) and `persistCredentials: true`, so the later `git push` authenticates |
| `setup-python` reading `python-version-file: .python-version` | `UsePythonVersion@0` — it has no version-file input and `versionSpec` is required, so a script step must read `.python-version` first |
| `setup-node` | `UseNode@1` with `version: '22'` |
| `secrets.ANTHROPIC_API_KEY` | a secret pipeline variable or variable group — secrets are not decrypted into the environment, so each step must map it under `env:` |
| `gh pr create` with `GITHUB_TOKEN` | `az repos pr create` (the `azure-devops` CLI extension), authenticated by `AZURE_DEVOPS_EXT_PAT: $(System.AccessToken)` |
| workflow `permissions: contents/pull-requests: write` | on the repo, `<project> Build Service (<org>)` needs *Contribute*, *Create branch* and *Contribute to pull requests* — or `Project Collection Build Service (<org>)` if the job authorization scope is collection |

**Closes when:** the user has done the header's setup and `azure-pipelines/verify-docs.yml` has run
once on the ADO project, both reports were produced, and either a pull request was opened or the run logged *No
documentation drift found* — with the run URL recorded here before the item is deleted.

### 12. `review`'s Apply mode approve-each step has not run

Opened 2026-09-18, with `5949ef5`. Narrowed the same day: the review of `workstation/` applied in
`e9b3263` exercised failing-test-first (step 4) — `test_link_config.py` failed with 2 failures and 1
error against the unfixed `link_config.py` before the fix — and recording unfixed findings (step 8),
into this file's item 17 and one closed in `d419f95`. Approve-each (step 2) did not run: the user answered the review's
decisions and then said to go ahead with all of it.

**Closes when:** one review in Apply mode, with the user asking to approve each finding, offers one
choice per finding with its confidence and applies only the approved ones.

### 15. The subagent rule has not steered a session

Opened 2026-09-18, with the rewrite of principle 5 in `workstation/agent/AGENT-INSTRUCTIONS.md` and
the subagent rule in § *Skills and subagents*. **Principle 5's triggers were observed on 2026-09-19**
in a fresh Claude Code session in a scratch repo (`~/tmp/probe-repo`): it fixed a README typo without
asking, and on *add a git pre-commit hook that runs ruff* it stopped, named the hook as a gate needing
design approval, and handed over the `uv` scaffolding commands instead of running them.

Also seen in that session, twice: a bare one-line request was read as pasted text with "no message of
your own" and the agent asked before acting — on a read-only lookup, which meets no trigger. The typo
request between them was acted on. Two samples; not yet a reason to change the instructions.

**Closes when:** a session spawns a subagent under the rule and the parent re-checks its result,
recorded here or in the machine note. The pasted-text reading is dropped after a month of sessions
without it, or becomes an instruction change if it recurs.

### 17. The emphasis in `AGENT-INSTRUCTIONS.md` may be over-applied

Opened 2026-09-18, from the review of `workstation/agent/AGENT-INSTRUCTIONS.md`, as the unapplied
low-confidence finding: the file carries about thirty bold or "never" emphases, which may make
current models apply rules too broadly. That is a judgement, not a measurement.

The rest of that item closed on 2026-09-19: both assistants resolved a `workstation/…` path through
the machine note's `repo:` field from outside this repo, without searching — recorded in
`workstation/machines/macos-workstation.md`.

**Closes when:** a session is observed over-applying a rule because of the emphasis (then trim), or
after a month of sessions without such a case (then drop).
