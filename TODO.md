---
role: Open work carried between sessions — committed new work and unproven existing gaps
updated: 2026-09-29
verified: never
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

### 33. Claude has not validated the Windows drawio-mcp connection

Opened 2026-09-29. The catalog entry is linked, but Claude's `drawio-mcp` connection timed out after
30 seconds. This is independent of the Azure DevOps MCP OAuth requirement in item 28.

**Closes when:** Claude reports `drawio-mcp` connected and successfully invokes one Draw.io tool from
the Windows setup.

### 31. The documentation claim extractor binds local-script flags to `python`

Opened 2026-09-29. A Databricks MCP setup check found that a command such as
`python workstation/scripts/databricks_mcp.py --profile ...` produces the claim "`python` supports
`--profile`". The generator's own help proves the flag, but the wrongly bound claim remains
unverifiable and obscures the actual documentation result. The 29 September full offline sweep also
refuted five Unity Gateway claims because the extractor bound flags to an incomplete command:
`ug mcp-proxy --host`, `--profile`, and `--url`;
`ug mcp --names`; and `ug configure --agents`.

**Closes when:** the extractor binds flags after an interpreter invocation to the repository-local
script and to the complete subcommand invocation; regression fixtures cover `databricks_mcp.py` and
the Unity Gateway forms above; and the manifest contains no false `python supports …` or
`ug supports …` flag claims.

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

### 25. The README *Install* steps have not run on Windows

Opened 2026-09-22. `README.md` § *Install* gained `uv sync`, the pre-push gate and `status.py` as steps
1–3; on macOS they ran end to end on a fresh clone (`uv sync` installed `pytest` and `ruff`, `status.py`
reported `READY`). The Windows pre-push step is now validated in item 24's recorded evidence, but no
evidence yet establishes that `uv sync` and `status.py` ran in a fresh Windows clone.

**Closes when:** on `ema-pf5n4xe7`, a fresh clone runs `uv sync`, then
`python workstation\scripts\status.py` exits 0 with a Requirement cell reading `workstation tool for
fetch-to-markdown, pdf-deliverable` on the Pandoc row — recorded in the machine note.

### 20. The corpus on this machine is 93 of 94 entries

Opened 2026-09-21 at **0 of 76**, with `docs/landing-zone/` absent. On 2026-09-27
`repo_check.py --corpus` reports **93 of 94**, after `ado-remote-mcp` was ingested through the
server-rendered route (`div.content`, the page's second one; markup-noise 0, no relative links). The
one missing entry is `confluence-sync-md`, blocked on the Azure DevOps sign-in in item 28.

**Closes when:** `repo_check.py --corpus` reports 94 of 94.

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
