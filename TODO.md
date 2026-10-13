---
role: Open work carried between sessions — committed new work and unproven existing gaps
updated: 2026-10-10
verified: never
author: Achilleas Voutsas
version: 0.3.0
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

### 52. The machine probes do not detect a quarantined venv launcher

Opened 2026-10-10. `workstation/machines/windows-ema-pf5n4xe7.md` § *A new venv's console-script
launchers can be quarantined* records two 46,080-byte uv launchers in another repo's `.venv` that
could not be read or started, found only when a session hit `Failed to spawn … os error 5`. Neither
`inventory.py` nor `status.py` reads `.venv\Scripts\*.exe`, so the next occurrence will also surface
mid-task, and the machine note's account of it is hand-written rather than measured.

**Closes when:** a probe in `workstation/scripts/` reports every `.venv\Scripts\*.exe` of the repo it
checks that cannot be read, with a unit test for the refused case — or the user decides the
hand-written section is enough and deletes this item.

### 51. GitHub Copilot's project-level `.claude/skills/` discovery has never been observed

Opened 2026-10-09, while applying Option B of the skills-location rule in
`workstation/agent/AGENT-INSTRUCTIONS.md` § *Start local, validate, then scale to global* (skills
authored under `<repo>/skills/<name>/SKILL.md`, linked back from `.claude/skills/<name>` for
discovery). That rule asserts Claude Code *and* GitHub Copilot both read
`.claude/skills/<name>/SKILL.md` at the project level — unlike the global case, where
`link_config.py` links Copilot to its own `~/.copilot/skills/`. The project-level claim about
Copilot has not been tested on any machine; it was carried over from the original rule text
without a run to back it.

**Closes when:** a Copilot CLI session, run from inside a repo that has only
`.claude/skills/<name>/SKILL.md` (no `~/.copilot/skills/` entry for it), lists or invokes that
skill — or, if it does not, the rule is corrected to say what Copilot actually needs at project
scope and `link_config.py --project` is adjusted to match.

### 50. `session-signature` has not probed a harness other than Claude CLI and Copilot live

Opened 2026-10-06. `--harness <label> --harness-command <cli>` is covered only by a unit test with
the CLI mocked; no non-Claude, non-Copilot assistant (e.g. Kiro) is installed on either machine.
Closed by a run on a machine that has one, quoting the id, e.g.
`python workstation/agent/skills/session-signature/scripts/signature.py --model <id> --harness kiro --harness-command <kiro-cli>`.

### 45. Eight Fabric-family MCP entries are registered but not ingested

Opened 2026-09-30. `SOURCES.md` → *MCP servers* gained ten entries; the pilot ingested two
(`fabric-iq-mcp`, `powerbi-modeling-mcp`). These eight have no `reference.md`, no `setup.md` and no
row in `workstation/mcp/README.md`: remote `fabric-mcp-overview`, `fabric-ontology-mcp`,
`fabric-warehouse-mcp`, `fabric-data-agent-mcp`, `powerbi-remote-mcp`; local `fabric-onelake-mcp`,
`sql-mcp-server`, `cosmos-db-shell-mcp`. Each local `setup.md` must carry its install route as well as
the Claude and Copilot registration. Held for the user's review of the pilot.

2026-10-06: all eight `reference.md` files ingested on macos-workstation via Microsoft Learn's
`Accept: text/markdown` route (markup-noise 0, no relative links); `repo_check.py --corpus` no longer
lists them. The `setup.md` files and README rows are still missing.

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

The run has to happen on the Windows machine: the Azure workspace is reachable only through the VPN,
which macos-workstation does not use (`workstation/machines/macos-workstation.md` § *Known blockers*).

**Closes when:** one Genie Agent and one AI Search server each answer a read-only tool call from
Claude Code and from Copilot CLI, and the generator is corrected for whatever that run shows.

### 34. The symlinked pre-push hook path is untested

Opened 2026-09-29. The hook now finds `repo_check.py` and `verify_claims.py` beside its own real
location, following symlinks. `test_symlinked_hook_resolves_to_its_real_location` skips on the Windows
machine, which has no symlink privilege; the Windows shim path is tested and was run end to end.

2026-10-10: reconfirmed directly, outside the test suite. Creating
`confluence-sync-md-demo/.claude/skills/confluence-setup` as a symlink (to match its
`confluence-export`/`confluence-publish` siblings, which already are real relative symlinks and are
committed) failed identically via both `PowerShell`'s `New-Item -ItemType SymbolicLink`
(`Administrator privilege required for this operation`) and `cmd.exe`'s `mklink /D`
(`You do not have sufficient privilege to perform this operation`) on `windows-ema-pf5n4xe7` — so this
is not a PowerShell-specific restriction. Worked around there with a directory junction
(`New-Item -ItemType Junction`, no privilege needed) instead, gitignored rather than committed because
a junction's target is an absolute, machine-specific path — committing it would duplicate the skill's
files as a second literal copy rather than travel as a link. That repo's `.gitignore` carries the
`mklink /J` command to recreate it per clone, and a note to replace it with a real symlink once this
item closes.

**Closes when:** that test runs unskipped and passes on macOS, and one real `git push` from a repo other
than the workbench runs the linked hook there.

### 33. Claude has not validated the Windows drawio-mcp connection

Opened 2026-09-29. The catalog entry is linked, but Claude's `drawio-mcp` connection timed out after
30 seconds. This is independent of the Azure DevOps MCP OAuth requirement in item 28.

Also 2026-09-29, in a later Windows Claude Code session: `drawio-mcp` connected and its tools were
offered, while `ado-remote-mcp` failed to connect with "Incompatible auth server: does not support
dynamic client registration" — the same failure item 28 already tracks. No Draw.io tool was actually
invoked in that session, so the connection is observed but unproven.

2026-10-06: back to `CONNECT_TIMEOUT` ("MCP server drawio-mcp connection timed out after 30000ms"),
re-checked twice in one session. Intermittent, not fixed — still no tool ever invoked.

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
either. The known-outstanding gaps are `confluence-sync-md`, blocked on the Azure DevOps sign-in in
item 28 (an unauthenticated `curl` of its README returns `302`), and DPACT on macos-workstation, which
SSRN serves only to a browser — closed by the user saving its PDF to
`docs/landing-zone/DPACT - A Framework for Identity, Accountability, and Task-Scoped Authority in Autonomous AI Agent Systems.pdf`.

**Closes when:** every entry is ingested on each machine — `repo_check.py --corpus` reports N of N.

### 9. The Azure DevOps pipeline has never run, and its model auth needs a design, not a secret

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

2026-10-06: `az pipelines list` and `az pipelines runs list` against `organization=https://dev.azure.com/euemadev project=EA` show one pipeline, `ea-blueprints-web` (id 2010) — unrelated. None of the header's three setup steps has happened yet; this is still at square one on the ADO side. The user chose to create the pipeline through the ADO portal rather than `az pipelines create`.

2026-10-06, narrowed from a mechanical "add a secret" item to a design item: the model-auth question
turned out not to be a one-line swap. `az devops service-endpoint list` for `EA` returns `[]` — no AWS
or Azure OpenAI credential of any kind exists in this ADO project yet, so whichever provider is picked,
the credential plumbing is new, not a reuse.

Three constraints, gathered in order:

1. The workstation's AWS Bedrock mandate (`workstation/machines/windows-ema-pf5n4xe7.md`) **extends to
   this pipeline** — confirmed by the user, reversing an initial "workstation-only" answer. Recorded in
   assistant memory as `bedrock-scope-ci`.
2. The user's actual requirement is broader than Bedrock: **work runs need an Azure OpenAI key; private
   runs need an OpenAI or Anthropic key** — three provider families, not one.
3. Azure AI Foundry (`CLAUDE_CODE_USE_FOUNDRY`, which would have kept this inside the Anthropic family
   on Azure infrastructure) does not offer Anthropic models in the EU, so it cannot substitute for
   Bedrock or for a real OpenAI/Azure OpenAI path.

Checked empirically, not assumed: neither Claude Code CLI nor GitHub Copilot CLI can reach OpenAI or
Azure OpenAI at all — `grep` over both installed binaries (`claude.exe`, `copilot.exe`) finds zero
`OPENAI`/`AZURE_OPENAI` strings in either. Claude Code's only four backends are direct Anthropic API,
AWS Bedrock, Google Vertex AI, and Azure AI Foundry (all four run Anthropic models). The catalogued
`workstation/cli/` toolchain has no OpenAI-capable tool either. So an Azure OpenAI/OpenAI path is not a
config change: `scripts/verify-docs.sh`'s model-driven phase is built entirely on `claude -p`'s own
tool implementations (Read/Glob/Grep/Write/Bash) and its budget/sandbox flags
(`--max-budget-usd`, `--allowedTools`) — none of which exist for a raw OpenAI/Azure OpenAI SDK call.

Supporting the OpenAI family means building a second, parallel driver (e.g.
`scripts/verify-docs-openai.py` on the official `openai` SDK's `AzureOpenAI`/`OpenAI` client), which
would need to: reuse `extract_claims.py`/`verify_claims.py` unchanged (they are model-agnostic); reuse
or share the existing report prompt; implement its own read/grep/write(`$OUT`-only)/bash tool handlers
and request→tool-call→result loop; enforce its own token/cost budget cap (no `--max-budget-usd`
equivalent); and pick `OpenAI` vs `AzureOpenAI` by which secret is populated, mirroring how
`CLAUDE_CODE_USE_BEDROCK` presence already selects Bedrock over direct Anthropic. The hand-rolled Bash
tool is the real risk, not just the effort: a model-controlled shell-exec path implemented by us is a
materially larger attack surface than delegating to Claude Code's own hardened tool sandbox, and needs
its own scoping (allowlist, timeout, no writes outside `$OUT`) before it exists at all.

This is now two separable pieces of work, not one:

**Closes when**, for the ADO run (unblocks today, no new engineering):
the user has done the header's setup with AWS Bedrock credentials (Option A — a scoped IAM user's
`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` as ADO secret variables, `CLAUDE_CODE_USE_BEDROCK=1`,
`AWS_REGION=eu-central-1`, `ANTHROPIC_MODEL=eu.anthropic.claude-sonnet-5`), and
`azure-pipelines/verify-docs.yml` has run once on the ADO project, both reports were produced, and
either a pull request was opened or the run logged *No documentation drift found* — with the run URL
recorded here.

**Closes when**, for the Azure OpenAI/OpenAI driver (separate, needs its own design pass before any
code): a versioned design decides the tool allowlist and sandboxing for the hand-rolled Bash tool, the
budget-accounting approach, and the provider-selection convention across both `verify-docs.sh` and the
new script; the new driver passes its own test suite mirroring `review`'s `test_pre_push.py` style
(model call stubbed out, no real spend in tests); and one real run against each of an `OPENAI_API_KEY`
and an Azure OpenAI credential produces the same two reports the Anthropic path does. Until that design
exists, do not start writing the driver.

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
