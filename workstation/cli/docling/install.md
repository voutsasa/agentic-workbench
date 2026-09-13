---
tool: docling
command: docling
product: Docling
verified: 2026-08-26
---

# docling — install

Binary: `docling`. Product: Docling. Python tool, installed the same way on both platforms — not packaged for brew or scoop.

| Platform | Command |
|---|---|
| macOS | `pipx install docling` |
| Windows | `pipx install docling` |

Verify with `docling --version`. It prints a block, one line per component, and **the version numbers deliberately differ** — do not read a mismatch as a fault. A sample, recorded on Windows when this page was written, kept for its shape rather than its numbers:

```
Docling version: 2.122.0
Docling Core version: 2.92.0
Docling IBM Models version: 3.14.0
Docling Parse version: 7.16.0
Python: cpython-312 (3.12.10)
Platform: Windows-11-10.0.26200-SP0
```

The `Python:` line is the interpreter **pipx picked**, not necessarily the machine's default — worth reading when a version trap below applies.

## A successful install can still be an unrunnable one

`pipx install docling` succeeding proves nothing about whether the command runs. On a managed machine,
endpoint security can quarantine the shim afterwards, and the failure then looks like a permissions
fault rather than what it is — `Access is denied` before the process starts, with the ACL granting
`FullControl`.

The test that distinguishes the two is reading the file rather than executing it, and comparing
against another pipx shim in the same directory:

```powershell
[IO.File]::ReadAllBytes("$HOME\.local\bin\docling.exe")     | Measure-Object -Sum Length
[IO.File]::ReadAllBytes("$HOME\.local\bin\playwright.exe")  | Measure-Object -Sum Length
```

If the first is denied and the second reads fine, it is an EDR/antivirus block and **reinstalling will
not clear it.**

**A file that reads fine but still refuses to launch is a different fault, and not this one.** That is a
process-creation rule rather than a quarantined file, so allow-listing the binary is the wrong request:
the block is on running *that name from that location*, and the fix is usually to call a copy the policy
already trusts. Check readability before reporting anything as quarantined — the two failures look
identical at the prompt and have different owners. A worked example, with the sibling comparison that
settles it, is in
[`../../machines/windows-ema-pf5n4xe7.md`](../../machines/windows-ema-pf5n4xe7.md#whoami-and-hostname-are-blocked-in-gits-usrbin-and-it-does-not-matter). Ask the user to have `docling.exe` and `docling-tools.exe` allow-listed. Do not
substitute another route: docling is the primary PDF/Office → markdown route in
[`INGESTION_GUIDE.md`](../../../INGESTION_GUIDE.md), `pandoc` does not cover scanned PDFs, and
`pymupdf` in a project venv is a library rather than a drop-in for the CLI.

Which machines this is currently happening on is recorded in [`../../machines/`](../../machines/), not
here.

## Embedded images need LibreOffice

A `.docx` carrying DrawingML — diagrams, drawn shapes, most pasted figures — converts **at exit 0 with
every image silently dropped** unless LibreOffice is reachable. The only signal is a warning in the log:

```
WARNING docling.backend.msword_backend: Found DrawingML elements in document, but no
DOCX to PDF converters. If you want these exported, make sure you have LibreOffice
binary in PATH or specify its path with DOCLING_LIBREOFFICE_CMD.
```

**Check the image count, not the exit code.** A conversion an order of magnitude smaller than an earlier
one of the same document is this, not a failure:

```powershell
(Select-String -Path out.md -Pattern "data:image/[a-z]+;base64" -AllMatches).Matches.Count
```

**`DOCLING_LIBREOFFICE_CMD` does not work — the warning above is wrong.** Verified against docling
2.122.0: that name appears in the source *only inside the warning string it prints*, and nothing reads
it. Resolution is `shutil.which("libreoffice")`, then `shutil.which("soffice")`, then a hard-coded
`/Applications/LibreOffice.app/Contents/MacOS/soffice`, in `docling/backend/docx/drawingml/utils.py`.
Setting the variable to a real binary changes nothing; **`PATH` is the only route on Windows and Linux.**

Install is the user's, never yours:

| Platform | Command |
|---|---|
| macOS | `brew install --cask libreoffice` — the app-bundle fallback means no `PATH` work is needed |
| Windows | `scoop bucket add extras; scoop install libreoffice`, which installs **no shim** |

### Images cost roughly 100× the conversion time

Measured on one 132 KB `.docx` with 14 DrawingML figures — the same file, the same docling, the only
difference being whether `soffice` resolved:

| `soffice` on `PATH` | Convert time | Output | Images |
|---|---|---|---|
| no | **3.45 s** | 25,646 bytes | 0 |
| yes | **356.62 s** | 367,658 bytes | 14 |

Each figure is a separate headless LibreOffice round-trip, so the cost scales with figure count, not
file size. **Prefer making it opt-in per run over a permanent shim**, so routine conversions stay fast:

```powershell
$env:PATH = "$HOME\scoop\apps\libreoffice\current\LibreOffice\program;" + $env:PATH
```

That is a process-scoped assignment, so it lasts for the shell that set it and nothing else.

**Use the `.com`, not the `.exe`, wherever a path is named.** `soffice.exe` detaches from the console:
`soffice.exe --version` prints nothing and hangs indefinitely. `PATHEXT` puts `.COM` before `.EXE`, so
`which` finds the console variant first on its own — but a hand-written path must say so, and
`get_libreoffice_cmd(raise_if_unavailable=True)` runs `soffice -h` with a 60-second timeout.

Whether LibreOffice is present on a given machine is recorded in
[`../../machines/`](../../machines/), not here.

## Traps

- **Needs Python 3.10 or higher.** 3.9 support was dropped in 2.70.0.
- **Models download on first run, not at install.** The first conversion pulls layout and table-structure models; it is slow and needs network. Air-gapped use requires `--artifacts-path` pointing at a pre-fetched model directory.
- **`pipx` gives the CLI only.** To `from docling.document_converter import DocumentConverter` inside a project, add it there — `uv add docling`.

Docs: [Installation](https://docling-project.github.io/docling/getting_started/installation/) · full page ingest: [reference.md](reference.md)
