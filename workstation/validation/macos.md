# Validating a macOS workstation

Five sections, in order. Each says what to run and what it should print. Record the results in this
machine's file under [`../machines/`](../machines/README.md), not here.

`$R` below is the clone, the `repo:` field of `~/.agentic-workbench/machine.md`. `<tool-python>` is
`"$(uv tool dir)/playwright/bin/python"`.

## A. Config links and instruction loading

```sh
cd $R
python3 workstation/scripts/link_config.py --project --claude-md --agent claude --agent copilot
```

**Expect** `N of N linked` and exit 0, N being every row it plans. Anything `missing` or `detached` is
repaired by re-running with `--apply`; `diverged` is reconciliation work and is never forced.

Then, **in a session** (yours to run, one per assistant you use):

| Assistant | Command | Expect |
|---|---|---|
| Claude Code, in any repo | `/context` | `~/.claude/CLAUDE.md` under *Memory files* |
| Claude Code, in this repo | `/context` | `AGENTS.md` too, through the one-line `CLAUDE.md` import |
| Copilot CLI | `/context` as the **first** command | a System Prompt figure well above the `copilot --no-custom-instructions` baseline |
| Copilot CLI | `/skills` | every skill `link_config.py` linked |
| VS Code Chat | *Show Chat Debug View*, then search a request's prompt for `REPLY_CEILING` | found — that string exists only in `AGENT-INSTRUCTIONS.md` |

## B. The toolchain, and the machine note it feeds

```sh
python3 workstation/scripts/inventory.py
```

**Expect** `N of N usable` with every row `installed`. `absent` means install it, from that tool's
`install.md`; `blocked` and `error` are diagnosed, not reinstalled. Paste the table into the machine
note — never hand-write it.

One end-to-end render, because a version probe is not a working toolchain:

```sh
printf '# T\n\nPara.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n' > /tmp/v.md
pandoc /tmp/v.md --pdf-engine=typst -o /tmp/v.pdf && file /tmp/v.pdf
```

**Expect** `PDF document`. Plain `pandoc /tmp/v.md -o /tmp/v.pdf` failing with `'pdflatex' not found`
is correct here: this workstation has no LaTeX, so naming the engine is not optional.

## C. Document conversion

Three figure kinds, two fixtures. Counts first, conversion second:

```sh
cd $R/workstation/validation/fixtures
for f in chartex shapes-with-text; do
  X=$(unzip -p $f.docx word/document.xml)
  echo "$f: pic=$(printf '%s' "$X" | grep -o '<pic:pic' | wc -l)" \
       "chart=$(printf '%s' "$X" | grep -o '<c:chart' | wc -l)" \
       "shape=$(printf '%s' "$X" | grep -o '<wps:wsp' | wc -l)"
  docling convert $f.docx --to md --output /tmp/val
done
```

**Expect**, in `/tmp/val/`:

| From | Check | Expect |
|---|---|---|
| `chartex.md` | `grep -c 'data:image/[a-z]*;base64'` | 2 — the pictures, not the charts |
| `chartex.md` | `grep -c 'Image not available'` | 4 |
| `chartex.md` | the chart data | pipe tables of Series/Category values |
| `shapes-with-text.md` | the shape text | five lines, "Floating text box" through "Where some contain text" |
| either | `grep -c '<div\|<header\|<span\|<svg\|<style\|<table\|<img'` | 0 |

Then the base64 split, which every `.docx` and PDF conversion needs:

```sh
$R/.venv/bin/python $R/workstation/agent/skills/fetch-to-markdown/scripts/clean_md_images.py /tmp/val/chartex.md
```

**Expect** `Found 2 embedded images`, a `-no-base64.md` beside the original, and the PNGs in a sibling
folder. To prove they are the source pixels, not a re-render:
`magick compare -metric AE <extracted>.png <word/media/imageN.png> null:` → `0`.

## D. The JS-hydrated route

Take a row from [`fixtures/hydrated-pages.md`](fixtures/hydrated-pages.md) and re-measure it first —
rows go stale.

```sh
U=https://retirejs.github.io/retire.js/
curl -sL -A "Mozilla/5.0" "$U" -o /tmp/raw.html
defuddle parse /tmp/raw.html --md | wc -w
<tool-python> $R/workstation/agent/skills/fetch-to-markdown/scripts/render_page.py "$U" /tmp/r.html
defuddle parse - --md --frontmatter < /tmp/r.html | wc -w
```

**Expect** a raw count in the low hundreds against a rendered count in the thousands, and a rendered
`title:` that is the real page, not *Page Not Found*. Running `render_page.py` under any interpreter
but the uv tool one **must** exit 2 naming the right one — that is the check that the guidance is true.

Where defuddle's output holds a raw `<table>`, finish through the extractor, per the skill's §2:

```sh
$R/.venv/bin/python $R/workstation/agent/skills/fetch-to-markdown/scripts/extract_article.py \
  /tmp/r.html section#main_content "$U" > /tmp/article.html
pandoc -f html -t markdown -o /tmp/r.md /tmp/article.html
```

**Expect** markup count 0 and no relative link left.

## E. The repo's own gates

```sh
cd $R
.venv/bin/python workstation/agent/skills/review/scripts/repo_check.py
.venv/bin/python workstation/agent/skills/verify-docs/scripts/verify_claims.py --repo .
for d in $(grep -v '^#' .pre-push-tests | grep -v '^$'); do
  .venv/bin/python -m unittest discover -s $d -t $d
done
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python -m pyright
```

**Expect** `all enabled checks passed`, `No claim was refuted`, `OK` from every suite, ruff clean,
and `0 errors, 0 warnings, 0 informations` from Pyright.
A `.venv` that does not exist yet is the user's to create (`uv venv`, `uv sync`), never the agent's.
