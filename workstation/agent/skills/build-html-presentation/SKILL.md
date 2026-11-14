---
name: build-html-presentation
description: Create or update a Reveal.js HTML presentation stored in the repository under docs/html-presentations/, with Reveal.js kept locally beside the decks so they run offline. Checks the stored Reveal.js against the latest release, scaffolds a named deck, writes its slides from the user's brief, and render-checks every slide. Use when asked to build, create, make, update or check an HTML presentation, slide deck or Reveal.js deck. Not for PowerPoint or PDF decks.
author: Achilleas Voutsas
version: 0.4.2
---

# Build an HTML presentation

Decks live at `docs/html-presentations/<name>/` (`index.html` + `theme.css`) in the current repo.
They load Reveal.js from `docs/html-presentations/vendor/reveal.js/<version>/`, never from a CDN, so
a deck opens offline and only changes Reveal.js version when someone decides it should.

Every deterministic step is `scripts/reveal.py`, run from the repo root with `python3` (macOS) or
`python` (Windows). It is stdlib-only and needs no venv. Below, `<skill>` is this skill's folder.

## 1. Check the state

```sh
python3 <skill>/scripts/reveal.py status
```

It prints JSON: `folder_exists`, `stored_versions`, `latest_version` (null when npm is unreachable),
`update_available`, and `presentations` (each with the Reveal.js version it loads).

## 2. Reveal.js version: report, then ask

- **Nothing stored:** say so and ask to fetch `latest_version`. Without it no deck can be created.
- **`update_available`:** report the stored and latest versions and ask whether to fetch the newer
  one. A major version (5 → 6) can change behaviour. If yes, run `fetch <latest>`; then, per deck the
  user names, `use <name> <latest>`, and re-run the check in step 6 on each.
- **`latest_version` null:** say the check could not reach npm and continue with what is stored.

Never fetch or switch versions without the user's yes: a stored release is a dependency change.

```sh
python3 <skill>/scripts/reveal.py fetch <version>
python3 <skill>/scripts/reveal.py use <name> <version>
```

## 3. Choose the presentation

**`presentations` is empty** (whether or not the folder exists): ask for a unique name —
lowercase letters, digits and single hyphens, e.g. `q3-review` — and tell the user what you need
to write the deck:

| Provide | Why |
|---|---|
| Title | The title slide and browser tab |
| Audience | What they know already sets the depth |
| Outcome | What they should know, decide or do afterwards |
| Key messages or sections | The skeleton of the deck |
| Source material — files, links, notes | Facts come from these, not invention |
| Length — minutes or slide count | How much fits |
| Needs — code, diagrams, speaker notes, language | Which slide types to use |

**Presentations exist:** list them and ask which to build, or whether to start a new one. **Skip
the table above** — the user already knows how decks here work; for a new deck ask only for its
name and brief.

Create a new deck (this also creates `docs/html-presentations/` when it is missing):

```sh
python3 <skill>/scripts/reveal.py new <name> --title "<Title>"
```

It refuses a name that exists or is malformed; ask again rather than inventing one.

## 4. Build the slides

Write or update `docs/html-presentations/<name>/index.html` from the brief and its sources. The
template's comment block and `theme.css` classes are the conventions:

- one `<section>` per slide; a `<section>` of `<section>`s for a vertical stack (↓);
- at most five bullets per slide; three or more comparable items as a table;
- speaker notes in `<aside class="notes">`;
- divider slides: `class="divider"` with `data-background-gradient`;
- code: static highlights only, e.g. `data-line-numbers="2,4"`;
- text sizes come from `theme.css` — body text is 26px; change sizes there, not per slide.

Every claim on a slide must trace to the user's sources. Where they are silent, say so rather than
filling the gap.

## 5. Show it

```sh
open docs/html-presentations/<name>/index.html      # macOS
start docs\html-presentations\<name>\index.html     # Windows
```

Keys: `Esc` overview, `S` speaker notes, `F` fullscreen, `Alt`+click zoom.

## 6. Check every slide

```sh
"$(uv tool dir)/playwright/bin/python" <skill>/scripts/render_check.py docs/html-presentations/<name>/index.html
```

`Scripts\python.exe` replaces `bin/python` on Windows. It renders each slide with all fragments
shown and reports `overflow-bottom`, `overflow-right`, `stacked-code` and console errors (exit 1).
Fix what it reports and run it once more. Exit 2 means Playwright is not installed: say so, and
hand the user the route in `workstation/cli/playwright/install.md` of the agentic-workbench, rather
than skipping the check silently.

## 7. Publish — only when asked

```sh
python3 <skill>/scripts/reveal.py build-artifact <name> <out-dir>
```

Writes `<out-dir>/<name>.html` (no document skeleton, local `reveal.css`, scripts from cdnjs) plus
`reveal.css` and `theme.css` to publish beside it.
