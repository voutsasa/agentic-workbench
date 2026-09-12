"""
Reports what a Python project's quality gates would say today, and proposes thresholds from it.

Read-only. Nothing here writes configuration; phase 3 of the skill does that, once a human has
seen the numbers. The point is that a threshold set to an ideal produces a wall of failures and
teaches everyone to bypass the gate, so every proposal here is derived from the code as it stands.

    uv run python measure.py [PATH]

Tools that are not installed are reported as absent rather than installed — what to add is a
decision for phase 2, not a side effect of measuring.
"""

import json
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# The complexity gate is set to the tightest value that is GREEN today, so introducing it never
# turns the build red. What sits at that value is named as the next refactor.

# How far under measured coverage the floor sits: enough that an honest refactor does not fail CI,
# tight enough that a whole untested module does.
COVERAGE_HEADROOM = 5

RADON_LINE = re.compile(r"^\s+\w+ (\d+):\d+ (\S+) - ([A-F]) \((\d+)\)", re.MULTILINE)
# `<name> is too complex (N > 1)` — ruff's own number, which is what C901 gates on.
RUFF_COMPLEXITY = re.compile(r"`([^`]+)` is too complex \((\d+) > \d+\)")
COVERAGE_TOTAL = re.compile(r"^TOTAL\s+\d+\s+\d+\s+(\d+)%", re.MULTILINE)


@dataclass
class Finding:
    """One measurement, and what it implies for a threshold."""

    tool: str
    available: bool
    summary: str
    proposal: str = ""
    detail: list[str] = field(default_factory=list)


def propose_complexity(scores: list[int]) -> int:
    """
    The tightest gate that passes today: the highest complexity any function currently has.

    C901 fails when complexity *exceeds* the gate, so this is green on the day it is introduced and
    fails the moment anything gets worse — which is the whole job of a ratchet. Anything looser is
    slack that hides a regression; anything tighter turns the build red and gets switched off.

    Measure with ruff, not radon: the two count differently. On the project this rule came from,
    ruff scored a function 5 where radon scored it 20, and a gate proposed from radon's numbers
    would have been three levels too loose to catch anything.
    """

    return max(scores, default=5)


def at_the_gate(scores: dict[str, int], gate: int) -> list[str]:
    """
    The functions sitting exactly at the gate — the ones a single added branch would break.

    These are the names that belong in the config comment, because they are what to refactor before
    the gate can be tightened again.
    """

    return sorted(name for name, score in scores.items() if score >= gate)


def propose_coverage(actual: int, headroom: int = COVERAGE_HEADROOM) -> int:
    """The floor to set today: under what the project achieves, never above it, never below zero."""

    return max(0, actual - headroom)


def parse_radon(output: str) -> dict[str, int]:
    """Function name -> cyclomatic complexity, from `radon cc -s` output."""

    return {name: int(score) for _line, name, _grade, score in RADON_LINE.findall(output)}


def parse_coverage(output: str) -> int | None:
    """The TOTAL percentage from a `pytest --cov` terminal report."""

    match = COVERAGE_TOTAL.search(output)
    return int(match.group(1)) if match else None


def parse_ruff_complexity(output: str) -> dict[str, int]:
    """Function name -> ruff's own cyclomatic complexity, from a C901 run with the gate at 1."""

    return {name: int(score) for name, score in RUFF_COMPLEXITY.findall(output)}


def parse_ruff(output: str) -> dict[str, int]:
    """Rule code -> count, from `ruff check --statistics`."""

    counts: dict[str, int] = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].isdigit():
            counts[parts[1]] = int(parts[0])
    return counts


def python_requirement(project: Path) -> str:
    """
    The Python version the project targets, which anything parsing its source must match.

    radon under `uvx` otherwise runs on whatever uv picks, and silently skips files using syntax
    newer than that — reporting a better average than the truth. See references/traps.md.
    """

    pyproject = project / "pyproject.toml"
    if not pyproject.is_file():
        return ""
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    requires = data.get("project", {}).get("requires-python", "")
    match = re.search(r"(\d+\.\d+)", requires)
    return match.group(1) if match else ""


def run(command: list[str], cwd: Path) -> tuple[int, str]:
    """Runs a read-only command and returns its exit code and combined output."""

    # S603: the argument list is built from literals and paths this module controls,
    # never from a shell string, and no shell is involved.
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)  # noqa: S603
    return result.returncode, result.stdout + result.stderr


def measure(project: Path) -> list[Finding]:
    """Every measurement, in the order the report reads best."""

    findings: list[Finding] = []
    venv = project / ".venv" / "bin"
    target = python_requirement(project)

    ruff = venv / "ruff"
    if ruff.is_file():
        _, output = run([str(ruff), "check", ".", "--statistics"], project)
        counts = parse_ruff(output)
        total = sum(counts.values())
        findings.append(
            Finding(
                "ruff",
                True,
                f"{total} finding(s)" if total else "clean",
                detail=[f"{count:>5}  {code}" for code, count in sorted(counts.items(), key=lambda i: -i[1])],
            )
        )
    else:
        findings.append(Finding("ruff", False, "not installed — `uv add --dev ruff`"))

    pyright = venv / "pyright"
    if pyright.is_file():
        _, output = run([str(pyright), "--outputjson"], project)
        try:
            summary = json.loads(output).get("summary", {})
            errors = summary.get("errorCount", "?")
        except json.JSONDecodeError:
            errors = "?"
        findings.append(
            Finding(
                "pyright",
                True,
                f"{errors} error(s)",
                proposal="" if _venv_configured(project) else "set [tool.pyright] venvPath='.' and venv='.venv'",
            )
        )
    else:
        findings.append(Finding("pyright", False, "not installed — `uv add --dev pyright`"))

    python = venv / "python"
    if python.is_file():
        _, output = run([str(python), "-m", "pytest", "-q", "--cov", "--cov-report=term"], project)
        actual = parse_coverage(output)
        if actual is None:
            findings.append(Finding("coverage", False, "no coverage reported — `uv add --dev pytest-cov`"))
        else:
            findings.append(
                Finding("coverage", True, f"{actual}%", proposal=f"--cov-fail-under={propose_coverage(actual)}")
            )
    else:
        findings.append(Finding("coverage", False, "no project venv — run `uv sync` first"))

    if ruff.is_file():
        # Gate at 1 so every function reports its number; this is a measurement, not a check.
        _, output = run([str(ruff), "check", ".", "--select", "C901", "--config", "lint.mccabe.max-complexity = 1"], project)
        scores = parse_ruff_complexity(output)
        if scores:
            gate = propose_complexity(list(scores.values()))
            findings.append(
                Finding(
                    "complexity",
                    True,
                    f"{len(scores)} function(s), worst {max(scores.values())} (ruff C901)",
                    proposal=f"max-complexity = {gate} — green today; at the gate: {', '.join(at_the_gate(scores, gate))}",
                    detail=[f"{score:>5}  {name}" for name, score in sorted(scores.items(), key=lambda i: -i[1])[:8]],
                )
            )
        else:
            findings.append(Finding("complexity", True, "nothing measurable — no functions with branches"))

    if shutil.which("uvx"):
        # radon reports a trend a gate cannot, and must run on the version the project targets:
        # on an older interpreter it skips files silently. See references/traps.md.
        command = ["uvx", "--quiet"]
        if target:
            command += ["--python", target]
        _, output = run([*command, "radon", "cc", ".", "-a", "-nb"], project)
        average = next((line.strip() for line in output.splitlines() if "Average complexity" in line), "")
        findings.append(
            Finding("radon", bool(average), average or "no average reported", proposal="advisory only; ruff is the gate")
        )
    else:
        findings.append(Finding("radon", False, "uvx not on PATH — the trend report is optional"))

    return findings


def _venv_configured(project: Path) -> bool:
    """Whether pyright is pointed at the project venv — the single most common misconfiguration."""

    pyproject = project / "pyproject.toml"
    if not pyproject.is_file():
        return False
    return "venvPath" in tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool", {}).get("pyright", {})


def report(findings: list[Finding]) -> str:
    """The table phase 2 shows the user before anything is written."""

    lines = ["measured", ""]
    for finding in findings:
        mark = "ok  " if finding.available else "--  "
        lines.append(f"{mark}  {finding.tool:<12} {finding.summary}")
        lines += [f"          {row}" for row in finding.detail]
        if finding.proposal:
            lines.append(f"          -> {finding.proposal}")
    lines += [
        "",
        "Thresholds are proposed from these numbers, not from an ideal. Approve or adjust them",
        "before anything is written, and record in the config why each one is where it is.",
    ]
    return "\n".join(lines)


def main() -> int:
    """Measures the project at argv[1], or the working directory."""

    project = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not project.is_dir():
        print(f"error: {project} is not a directory", file=sys.stderr)
        return 2

    print(report(measure(project)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
