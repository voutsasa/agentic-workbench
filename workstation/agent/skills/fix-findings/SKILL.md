---
name: fix-findings
description: Apply the most recent review's findings, under the review skill's Apply mode. Use when a review has produced findings and the user asks for them to be applied.
author: Achilleas Voutsas
version: 0.6.2
---

# Fix findings

Apply the findings from the most recent review by running **`review`'s Apply mode**.
That section is the only definition of the procedure; this skill exists to start it
without re-running the review first.

**Read the `review` skill's `SKILL.md`, section *Apply mode*, and follow it.** Find it at
`~/.claude/skills/review/` (Claude Code) or `~/.copilot/skills/review/` (Copilot). No
summary is given here on purpose — a copy is what an agent reads instead of the
original, and it is the copy that goes stale.

The one rule most easily lost on the way: a finding whose fix is a judgement call —
which of two contradicting rules wins, what an absent rule should say, a scope
question — goes to *Decisions requested* untouched, however confident the finding is.
Asking is not a failure of nerve here; guessing is.
