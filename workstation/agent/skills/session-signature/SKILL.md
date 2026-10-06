---
name: session-signature
description: Generate a session signature id — workstation, username, AI assistant harness version (Claude CLI, GitHub Copilot, Kiro or any other), agentic-workbench version, model ID and UTC timestamp — or, when asked for the extended signature, the full JSON. Use when asked to sign, stamp or attribute an output with who and what produced it.
author: Achilleas Voutsas
version: 0.1.0
---

# Session signature

## Which form

| The user asks for | Run with | Show |
|---|---|---|
| a **signature** | no extra flag | the id line only |
| an **extended signature** | `--extended` | the full JSON |

Show the output verbatim. On exit 1, report its stderr line — never hand-assemble a signature.

## Arguments

Every attribute except the model and harness is probed by the script. Supply:

- `--model` — the exact model ID your system prompt gives for this session, not a configured
  default; `env.ANTHROPIC_MODEL` can name a different model than the one actually running.
- `--harness` — a label for the AI assistant you are running in: lowercase letters, digits, `.` and
  `-`, no `_`. Two labels are known and probed automatically: `claude-cli` (the default, probes
  `claude --version`) and `github-copilot` (probes `copilot --version`). Any other assistant — e.g.
  `kiro` — also needs one of:
  - `--harness-command <cli>` — the CLI whose `--version` prints its version;
  - `--harness-version <x.y.z>` — the version, used as-is, when there is no CLI to probe.

The script is stdlib-only and lives in this skill's own `scripts/` folder, so run it with `python` on
Windows and `python3` on macOS — no project venv needed:

```sh
python <this-skill-dir>/scripts/signature.py --model <exact-model-id>
python <this-skill-dir>/scripts/signature.py --model <exact-model-id> --extended
python <this-skill-dir>/scripts/signature.py --model <exact-model-id> --harness github-copilot
python <this-skill-dir>/scripts/signature.py --model <exact-model-id> --harness kiro --harness-command kiro-cli
```

## Id sequence

The id joins these attributes with `_`, in this order — the script's `ID_FIELDS` tuple, which a unit
test holds to this list:

| # | Attribute | Example |
|---|---|---|
| 1 | `workstation` | `EMA-PF5N4XE7` |
| 2 | `username` | `voutsas` |
| 3 | `harness` | `claude-cli-2.1.291`, `github-copilot-1.0.89`, `kiro-0.5.0` |
| 4 | `agent` | `agentic-workbench-0.1.0` — `version` in the plugin's `.claude-plugin/plugin.json`, three levels above the script |
| 5 | `model` | `eu.anthropic.claude-opus-5-5` |
| 6 | `timestamp` | `20261006T100816Z` — UTC, `YYYYMMDDTHHMMSSZ` |
