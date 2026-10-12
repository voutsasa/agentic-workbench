---
server: drawio-mcp
package: @drawio/mcp
transport: stdio
version_observed: 1.5.0
verified: 2026-08-05
pinned: false
author: Achilleas Voutsas
version: 0.3.0
---

# drawio-mcp — setup

Official draw.io MCP server (`jgraph/drawio-mcp`). Generates a diagram from XML, CSV, or Mermaid and opens it in the draw.io editor in a browser tab. Package `@drawio/mcp`, binary `drawio-mcp`, stdio transport.

Observed `1.5.0` via `npx -y @drawio/mcp --version` (checked 5 August 2026).

> **Whether this is registered on your machine is machine state, not a fact this file can carry** — see
> [`../../machines/`](../../machines/). Confirm with `claude mcp list` or `copilot mcp list` before
> assuming the tools are live rather than trusting this page.

## Which of the four routes this is

The [docs page](https://www.drawio.com/docs/manual/generate/drawio-mcp-server/) offers four integrations and does not tell you which to pick. This workbench uses the **MCP tool server** — the stdio npm package.

| Route | Why not |
|---|---|
| **MCP tool server** ← *chosen* | Local, no account, works in Claude Code. Diagrams open in a browser tab. |
| MCP app server | Hosted at `mcp.draw.io/mcp`, renders inline via the MCP Apps protocol. Needs a remote endpoint and a client that supports Apps. |
| Skill + CLI | Generates native `.drawio` files and exports PNG/SVG/PDF, but requires draw.io Desktop installed. Revisit if file output is ever needed — this route is the only one that writes files. |
| Embedded URL | Project instructions plus Python, no server. Zero install, but no tools — the model hand-rolls URLs. |

## Register it — run by the user

**Shared, project scope (recommended for this repo):** the catalog at
[`../.mcp.json`](../.mcp.json) already carries the `drawio-mcp` block. Running
`link_config.py --mcp --apply` (see [`../README.md`](../README.md)) writes it into the
repo's tracked `.mcp.json`, which **both** Claude Code (project scope) and Copilot CLI
(workspace scope) read from the same file — nobody has to run either command below
individually.

**Personal, every repo on this machine** — if you'd rather not share it via the repo:

```
claude mcp add -s user drawio-mcp -- npx -y @drawio/mcp
```

```
copilot mcp add drawio-mcp -- npx -y @drawio/mcp
```

Claude's `-s user` and Copilot's (scope-less, always-user) `add` both write to a
per-machine config outside this repo — `~/.claude.json` and
`~/.copilot/mcp-config.json` respectively, neither tracked here. The command itself is
the only record of it — see [`../README.md`](../README.md).

Confirm with `claude mcp list` (should report `drawio-mcp: ✓ Connected`) or
`copilot mcp list`. The tools appear as `open_drawio_xml`, `open_drawio_csv`,
`open_drawio_mermaid`, `search_shapes`, and `list_pages` / `get_page` / `set_page`.

## Tools worth knowing about

Schemas arrive with the tools, so this covers only what they do not say.

- **`search_shapes` is opt-in and usually unnecessary.** It searches ~10,000 library shapes (AWS, Azure, GCP, Cisco, Kubernetes, BPMN, P&ID) and returns style strings to paste into `open_drawio_xml`. Standard flowcharts, UML, ERD, and org charts do not need it — reach for it only when a diagram wants branded or industry-specific icons.
- **`list_pages` / `get_page` / `set_page` work on a local `.drawio` file**, not on the generated URL, and are the way to edit one page of a multi-page file without loading all of it. Paths must end `.drawio` or `.xml`. Compressed pages are handled transparently.
- **`routing: "libavoid"` on `open_drawio_xml`** reroutes connectors around shapes before opening. Worth setting for dense architecture diagrams, where the default routing runs edges through boxes.

## Traps

- **Nothing is written to disk.** The server compresses the diagram, base64-encodes it into a draw.io `#create` URL, and returns the URL. There is no output file unless you use `set_page` against one that already exists. For a committable artefact, render with `d2`, `mmdc`, or `plantuml` instead — see [`cli/README.md`](../../cli/README.md).
- **`npx -y` resolves the latest version on every launch.** Unpinned by design; pin with `@drawio/mcp@1.5.0` in the args if behaviour shifts mid-task.
- **The model may reach for another diagramming route first.** Name the tool explicitly in the prompt when you specifically want draw.io.
- **Do not follow the README's `.claude/settings.json` snippet.** That file has no `mcpServers` key in this Claude Code install; the catalog or the `mcp add` commands above are the working route.
- **`DRAWIO_BASE_URL`** points the server at a self-hosted draw.io instance; it defaults to `https://app.diagrams.net/`, so diagrams leave the machine as URL-encoded content unless it is set.

Docs: [draw.io MCP server](https://www.drawio.com/docs/manual/generate/drawio-mcp-server/) · [tool server README](https://github.com/jgraph/drawio-mcp/blob/main/mcp-tool-server/README.md) · full page ingest: [reference.md](reference.md)
