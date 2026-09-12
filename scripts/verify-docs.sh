#!/usr/bin/env bash
#
# Headless documentation verification. Drives the `verify-docs` skill via
# `claude -p` and writes an evidence report. Read-only: it applies no fixes,
# because deciding whether a refutation has an unambiguous correction is a
# judgement that belongs in a pull request review, not in CI.
#
#   ./scripts/verify-docs.sh                  # whole tracked doc corpus
#   ./scripts/verify-docs.sh README.md        # named files only
#
# Environment:
#   ANTHROPIC_API_KEY   required by `claude -p` in a non-interactive session
#   VERIFY_DOCS_OUT     report path (default: DOCS-VERIFICATION.md)
#   VERIFY_DOCS_MODEL   model alias (default: sonnet)
#   VERIFY_DOCS_BUDGET  hard spend ceiling in USD (default: 5)
#   VERIFY_DOCS_BYPASS  set to 1 to skip the tool allowlist. Only in a
#                       disposable container — verification runs `<bin> --help`
#                       for arbitrary binaries, which no static allowlist covers.
#   VERIFY_DOCS_SETTLED path to a verify_claims.py --json run to reuse. Without
#                       it this script performs that run itself. CI already has
#                       one, and a --online pass costs a round trip per URL.
#   VERIFY_DOCS_ONLINE  0 to keep the deterministic pass off the network.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

OUT="${VERIFY_DOCS_OUT:-DOCS-VERIFICATION.md}"
MODEL="${VERIFY_DOCS_MODEL:-sonnet}"
BUDGET="${VERIFY_DOCS_BUDGET:-5}"
MANIFEST="$(mktemp -t claims.XXXXXX.jsonl)"
SETTLED_TMP="$(mktemp -t settled.XXXXXX.json)"
trap 'rm -f "$MANIFEST" "$SETTLED_TMP"' EXIT

command -v claude >/dev/null || { echo "verify-docs: 'claude' is not on PATH" >&2; exit 127; }
: "${ANTHROPIC_API_KEY:?verify-docs: ANTHROPIC_API_KEY must be set for headless runs}"

SKILL_DIR="${VERIFY_DOCS_SKILL_DIR:-$HOME/.claude/skills/verify-docs}"
EXTRACTOR="$SKILL_DIR/scripts/extract_claims.py"
[ -f "$EXTRACTOR" ] || { echo "verify-docs: extractor not found at $EXTRACTOR" >&2; exit 1; }

echo "verify-docs: extracting claims from ${*:-tracked markdown}"
if [ "$#" -gt 0 ]; then
  python3 "$EXTRACTOR" --repo "$REPO_ROOT" --files "$@" --out "$MANIFEST" --summary
else
  python3 "$EXTRACTOR" --repo "$REPO_ROOT" --out "$MANIFEST" --summary
fi

CLAIM_COUNT="$(wc -l < "$MANIFEST" | tr -d ' ')"

# Settle mechanically first. verify_claims.py runs the same class of checks a
# model would, but from structured fields rather than from the manifest's command
# strings — which matters, because those strings carry the extractor's guess at
# which tool a flag belongs to. `pandoc --help | grep -F -- '--pdf-variant'`
# returns nothing and reads as REFUTED, when the flag is WeasyPrint's and pandoc
# never claimed it. Every claim the deterministic pass settles is one the model
# neither pays for nor can get wrong.
VERIFIER="$SKILL_DIR/scripts/verify_claims.py"
SETTLED=""
if [ -n "${VERIFY_DOCS_SETTLED:-}" ] && [ -f "${VERIFY_DOCS_SETTLED}" ]; then
  SETTLED="$VERIFY_DOCS_SETTLED"
  echo "verify-docs: reusing the deterministic pass at $SETTLED"
elif [ -f "$VERIFIER" ]; then
  ONLINE_ARGS=()
  [ "${VERIFY_DOCS_ONLINE:-1}" = "1" ] && ONLINE_ARGS=(--online)
  echo "verify-docs: settling what a command can settle, deterministically"
  if [ "$#" -gt 0 ]; then
    python3 "$VERIFIER" --repo "$REPO_ROOT" --files "$@" \
      ${ONLINE_ARGS[@]+"${ONLINE_ARGS[@]}"} --json > "$SETTLED_TMP" || true
  else
    python3 "$VERIFIER" --repo "$REPO_ROOT" \
      ${ONLINE_ARGS[@]+"${ONLINE_ARGS[@]}"} --json > "$SETTLED_TMP" || true
  fi
  [ -s "$SETTLED_TMP" ] && SETTLED="$SETTLED_TMP"
fi

if [ -n "$SETTLED" ]; then
  SETTLED_TOTAL="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))))' "$SETTLED")"
  SETTLED_OPEN="$(python3 -c 'import json,sys; print(sum(1 for r in json.load(open(sys.argv[1])) if r["verdict"]=="UNVERIFIABLE"))' "$SETTLED")"
  echo "verify-docs: $SETTLED_TOTAL settled deterministically, $SETTLED_OPEN left for $MODEL"
else
  SETTLED_TOTAL=0
  SETTLED_OPEN="$CLAIM_COUNT"
fi

echo "verify-docs: $CLAIM_COUNT claims extracted; verifying with $MODEL (budget \$$BUDGET)"

PROMPT="$(cat <<PROMPTEOF
Run the verify-docs skill on this repository, non-interactively.

The phase 1 claims manifest has already been built for you at $MANIFEST
($CLAIM_COUNT claims, JSONL, one claim per line). Read it and skip phase 1.

A deterministic pass has already run: $SETTLED_TOTAL claims settled, results at
$SETTLED (JSON array; each row has file, line, kind, claim, verifier, evidence,
verdict). Read it first.

  * Rows it marked VERIFIED or REFUTED are DONE. Carry them into your report
    with their evidence as written. Do not re-run them, and do not overturn
    them — that pass executes structured verifiers, whereas the
    verification_command strings in the manifest can name the wrong tool for a
    flag.
  * The $SETTLED_OPEN rows marked UNVERIFIABLE are your work. For each, decide
    whether a command you can construct here would settle it. If one would, run
    it and record its real output. If none would, keep UNVERIFIABLE and name the
    blocker.
  * Then add the claims no extractor can see: counts ("51 input formats"),
    behavioural assertions ("defaults to LaTeX"), ordering and precedence, and
    anything asserting one tool requires another.

Skip the phase 2 approval gate — there is no user to approve. Do NOT skip
anything else, and do NOT relax the hard rule. Where a command cannot run here,
the verdict is UNVERIFIABLE with the blocker named — never VERIFIED and never a
guess.

Do NOT run phase 5. Apply no fixes and edit no documentation. For each REFUTED
claim, state the correction the evidence supports and whether it is unambiguous
enough to auto-apply, but leave the file untouched.

Write the phase 4 report to $OUT and write no other file. Begin the report with
a one-line summary of counts per status.
PROMPTEOF
)"

CLAUDE_ARGS=(
  -p "$PROMPT"
  --model "$MODEL"
  --max-budget-usd "$BUDGET"
  --output-format text
  --add-dir "$SKILL_DIR"
)

if [ "${VERIFY_DOCS_BYPASS:-0}" = "1" ]; then
  CLAUDE_ARGS+=(--permission-mode bypassPermissions)
else
  CLAUDE_ARGS+=(--allowedTools Read Glob Grep "Write($OUT)" Bash Skill)
fi

claude "${CLAUDE_ARGS[@]}"

[ -f "$OUT" ] || { echo "verify-docs: no report written to $OUT" >&2; exit 1; }
echo "verify-docs: report written to $OUT"
