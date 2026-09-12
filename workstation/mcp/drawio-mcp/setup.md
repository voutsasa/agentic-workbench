---
server: drawio-mcp
package: @drawio/mcp
transport: stdio
version_observed: 1.5.0
verified: 2026-08-05
registered: false
pinned: false
---

# drawio-mcp — setup

Official draw.io MCP server (`jgraph/drawio-mcp`). Generates a diagram from XML, CSV, or Mermaid and opens it in the draw.io editor in a browser tab. Package `@drawio/mcp`, binary `drawio-mcp`, stdio transport.

Observed `1.5.0` via `npx -y @drawio/mcp --version` (checked 5 August 2026).

> **Not yet registered.** The package was verified directly, but the `claude mcp add` below has not been run — registration is the user's step. Until they run it and `claude mcp list` confirms, treat the tools as unavailable.

## Which of the four routes this is

The [docs page](https://www.drawio.com/docs/manual/generate/drawio-mcp-server/) offers four integrations and does not tell you which to pick. This workbench uses the **MCP tool server** — the stdio npm package.

| Route | Why not |
|---|---|
| **MCP tool server** ← *chosen* | Local, no account, works in Claude Code. Diagrams open in a browser tab. |
| MCP app server | Hosted at `mcp.draw.io/mcp`, renders inline via the MCP Apps protocol. Needs a remote endpoint and a client that supports Apps. |
| Skill + CLI | Generates native `.drawio` files and exports PNG/SVG/PDF, but requires draw.io Desktop installed. Revisit if file output is ever needed — this route is the only one that writes files. |
| Embedded URL | Project instructions plus Python, no server. Zero install, but no tools — the model hand-rolls URLs. |

## Register it — run by the user

```
claude mcp add -s user drawio-mcp -- npx -y @drawio/mcp
```

`-s user` makes it available in every project on this machine, matching how the register describes workstation tooling. Use `-s project` instead to write a tracked `.mcp.json` scoped to one repo.

Confirm with `claude mcp list` — it should report `drawio-mcp: ✓ Connected`. The tools appear as `open_drawio_xml`, `open_drawio_csv`, `open_drawio_mermaid`, `search_shapes`, and `list_pages` / `get_page` / `set_page`.

**User scope writes to `~/.claude.json`, which is not tracked in this repo.** The command above is the only record of it — see [`../README.md`](../README.md).

## Tools worth knowing about

Schemas arrive with the tools, so this covers only what they do not say.

- **`search_shapes` is opt-in and usually unnecessary.** It searches ~10,000 library shapes (AWS, Azure, GCP, Cisco, Kubernetes, BPMN, P&ID) and returns style strings to paste into `open_drawio_xml`. Standard flowcharts, UML, ERD, and org charts do not need it — reach for it only when a diagram wants branded or industry-specific icons.
- **`list_pages` / `get_page` / `set_page` work on a local `.drawio` file**, not on the generated URL, and are the way to edit one page of a multi-page file without loading all of it. Paths must end `.drawio` or `.xml`. Compressed pages are handled transparently.
- **`routing: "libavoid"` on `open_drawio_xml`** reroutes connectors around shapes before opening. Worth setting for dense architecture diagrams, where the default routing runs edges through boxes.

## Traps

- **Nothing is written to disk.** The server compresses the diagram, base64-encodes it into a draw.io `#create` URL, and returns the URL. There is no output file unless you use `set_page` against one that already exists. For a committable artefact, render with `d2`, `mmdc`, or `plantuml` instead — see [`cli/README.md`](../../cli/README.md).
- **`npx -y` resolves the latest version on every launch.** Unpinned by design; pin with `@drawio/mcp@1.5.0` in the args if behaviour shifts mid-task.
- **The model may reach for another diagramming route first.** Name the tool explicitly in the prompt when you specifically want draw.io.
- **Do not follow the README's `.claude/settings.json` snippet.** That file has no `mcpServers` key in this Claude Code install; the `claude mcp add` command above is the working route.
- **`DRAWIO_BASE_URL`** points the server at a self-hosted draw.io instance; it defaults to `https://app.diagrams.net/`, so diagrams leave the machine as URL-encoded content unless it is set.

Docs: [draw.io MCP server](https://www.drawio.com/docs/manual/generate/drawio-mcp-server/) · [tool server README](https://github.com/jgraph/drawio-mcp/blob/main/mcp-tool-server/README.md) · full page ingest: [reference.md](reference.md)
