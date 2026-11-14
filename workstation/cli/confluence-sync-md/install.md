---
tool: confluence-sync-md
command: confluence-sync-md, md2conf
product: confluence-sync-md
used_by: confluence-publish, confluence-export
verified: 2026-09-27
author: Achilleas Voutsas
version: 0.4.1
---

# confluence-sync-md — install

Binaries: `confluence-sync-md`, plus `md2conf` (publish) and `cme` (export), which it drives. The
product is `confluence-sync-md`, a Python tool from this organisation's Azure DevOps repository. It
isn't packaged for brew, scoop or PyPI.

| Platform | Command |
|---|---|
| macOS | `uv tool install --python 3.14 --with-executables-from markdown-to-confluence,confluence-markdown-exporter "git+https://dev.azure.com/euemadev/EA/_git/confluence-sync-md"` |
| Windows | `uv tool install --python 3.14 --with-executables-from markdown-to-confluence,confluence-markdown-exporter "git+https://dev.azure.com/euemadev/EA/_git/confluence-sync-md"` |

**`uv tool`, Python 3.14, from `main`, and the user runs it.** This follows the workbench order for
global Python CLIs (Homebrew or Scoop, then `uv tool`, then pipx; see
[`AGENT-INSTRUCTIONS.md`](../../agent/AGENT-INSTRUCTIONS.md)). The source is the repository's `main`
branch, a deliberate choice: an upgrade (`uv tool upgrade confluence-sync-md`) takes whatever `main`
holds. A consuming repository that needs a fixed version pins a tag itself
(`uv add … --tag v0.6.0`). There is no GitHub copy. Cloning needs Azure DevOps credentials; git's
credential helper supplies them.

**`--with-executables-from` is not optional.** Without it, `uv tool` puts only `confluence-sync-md` on
`PATH`, and `md2conf` and `cme` stay inside the tool's venv. `confluence-sync-md` itself still finds
them, because it looks beside its own interpreter first. But the `confluence-export` skill hands you
a `cme` command to run, and the credential setup below runs `cme` directly.

Verify:

```sh
confluence-sync-md --version        # confluence-sync-md 0.6.0
confluence-sync-md capabilities     # first line: confluence-sync-md 0.6.0   (md2conf 0.6.4, cme installed)
command -v md2conf cme              # both under ~/.local/bin
```

`cme` has no `--version` flag, so the inventory probes only `confluence-sync-md` and `md2conf`.
`capabilities` reports whether `cme` is installed.

**Diagram renderers are separate.** `capabilities` ends with `renderers on this machine — mermaid: …,
plantuml: …`. Both come from this workbench's toolchain:
[`../mermaid-cli/install.md`](../mermaid-cli/install.md) and
[`../plantuml-cli/install.md`](../plantuml-cli/install.md).

## Python 3.14 is a real floor, not just a declared one

Tested on 2026-09-27 against `main` (`3b0e3f9`):

| Python | Result |
|---|---|
| 3.14.6 | Installs; its own suite passes, `337 passed` |
| 3.12.14, as published | **Install refused**: `the current Python version (3.12.14) does not satisfy Python>=3.14` |
| 3.12.14, floor lowered in a scratch copy | Every dependency resolves, but the code fails to import. `documents.py:36` refers to its own class in an annotation, which needs 3.14's deferred annotations (PEP 649), and `cli/spaces.py:54` uses `except SpaceError, ConfigError:` without parentheses (PEP 758, a `SyntaxError` before 3.14) |
| 3.12.14, scratch copy ported | With `from __future__ import annotations` in each module and that one `except` parenthesised, `337 passed`, including the 11 `slow` tests that drive the real md2conf binary. `capabilities` also ran |

So run it on 3.14. Supporting 3.12 would be a change to the confluence-sync-md repository itself:
lower `requires-python` and make those two edits. It isn't something to force from this side.

## Configure

The install is global, but configuration belongs to **each repository that holds Confluence
content**. There are three pieces, all in that repository's root and all gitignored: `.env`,
`cme`'s credential store, and one `space_key.json` per space.

### 1. `.env`

**Neither md2conf nor cme reads `.env`.** Source it into the shell, in the same call as the
command: `source .env && confluence-sync-md …`. So every line needs `export`; without it the
variable is never passed to the tools.

| Variable | Required | Value | Read by |
|---|---|---|---|
| `CONFLUENCE_API_KEY` | **yes** | A **scoped** Atlassian API token (see *2. The token*) | md2conf; copied into cme's store |
| `CONFLUENCE_API_URL` | **yes** | `https://api.atlassian.com/ex/confluence/<cloud-id>/`, the API gateway, because a scoped token authenticates nowhere else. `confluence-sync-md` refuses to publish without it | md2conf, confluence-sync-md |
| `CONFLUENCE_USER_NAME` | **yes** | Your Atlassian account email. It puts md2conf on HTTP Basic (email + token); without it md2conf sends Bearer, which API tokens don't support, and `confluence-sync-md` refuses to run | md2conf, confluence-sync-md |
| `CONFLUENCE_DOMAIN` | **yes** | The bare host, e.g. `euema.atlassian.net`: no `https://`, no trailing slash. The only variable `publish check --local` needs | md2conf, confluence-sync-md |
| `CONFLUENCE_PATH` | recommended | `/wiki/` for Confluence Cloud (`/` for Server / Data Center), as the demo template sets it | md2conf |
| `CME_CONFIG_PATH` | **yes, for export** | The **absolute** path of cme's credential store, e.g. `<repo>/.cme_config.json`. Exports run from inside `export/`, so a relative path points at the wrong place | cme, confluence-sync-md |
| `CONFLUENCE_CONTENT_ROOT` | no | A content root other than the nearest `confluence-content/` | confluence-sync-md |
| `CONFLUENCE_CLOUD_ID` | no | The cloud ID on its own. No tool reads it; it's handy for `curl` and for cme's `cloud_id` | — |
| `CONFLUENCE_SPACE_KEY` | **leave unset** | The space is declared per directory in `space_key.json` and passed on every publish | — |

The cloud ID is the `cloudId` field of `https://<your-site>.atlassian.net/_edge/tenant_info`. It
isn't a secret.

A template to copy, with placeholders in angle brackets:

```sh
# .env: gitignored. Use: source .env && confluence-sync-md …
export CONFLUENCE_API_KEY='<scoped-api-token>'
export CONFLUENCE_API_URL='https://api.atlassian.com/ex/confluence/<cloud-id>/'
export CONFLUENCE_USER_NAME='<you>@<organisation>'
export CONFLUENCE_DOMAIN='<site>.atlassian.net'
export CONFLUENCE_PATH='/wiki/'
export CME_CONFIG_PATH='<absolute-path-to-this-repo>/.cme_config.json'
# export CONFLUENCE_CONTENT_ROOT='<absolute-path-to-another-content-tree>'
```

Add `.env` and `.cme_config.json` to the repository's `.gitignore` before creating either.

### 2. The token

Create it at <https://id.atlassian.com/manage-profile/security/api-tokens> as a token **with
scopes**. Its `ATATT…` prefix doesn't tell you which kind you have. Grant **read and write only,
never delete**: the tool is built so that deleting in Confluence stays a human action.

| Direction | Scopes |
|---|---|
| read | `read:space:confluence`, `read:page:confluence`, `read:content:confluence`, `read:content-details:confluence`, `read:attachment:confluence`, `read:label:confluence`, `read:comment:confluence` |
| write | `write:page:confluence`, `write:content:confluence`, `write:attachment:confluence`, `write:label:confluence` |

cme needs only the read half. Check `read:space:confluence` first, because md2conf's first call
fails without it while cme keeps working:

```sh
source .env && curl -s -o /dev/null -w '%{http_code}\n' -u "$CONFLUENCE_USER_NAME:$CONFLUENCE_API_KEY" \
  "${CONFLUENCE_API_URL}api/v2/spaces?limit=1"      # 200 is good; 401 means read:space:confluence is missing
```

### 3. cme's credential store (export only)

cme keeps its own store and never reads `.env`. It holds three fields under the **site** URL
(`https://<site>.atlassian.net`): `username` (= `CONFLUENCE_USER_NAME`), `api_token`
(= `CONFLUENCE_API_KEY`) and `cloud_id` (the path segment of `CONFLUENCE_API_URL`). Source `.env`
**before the first `cme` command**; otherwise the store is created in the default location, outside
the repository:

```sh
source .env
cme config path                    # must print $CME_CONFIG_PATH
cme config edit auth.confluence    # interactive; leave pat and session_cookies empty
chmod 600 "$CME_CONFIG_PATH"
```

To set it without prompts, and without putting the token on a command line, use the tool's own
interpreter:

```sh
source .env && "$(uv tool dir)/confluence-sync-md/bin/python" - <<'PY'
import os, re
from confluence_markdown_exporter.utils.app_data_store import set_setting_with_keys
site = "https://" + os.environ["CONFLUENCE_DOMAIN"]
cloud_id = re.search(r"/ex/confluence/([^/]+)/?", os.environ["CONFLUENCE_API_URL"]).group(1)
for field, value in [("username", os.environ["CONFLUENCE_USER_NAME"]),
                     ("api_token", os.environ["CONFLUENCE_API_KEY"]),
                     ("cloud_id", cloud_id)]:
    set_setting_with_keys(["auth", "confluence", site, field], value)
PY
```

**Never check it with `cme config list`**, which prints `api_token` in plaintext. Read it back
this way instead, which prints only the token's length:

```sh
source .env && "$(uv tool dir)/confluence-sync-md/bin/python" -c "
import os
from confluence_markdown_exporter.utils.app_data_store import get_settings
a = get_settings().auth.confluence['https://' + os.environ['CONFLUENCE_DOMAIN']]
print('username:', a.username.get_secret_value())
print('token   : set (%d chars)' % len(a.api_token.get_secret_value()))
print('cloud_id:', a.cloud_id)"
```

Both snippets were run against a scratch `CME_CONFIG_PATH` with dummy values on 2026-09-27.
Rotating the token means updating `.env` and this store.

### 4. `space_key.json`, one per space

Don't write it by hand. `source .env && confluence-sync-md space declare <target-page-url>` creates
the space directory and its `space_key.json` from the page URL, asking before it creates a content
tree, and never overwrites an existing one.

### Check the configuration

```sh
source .env && confluence-sync-md capabilities --json            # "content_root" is the tree it resolved
source .env && confluence-sync-md publish check --offline <source>   # all four publish variables, no API calls
source .env && confluence-sync-md publish check --local <source>     # conversion only: needs just CONFLUENCE_DOMAIN, no token
```

A missing or malformed variable shows as `FAIL  environment configured`, with the reason on the
next line, and the check exits 1. `--offline` makes no API calls: with all four variables set to
dummy values it exits 0 (tested 2026-09-27), so it validates the configuration's shape without
checking the token itself. The `curl` in *2. The token* checks the token.

## Traps

- **Don't pass a Python older than 3.14** to make it match the other tools' 3.12. See above.
- **A repository can pin its own copy.** `confluence-sync-md-demo` pins `v0.6.0` in its
  `pyproject.toml`. The skills run `uv run --no-sync -- confluence-sync-md`, which uses that pinned copy
  where one exists and this global install everywhere else.
- **A `.env` line without `export` is silently ignored** by md2conf and cme: the shell sets the
  variable but doesn't pass it on.

Docs: [confluence-sync-md](https://dev.azure.com/euemadev/EA/_git/confluence-sync-md) · full page
ingest: [reference.md](reference.md)
