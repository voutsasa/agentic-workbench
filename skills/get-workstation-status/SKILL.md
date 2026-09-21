---
name: get-workstation-status
description: Check whether this machine has the workbench prerequisites and CLI tools, report observed versions, and give recorded corrective actions without installing or authenticating anything. Use independently for workstation readiness or as the pre-step for setup-agents.
---

# Get workstation status

Run the deterministic workstation report. It loads common requirements from
`workstation/dependencies.toml`, applies this machine's
`workstation/machines/<machine>.prerequisites.toml` overrides, probes every dependency, and then
probes every tool whose install route is registered under
[`workstation/cli/`](../../workstation/cli/).

Use the repository `.venv` interpreter when it exists; otherwise use the documented bootstrap
interpreter (`python` on Windows, `python3` on macOS):

```sh
<python> workstation/scripts/status.py
```

Add `--json` when another skill needs to branch on the result. Add `--machine <id>` only when machine
resolution is ambiguous or when checking a profile for a different recorded machine.

The report has three overall states:

| State | Meaning |
|---|---|
| `READY` | Every required prerequisite and optional tool is usable. |
| `READY WITH ACTIONS` | Required prerequisites pass; one or more optional items need attention. |
| `NOT READY` | At least one required prerequisite is absent, blocked, broken, or below its version floor. |

## Boundaries

- Report versions from the probes; enforce only minimums recorded in the machine profile.
- Give corrective actions exactly as reported. Tool installation commands come from the matching
  platform row in each tool's `install.md`.
- Git, Python, Node.js/npm, the package manager, dependency manager, and AI assistants are common
  dependencies with `external` provisioning. Report their presence and versions, but never provide
  or run installation commands for them.
- Never install, upgrade, sign in, or authenticate. Authentication is outside this skill's scope.
- Treat `blocked` and `error` as diagnostic work, not as permission to reinstall.
- Do not edit the generated report into the machine note. Re-run the command when current state matters.
