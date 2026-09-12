---
tool: mermaid-cli
command: mmdc
product: Mermaid CLI
verified: 2026-08-20
---

# mermaid-cli — install

Binary: `mmdc` — **not `mermaid-cli`**. Product: Mermaid CLI.

| Platform | Command |
|---|---|
| macOS | `brew install mermaid-cli` |
| Windows | `npm install -g @mermaid-js/mermaid-cli` |

Verify with `mmdc --version`; it prints a bare `11.x.y`.

## macOS: the Homebrew build ships no browser

`mmdc` rasterises through a headless Chromium driven by Puppeteer. **The Homebrew formula does not provide one** — its own test asserts that a bare `mmdc` fails with `Could not find chrome-headless-shell`. The npm package does provide one, which is why the two routes behave differently on a fresh machine.

Do not download a second Chromium. Point Puppeteer at the one Playwright already manages:

```sh
# ~/.zshenv
export PUPPETEER_EXECUTABLE_PATH="$(ls -d "$HOME"/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/*.app/Contents/MacOS/* 2>/dev/null | sort -V | tail -1)"
```

Resolved dynamically so it survives Playwright upgrades (`chromium-1228` → `1229`); `sort -V` is required or `chromium-999` sorts above `chromium-1228`. Costs ~8 ms per shell. Puppeteer tolerates a Chromium a version or two off its pin — verified rendering at 149.0.7827.55 against an expected 150.0.7871.24. If a future skew breaks it, `npx puppeteer browsers install chrome-headless-shell` fetches the exact build.

`~/.zshenv`, not `~/.zshrc`: zsh reads `.zshrc` only for interactive shells, so scripts, make, cron and CI would not see the variable.

## Traps

- **The command does not match the package.** Installing `mermaid-cli` gives you `mmdc`.
- **Never install through both brew and npm.** Both link `mmdc` into `/opt/homebrew/bin`; the last writer wins and `mmdc --version` then reports a version you did not install. Seen in practice: npm 11.4.2 shadowing brew 11.16.0 for months. Check with `ls -l "$(which mmdc)"`.
- **Removing the npm copy takes its browser with it.** The brew copy left behind has none, so Mermaid rendering breaks until `PUPPETEER_EXECUTABLE_PATH` is set. A stale `~/.cache/puppeteer` from an old npm install does not help — the version pin will not match.
- **PyPI `mermaid-cli` is not this tool.** It is `seigok/mermaid-cli-python`, an unrelated third-party wrapper. Mermaid CLI is a Node package with no Python channel.
- **No scoop package.** npm is the Windows route; note the scope, `@mermaid-js/mermaid-cli`.

Docs: [README](https://github.com/mermaid-js/mermaid-cli) · full page ingest: [reference.md](reference.md)
