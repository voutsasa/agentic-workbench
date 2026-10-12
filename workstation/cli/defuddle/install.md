---
tool: defuddle
command: defuddle
product: Defuddle
used_by: fetch-to-markdown
verified: 2026-08-20
author: Achilleas Voutsas
version: 0.3.0
---

# defuddle — install

Binary: `defuddle`. Product: Defuddle. Node tool; brew packages it on macOS, npm is the only route on Windows.

| Platform | Command |
|---|---|
| macOS | `brew install defuddle` |
| Windows | `npm install -g defuddle` |

Verify with `defuddle --version`; it prints a bare `0.x.y` and nothing else.

## Traps

- **No scoop package.** npm is the only Windows route; do not go looking for a bucket.
- **The CLI ships inside the main package.** It is `defuddle`, not a separate `defuddle-cli`.
- **Not the browser extension.** Defuddle is also distributed as an extension; this workbench uses the headless CLI only, driven after Playwright renders a page.

Docs: [README](https://github.com/kepano/defuddle) · full page ingest: [reference.md](reference.md)
