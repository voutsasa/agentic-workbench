# Maintaining confluence-publish

Maintainer-only. The agent does not need this to publish.

### Kept in sync by hand

A skill has to be readable on its own, so several rules are stated here *and* elsewhere. Nothing
checks that the copies agree — when one changes, change all of them. Canonical location first:

| Rule | Canonical | Also stated in |
|---|---|---|
| `index.md` / `README.md` / `<dirname>.md` precedence | `confluence-content/README.md#how-the-documents-must-be-organised` | `SKILL.md`; the tool's `capabilities` output |
| Where the page title comes from | `confluence-content/README.md#where-the-page-title-comes-from` | `SKILL.md`; `confluence-macro-md-examples/README.md` |
| Admonition keyword → macro → panel | [`macro-mapping.md`](macro-mapping.md) | `confluence-macro-md-examples/README.md` (stored names only) — and `make check` prints the macros that directory really emits |
| Delete before republishing | `confluence-content/README.md#republishing-a-page-delete-it-first` | `SKILL.md`; the content repository's `README.md` |
| What the content root is | the tool's `--help` | `SKILL.md`; `../../confluence-export/SKILL.md`; `.env.example` |
| The token is scoped, and the gateway URL | `confluence-content/README.md#the-token-is-a-scoped-token-and-its-prefix-does-not-say-so` | the content repository's `README.md`; `.env.example` |
| The `python -m` fallback for a quarantined exe | the `confluence-sync-md` tool repo's `docs/user_guide.md#windows-a-quarantined-console-script-exe` | `SKILL.md`; `../../confluence-export/SKILL.md` |
