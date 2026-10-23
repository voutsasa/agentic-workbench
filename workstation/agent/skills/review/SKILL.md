---
name: review
description: Produce a structured, read-only review report for a repo, incl. a set of documents and/or a body of code. Use whenever the user asks to review from, assess, critique, or score a document (guideline, spec, legal/regulatory text, README) or existing code, and wants findings rather than edits. Read-only by default; it applies fixes only when the user explicitly asks for them in the same pass (see Apply mode). Not for code changes the user has asked you to make.
author: Achilleas Voutsas
version: 0.3.0
---

# Review

Read the target, and review for
- consistency
- correctness
- conciseness
then output a structured markdown report. **Read-only by default**: do not run, edit, or fix
anything under review — findings only. Two exceptions, both opt-in: **Apply mode**, when the user asks
in the same breath for the fixes to be applied, and annotating a markdown document in place, which adds
comments but never alters the text under review. Both are described below; neither is the default, and
neither is something to offer unprompted.

## Before starting

Verify you can actually read every target. If macOS Full Disk Access, an auth wall, or a login prompt
blocks a file, stop and say exactly what needs granting — don't review a partial set and don't retry
in a loop.

**Settle the shell tool before the first command when your harness offers more than one.** If the
machine note (`~/.agentic-workbench/machine.md`) records a preferred shell route for this platform and
harness, and the folder under review is not yet set up for it, ask the user once whether to set it up,
and wait for the answer; on a decline, use the note's fallback route. With no machine note, or no route
recorded for your harness, skip this and say so in the scope line. Working around a broken shell tool
silently hides it from the report, and a review that cannot run a command cannot cite evidence. This is
prose rather than a `repo_check.py` rule on purpose — that gate is documentation-only and runs on every
platform.

State up front which files you read, so the scope of the review is unambiguous.

## Report structure

This structure is the reply, and it **overrides `REPLY_CEILING`** — as long as the findings require,
no longer. `REPLY_CEILING` is defined in `~/.claude/CLAUDE.md`.

```markdown
# Review: <target>

## Summary
2–4 sentences: what this is, its overall state, and the single most important thing to address.

## Findings
1. **<Short claim>** — Classify findings by consistency, correctness, conciseness and state what's wrong, where (`file:line` for code, section/page for documents),
   why it matters, and what it would take to fix. Most severe first.
2. ...

## Decisions requested
Each thing only the user can settle — a contradiction with two defensible resolutions, a
missing rule whose content is a judgement call, a scope question. State the options and
your recommendation. Write "None" if there are none; don't fold these into the findings.

## Clarity score: N / 5
One or two sentences justifying the number — what held it down or lifted it.

## Next steps
Ordered, concrete, each one something the user can act on or hand to an agent.
```

**Findings, Decisions requested, and Next steps are always three distinct headed sections**,
even when one is empty. A decision buried in a finding, or a next step implied by one, gets lost.

## What makes a finding worth reporting

- **Anchor it.** Every finding cites a location. A finding without one is an impression.
- **Contradictions first.** Two instructions that collide, or a spec that disagrees with the code or
  with another document, outrank style issues — they force a wrong decision at read time.
- **Say the consequence.** "Section 4 is unclear" is weak; "Section 4 leaves the retention period
  undefined, so an implementer has to guess between 30 days and indefinite" is actionable.
- **Separate severity from taste.** Don't pad the list with preferences to make it look thorough. A
  short, correct review beats a long one.
- **Report what's missing**, not just what's wrong — an absent rule is often the real defect.
- **Cite a primary source for every claim about external tooling** — a live API response, the
  package registry entry, the actual file on disk. A version number, a flag, a package name or an
  install route asserted from memory is a guess; run the command and quote its output, or mark the
  claim unknown.

## Scoring

The clarity score measures how unambiguously a reader can act on the material — not its quality,
ambition, or completeness. Anchor it:

- **5** — no ambiguity; a reader acts correctly without asking questions.
- **4** — sound, with minor gaps that don't change decisions.
- **3** — usable but has real ambiguity, redundancy, or a contradiction a reader must resolve.
- **2** — significant contradictions or gaps; a reader will likely act wrongly.
- **1** — cannot be acted on as written.

Justify the number against these anchors rather than picking one that feels diplomatic.

## Annotating in place (markdown only)

When I ask for the comments *in* the document rather than as a report. Markdown only — for any
other format, ask before editing.

- **Back up to the scratchpad first**, then diff non-comment lines against it and report the
  result. These files are often untracked, so there's no git safety net.
- **If the markdown was converted from a PDF**, diff it against the PDF text before reporting, so
  conversion artifacts aren't reported as document defects. Comment on them; never silently fix them.
- **One blockquote under the clause it concerns**: `**🔴 Opus Review [n]**`, a bolded one-line claim,
  body in italics. Number them, cross-reference related ones (`see **[3]**`), and add a 🟢 key at the
  top plus a closing note carrying the score.
- **Never inline `<span style=...>` for colour** — markdown has no colour, and a renderer that does not
  process HTML prints the raw tag. Keep the `.md` free of raw HTML. The 🔴/🟢 markers plus bold and italics carry the visual
  distinction in every renderer; don't offer to generate HTML or PDF unless asked.

## Apply mode (opt-in)

Only when the user asks for the fixes in the same request — "apply them", "then fix", "don't wait for
approval". Never infer it from a plain review request. The report still comes first, in the structure
above; applying does not replace it.

1. **Rate every finding high / medium / low confidence** in the report, and say what the rating rests
   on. Confidence is about whether the finding is *true*, not how easy the fix is.
2. **Apply high and medium.** Leave low-confidence findings in the report unapplied and say so.
   **Unless the user wants to pick** — "ask me which", "let me approve each": then ask which
   findings to apply, one choice per finding with its confidence, and apply only the approved ones.
   A finding not approved is left unapplied, with *not approved* as its reason.
3. **Stop for product decisions.** Anything where the fix is a judgement call — which of two
   contradicting rules wins, what an absent rule should say, a scope question — goes to *Decisions
   requested* and is left untouched, however confident the finding is. Asking is not a failure of
   nerve here; guessing is.
4. **For a code finding, write the regression test first** and show it failing against the unfixed
   code — quote the failure. A test that passes before the fix proves nothing. Documents have no
   such test; step 5's evidence covers them.
5. **Verify each fix empirically** — re-read the changed lines, run the command, fetch the URL — and
   quote the actual output. A fix asserted without evidence counts as unapplied.
6. **Run the project's full gate**: whatever the repo actually has — the full test suite, not just the
   new test, plus lint, type check, link check. Name each one and give its result. If a gate doesn't
   exist in this repo, say that rather than reporting a pass; a docs repo may have no test suite at all.
7. **Commit each logical group separately**, message per repo convention. Run `git status` and
   `git diff --staged` first: the staged set is that group and nothing else — no unrelated
   pre-existing changes, no deletions or formatter churn nobody asked for.
8. **Record what was found but not fixed** — low confidence, not approved, a decision pending — in the
   repo's TODO file if it keeps one, in the same commit. Where it keeps none, the closing table is
   the record.
9. **Close with the delta re-check** (below), then this table:

   | Finding | Fix | Evidence | Commit |
   |---|---|---|---|

   One row per finding — including the ones left unapplied, with the reason in place of a sha.

## Scripts

| Path | Purpose |
|---|---|
| `scripts/repo_check.py` | Deterministic documentation gate — links, bare repo paths, terminology, frontmatter, and a source register against its catalogue, over the tracked markdown, exiting non-zero on violations. No model, no network, a second or two. Run it by hand, or let the pre-push hook run it. |
| `scripts/repo_check.py --corpus` | The register's ingestion ledger: which entries have an ingested file and which do not. **Not** part of the gate — the corpus is gitignored, so a fresh clone has none and nothing is wrong. The preflight for an ingestion run. |
| `scripts/checks.toml` | The rules it enforces. Tune this file, not the script. |
| `scripts/pre-push` | Git hook wrapper; symlinked into `.git/hooks/pre-push` — **on Windows copy `scripts/pre-push.windows` there instead**, a shim that runs the tracked hook, or the push runs ungated with nothing to show it. `scripts/README.md` § *The pre-push hook* has both routes. |
| `tests/test_repo_check.py` | From the skill root, `<repo>/.venv/bin/python -m unittest discover -s tests -t tests` (`.venv\Scripts\python.exe` on Windows) — stdlib only, on the project venv. |
| `tests/test_pre_push.py` | The hook and the Windows shim, same command. |

`scripts/README.md` carries the exit codes, the scope rule, why every check ships on, and
why claim-verification is `verify-docs`' job rather than this gate's.

## After the fixes are applied

The review isn't closed by handing over findings. When the fixes land — whether I apply them or
`fix-findings` does — re-run the same consistency check over the changed material and report the
**delta**: which findings are now resolved, which are partly addressed, and what the edits
introduced. Never declare it done without that second pass.
