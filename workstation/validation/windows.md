# Validating a Windows workstation

The same five sections as [`macos.md`](macos.md), in PowerShell 7. Section letters match, so a machine
note can cite *validation C* whichever box ran it. Record results in that machine's file under
[`../machines/`](../machines/README.md), not here.

Where a step's Windows behaviour is genuinely unknown, it says so. Correct this file from the run
rather than trusting it.

`$Root` below is the clone, the `repo:` field of `~/.claude/machine.md`. `<tool-python>` is the
Playwright uv tool venv's `Scripts\python.exe`, under the directory `uv tool dir` prints.

## A. Config links and instruction loading

```powershell
Set-Location $Root
python workstation\scripts\link_config.py --project --claude-md --agent claude --agent copilot
```

**Expect** `N of N linked` and exit 0. Here the skills are junctions and the files are hardlinks, and
**a hardlink is severed by `git checkout` and by any atomic-saving editor** — so a `detached` row is
routine rather than exceptional, and `--apply` is re-run after merges, branch switches and edits. See
[`../agent/setup/windows.md`](../agent/setup/windows.md#windows-traps).

The in-session checks are identical to macOS section A, with one addition: VS Code's settings live in
`%APPDATA%\Code\User\settings.json`, so `chat.useClaudeMdFile`, `chat.useAgentsMdFile` and
`github.copilot.chat.codeGeneration.useInstructionFiles` are set there.

## B. The toolchain, and the machine note it feeds

```powershell
python workstation\scripts\inventory.py
```

**Expect** `N of N usable`. Two Windows-specific outcomes to read correctly rather than reinstall:
a tool `blocked` by policy, and LibreOffice deliberately off `PATH` — see
[`../cli/docling/install.md`](../cli/docling/install.md).

```powershell
"# T`n`nPara.`n" | Set-Content -Encoding utf8 $env:TEMP\v.md
pandoc $env:TEMP\v.md --pdf-engine=typst -o $env:TEMP\v.pdf
Get-Item $env:TEMP\v.pdf
```

**Expect** a PDF of non-zero length. Note `>` and `Out-File` default to UTF-16LE here and corrupt
markdown; use `Set-Content -Encoding utf8`.

## C. Document conversion

```powershell
Set-Location $Root\workstation\validation\fixtures
foreach ($f in "chartex","shapes-with-text") {
  docling convert "$f.docx" --to md --output $env:TEMP\val
}
Select-String -Path $env:TEMP\val\chartex.md -Pattern 'data:image/[a-z]*;base64' | Measure-Object
Select-String -Path $env:TEMP\val\chartex.md -Pattern 'Image not available'      | Measure-Object
```

**Expect** the same counts as macOS: 2 images and 4 placeholders from `chartex.docx`, the chart data as
pipe tables, and every shape's text from `shapes-with-text.docx`. The figure counts in the source are
read with any unzip tool — `Expand-Archive` to a temp folder, then search `word\document.xml` for
`<pic:pic`, `<c:chart` and `<wps:wsp`.

**Unknown on Windows:** whether docling's output is byte-identical to macOS's. On macOS it was
identical with and without `soffice` on `PATH`; that comparison has not been made here.

## D. The JS-hydrated route

```powershell
$U = "https://retirejs.github.io/retire.js/"
curl.exe -sL -A "Mozilla/5.0" $U | defuddle parse - --md | Measure-Object -Word
& <tool-python> $Root\workstation\agent\skills\fetch-to-markdown\scripts\render_page.py $U $env:TEMP\r.html
Get-Content $env:TEMP\r.html -Raw | defuddle parse - --md --frontmatter | Measure-Object -Word
```

**Expect** a raw count in the low hundreds against a rendered count in the thousands, and a rendered
title that is the real page. Re-measure the row in
[`fixtures/hydrated-pages.md`](fixtures/hydrated-pages.md) first; rows go stale.

`render_page.py`'s exit-2 message must name the uv tool interpreter, as on macOS. It prints
`sys.executable`, and the Windows venv layout ends `Scripts\python.exe` rather than `bin/python` — a
difference the message has to carry, not assume away.

## E. The repo's own gates

```powershell
Set-Location $Root
python workstation\agent\skills\review\scripts\repo_check.py
python workstation\agent\skills\verify-docs\scripts\verify_claims.py --repo .
foreach ($d in (Get-Content .pre-push-tests | Where-Object { $_ -and $_ -notmatch '^#' })) {
  .venv\Scripts\python.exe -m unittest discover -s $d -t $d
}
.venv\Scripts\ruff.exe check . ; .venv\Scripts\ruff.exe format --check .
```

**Expect** `all enabled checks passed`, `No claim was refuted`, `OK` from every suite, and ruff clean.

Two Windows traps that fail this section rather than the thing it tests: the `pre-push` hook is a
**copy** here, not a link, and `core.autocrlf=true` would break it with *bad interpreter* — both in
[`../agent/setup/windows.md`](../agent/setup/windows.md#the-pre-push-gate).
