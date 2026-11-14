# Maintaining confluence-export

Maintainer-only. The agent does not need this to export.

### Kept in sync by hand

A skill has to be readable on its own, so some rules are stated here *and* elsewhere, with nothing
checking that the copies agree. When one changes, change all of them:

| Rule | Canonical | Also stated in |
|---|---|---|
| What the content root is | the tool's `--help` | `SKILL.md`; `../../confluence-publish/SKILL.md`; `.env.example` |
| The `python -m` fallback for a quarantined exe | the `confluence-sync-md` tool repo's `docs/user_guide.md#windows-a-quarantined-console-script-exe` | `SKILL.md`; `../../confluence-publish/SKILL.md` |
| `CME_CONFIG_PATH` must be absolute, and set before the first `cme` | `confluence-content/README.md#credentials` | `SKILL.md`; `.env.example` |
| A template change invalidates the lock file | `confluence-content/README.md#changing-a-path-template-invalidates-the-lock-file` | `SKILL.md` |
| Breadcrumb links point outside a subtree export | `confluence-content/README.md#what-an-export-produces` | `SKILL.md` |
