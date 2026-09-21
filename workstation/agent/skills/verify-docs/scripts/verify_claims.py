#!/usr/bin/env python3
"""Execute a deterministic verifier for every checkable claim in a repo's markdown.

Phase 3 of the verify-docs skill, done mechanically. `extract_claims.py` finds
candidate claims and *proposes* a command for each; this script decides the
verdict by running one, and never asks a model anything. Same inputs, same
output, on any machine with the same tools installed.

Two tiers, because a push must not depend on someone else's uptime:

    offline (default)  paths, CLI flags, binaries on PATH, version strings
    online (--online)  external URLs and package-registry lookups

Usage:
    python verify_claims.py --repo /path/to/repo            # offline tier
    python verify_claims.py --repo . --online               # add network checks
    python verify_claims.py --repo . --kind version --json
    python verify_claims.py --repo . --strict               # UNVERIFIABLE fails too

Exit codes mirror repo_check.py: 0 clean, 1 something is REFUTED, 2 the gate
itself could not run. UNVERIFIABLE does not fail by default — an uninstalled
tool must not block a push on a machine where the documentation is correct.

No claim's text is ever passed to a shell. Verifiers are built from the claim's
structured fields and run with shell=False, so a command example in a document
cannot execute itself.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
import threading
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Literal
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))

# E402: sys.path has to be extended before this import, so it cannot move up.
from extract_claims import (
    CLI_FLAG,
    CLI_INVOCATION,
    GIT,
    INLINE_CODE_RE,
    INSTALL,
    PATH,
    PATH_EXT_RE,
    URL,
    VERSION,
    Claim,
    extract_repo,
    tracked_markdown,
)

# --- verdicts and exit codes ---------------------------------------------------

VERIFIED = "VERIFIED"
REFUTED = "REFUTED"
UNVERIFIABLE = "UNVERIFIABLE"

EXIT_OK = 0
EXIT_REFUTED = 1
EXIT_ERROR = 2

OFFLINE_KINDS = (PATH, CLI_FLAG, CLI_INVOCATION, VERSION)
ONLINE_KINDS = (URL, INSTALL)

# Generous on purpose. A timeout here is indistinguishable from "the tool
# printed no help", so a slow tool is reported as a refuted claim about a
# perfectly good flag. Measured on Windows 2026-09-21: `docling --version` takes
# 17s and `docling --help` 20s, right on the old 20s limit — which is why the
# same claim came back REFUTED or UNVERIFIABLE depending on machine load.
# The cost of the higher ceiling is paid only by a tool that is genuinely hung,
# and each binary is probed once per run and cached.
HELP_TIMEOUT = 120
VERSION_TIMEOUT = 120
HTTP_TIMEOUT = 10

# A token the document never meant literally. Verifying it proves nothing.
PLACEHOLDER_RE = re.compile(r"[<>{}]|\.\.\.|\bYOUR_|\bPATH_TO\b")
# A cross-platform instruction may name a POSIX venv path before its explicit
# Windows alternative. The earlier path is not a claim about a Windows host.
WINDOWS_VENV_ALTERNATIVE_RE = re.compile(
    r"\bor\s+`\.venv\\Scripts\\python(?:\.exe)?`\s+on\s+Windows\b",
    re.IGNORECASE,
)

ALLOW_FILE_NAME = ".verify-claims-allow"
FLAG_ALLOW_FILE_NAME = ".verify-flags-allow"

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
# `v0.8.1-HEAD`, `1.2026.6`, `69.0`. Anchored so `3.10` in prose is not a version.
VERSION_TOKEN_RE = re.compile(r"v?\d+(?:\.\d+)+(?:[-+][\w.]+)?")


@dataclass
class Result:
    id: str
    file: str
    line: int
    kind: str
    claim: str
    verifier: str
    evidence: str
    verdict: str

    @property
    def location(self) -> str:
        return f"{self.file}:{self.line}"


# --- the base-directory rule ---------------------------------------------------
#
# This is the part that has broken before, so it is written out rather than
# inlined at the call site. A relative path in markdown has *two* plausible
# bases and picking the wrong one silently passes a broken link:
#
#   ./NOTES.md  in workstation/cli/pandoc/quick_start.md
#       means   workstation/cli/pandoc/NOTES.md
#       never   <repo root>/NOTES.md
#
# If a NOTES.md happens to exist at the repo root, a root-first resolver reports
# VERIFIED for a link that is dead in a browser and dead on GitHub. So an
# explicitly anchored path (`./`, `../`) resolves against its own document's
# directory and is given **no fallback**. Only an unanchored token — this repo's
# house style for naming a path in prose, e.g. `docs/guidance/` — may try the
# repo root first and the document's directory second.


def candidate_paths(repo_root: Path, doc: str, token: str) -> list[tuple[str, Path]]:
    """Return (base name, candidate) pairs in the order they should be tried."""
    token = unquote(token.split("#", 1)[0].split("?", 1)[0]).strip()
    if not token:
        return []
    doc_dir = repo_root / Path(doc).parent

    def joined(base: Path) -> Path:
        return Path(os.path.normpath(base / token))

    if token.startswith("~"):
        return [("home", Path(token).expanduser())]
    if token.startswith(("./", "../")):
        # Anchored: the document's own directory, and nothing else.
        return [("document", joined(doc_dir))]
    if token.startswith("/"):
        # A leading slash is root-relative in a site-rendered document, but may
        # also be a genuine absolute path such as ~/.claude's symlink target.
        return [
            ("repo root", joined(repo_root / token.lstrip("/"))),
            ("absolute", Path(token)),
        ]
    return [("repo root", joined(repo_root)), ("document", joined(doc_dir))]


# --- frontmatter, and the version binding it settles ----------------------------


def read_allow_file(repo_root: Path) -> list[str]:
    """Path exemptions declared by the repo being checked, one glob per line.

    Repo-local on purpose. The pre-push hook lives in a globally symlinked
    skills tree, so one copy of it serves every repo that links it; a glob
    written into the hook would silently exempt paths in unrelated repos. No
    file means no globs, and nothing is inherited from anywhere else.
    """
    target = repo_root / ALLOW_FILE_NAME
    if not target.is_file():
        return []
    globs: list[str] = []
    for line in target.read_text(encoding="utf-8", errors="replace").splitlines():
        glob = line.split("#", 1)[0].strip()
        if glob:
            globs.append(glob)
    return globs


def read_flag_allow_file(repo_root: Path) -> frozenset[tuple[str, str]]:
    """Flag claims the repo declares unverifiable, as `<command> <flag>` per line.

    The case this exists for cannot be settled by reading help: `git diff -h`
    documents `--cached` and never mentions `--staged`, which works and exits 0.
    Refuting it is wrong and downgrading every absent flag to UNVERIFIABLE would
    blunt the whole class, so the exemption is declared once, in the repo, where
    a reviewer sees it in a diff — never inferred by the checker.

    Repo-local for the same reason as `ALLOW_FILE_NAME`: the hook is shared, so
    an exemption written into it would travel to unrelated repos. A line with no
    flag on it exempts nothing, so a typo fails closed.
    """
    target = repo_root / FLAG_ALLOW_FILE_NAME
    if not target.is_file():
        return frozenset()
    pairs: set[tuple[str, str]] = set()
    for line in target.read_text(encoding="utf-8", errors="replace").splitlines():
        tokens = line.split("#", 1)[0].split()
        flags = [t for t in tokens if t.startswith("-")]
        command = [t for t in tokens if not t.startswith("-")]
        if len(flags) == 1 and command:
            pairs.add((" ".join(command), flags[0]))
    return frozenset(pairs)


def exemption_notice(sources: dict[str, Sequence[str]]) -> str:
    """Every exemption in force, one block per source. Empty when there are none.

    An exemption nobody sees is one nobody revisits. Both allow files are read
    here, so this is what says they are in force — printed by the code that
    applies them, so the notice cannot drift from what the run did. The pre-push
    hook used to echo the path globs from its own parse of the file; it no longer
    parses it, precisely so that one piece of code owns the policy.

    Keyed by source rather than flattened, because a glob passed as `--allow`
    reported under the repo's file name would be the same drift in miniature.
    Entries are sorted and deduplicated, so two runs of one repo print the same
    lines and a glob given twice is announced once.
    """
    blocks: list[str] = []
    for source, entries in sources.items():
        items = sorted(set(entries))
        if not items:
            continue
        blocks.append(f"verify_claims: {len(items)} exemption(s) from {source}:")
        blocks.extend(f"{'':15}{item}" for item in items)
    return "\n".join(blocks)


def flag_line(
    help_text: str | None, flag: str, negated: re.Pattern[str] | None
) -> str | None:
    """The help line documenting `flag`, plainly or in git's bracket form."""
    if not help_text:
        return None
    if flag in help_text:
        return next((ln.strip() for ln in help_text.splitlines() if flag in ln), flag)
    if negated:
        return next(
            (ln.strip() for ln in help_text.splitlines() if negated.search(ln)), None
        )
    return None


def bracket_negation_re(flag: str) -> re.Pattern[str] | None:
    """`--porcelain` as help may actually print it: `--[no-]porcelain[=<version>]`.

    git writes the optional negation *inside* the flag, so a substring search
    for the flag as documented misses the line that documents it. Only that one
    form is tolerated — a trailing `[=<version>]` needs nothing, since the plain
    search already matches it — and a flag absent in every form still refutes.
    """
    if not flag.startswith("--") or len(flag) <= 2:
        return None
    name = flag[2:]
    stem = name.removeprefix("no-")
    if not stem:
        return None
    return re.compile(rf"--\[no-\]{re.escape(stem)}\b")


def root_is_known(repo_root: Path, doc: str, token: str) -> bool:
    """Is the first segment of an unanchored path a thing we can actually see?

    `repo_check.py` scopes its `bare_paths` check with
    `prefixes = ["workstation/cli/"]` for exactly this reason: a path is
    checkable only when its root is known. A label written relative to some
    implicit parent — `cli/README.md` inside `workstation/mcp/`, meaning
    `workstation/cli/README.md` — resolves from neither base, and refuting it
    blames the document for a base it never claimed. Nor is it this gate's place
    to invent one: guessing that `cli/` means `workstation/cli/` would pass a
    genuinely broken path in any repo where it does not.
    """
    head = token.split("/")[0]
    if not head or head in (".", ".."):
        return True
    return (repo_root / head).exists() or (repo_root / Path(doc).parent / head).exists()


def recorded_machine_platform(repo_root: Path, doc: str) -> str | None:
    """Return the host OS recorded by a machine-state document."""
    if not doc.startswith("workstation/machines/"):
        return None
    fields = parse_frontmatter(
        (repo_root / doc).read_text(encoding="utf-8", errors="replace")
    )
    value = fields.get("platform", "").lower()
    if value.startswith("macos"):
        return "Darwin"
    if value.startswith("windows"):
        return "Windows"
    if value.startswith("linux"):
        return "Linux"
    return None


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse a leading `---` block into key/value pairs. Not a YAML parser."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip("'\"")
    return fields


def frontmatter_version_claims(repo_root: Path, files: list[str]) -> list[Claim]:
    """Emit one version claim per (document, declared command).

    Replaces the extractor's `version` kind outright for these files. That kind
    infers its subject from the prose — the most frequent command head, else the
    folder name with `-cli` stripped — and on this repo it mis-binds three of
    twelve: mermaid-cli's binary is `mmdc` not `mermaid`, dbml-cli ships three
    binaries and none is `dbml`, and plantuml-cli's install page mentions `scoop`
    often enough that PlantUML's version gets attributed to the *installer*.

    Two tools' version numbers look alike; only the frontmatter says which
    number belongs to which binary, so the frontmatter is what we bind to.
    """
    claims: list[Claim] = []
    for rel in files:
        name = Path(rel).name
        if name not in ("install.md", "setup.md"):
            continue
        target = repo_root / rel
        if not target.is_file():
            continue
        fields = parse_frontmatter(target.read_text(encoding="utf-8", errors="replace"))
        expected = fields.get("version_observed", "").strip()
        commands = [
            c.strip() for c in fields.get("command", "").split(",") if c.strip()
        ]
        if not expected or not commands:
            continue
        for binary in commands:
            claims.append(
                Claim(
                    id="",
                    file=rel,
                    line=1,
                    kind=VERSION,
                    claim=f"{binary} reports version {expected}",
                    verification_method="frontmatter_version",
                    verification_command=f"{binary} --version",
                )
            )
    return claims


class ManifestIndex:
    """Versions declared in pyproject.toml / package.json, for diffing against docs."""

    def __init__(self, repo_root: Path) -> None:
        self.entries: dict[str, tuple[str, str]] = {}  # name -> (version, source)
        self._load_pyproject(repo_root / "pyproject.toml")
        self._load_package_json(repo_root / "package.json")

    def _record(self, name: str, version: str, source: str) -> None:
        if name and version:
            self.entries.setdefault(name.strip().lower(), (version.strip(), source))

    def _load_pyproject(self, path: Path) -> None:
        if not path.is_file():
            return
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError):
            return
        project = data.get("project", {})
        self._record(project.get("name", ""), project.get("version", ""), path.name)
        requires = project.get("requires-python", "")
        if requires:
            # `>=3.14` documents a floor, not an installed version. Keep the
            # number; the verifier compares against it as a floor, not equality.
            self._record(
                "python",
                requires.lstrip(">=~^ ").strip(),
                f"{path.name} requires-python",
            )
        for spec in project.get("dependencies", []) or []:
            match = re.match(r"^([A-Za-z0-9._-]+)\s*[=><~!]=*\s*([\w.]+)", str(spec))
            if match:
                self._record(
                    match.group(1), match.group(2), f"{path.name} dependencies"
                )

    def _load_package_json(self, path: Path) -> None:
        if not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        self._record(data.get("name", ""), data.get("version", ""), path.name)
        for section in ("dependencies", "devDependencies"):
            for name, spec in (data.get(section) or {}).items():
                self._record(name, str(spec).lstrip("^~>=< "), f"{path.name} {section}")

    def lookup(self, name: str) -> tuple[str, str] | None:
        return self.entries.get(name.strip().lower())


# --- resolving what a flag actually belongs to ---------------------------------
#
# The extractor binds every flag to the first token of the command, which is
# wrong whenever the flag belongs to a subcommand or to a script. On this repo
# that misfires on 58 of 148 flag claims: `git diff --stat` becomes "git
# supports --stat", `ruff check --fix` becomes "ruff supports --fix", and
# `python3 extract_claims.py --out` becomes "python3 supports --out". Running
# `git --help` then refutes a flag that plainly exists.
#
# So the verifier goes back to the source line and works out the *help subject*
# — the argv prefix whose --help should list the flag.

INTERPRETERS = {"python", "python3", "node", "ruby", "perl"}
SCRIPT_SUFFIXES = (".py", ".js", ".mjs", ".rb", ".pl", ".sh")
# Would fetch and install a package to answer a question. Never in a push gate.
NEVER_RUN = {"npx", "pnpx", "bunx"}
SUBCOMMAND_RE = re.compile(r"^[a-z][a-z0-9-]*$")
# A plausible binary name. Excludes `|`, so a markdown table row — which begins
# with one and can contain a flag in its text — is never read as an invocation.
BINARY_TOKEN_RE = re.compile(r"^[A-Za-z_./~][\w.+/~-]*$")
SOURCE_LINE_CACHE: dict[tuple[str, str], list[str]] = {}
FENCED_LINES_CACHE: dict[tuple[str, str], set[int]] = {}


def source_line(repo_root: Path, file: str, line: int) -> str:
    """The raw text of one line, so a claim can be re-read in its own context.

    Keyed by repo root as well as path: one process may hold more than one tree,
    and two of them both having a `doc.md` must not share an entry.
    """
    key = (str(repo_root), file)
    if key not in SOURCE_LINE_CACHE:
        try:
            SOURCE_LINE_CACHE[key] = (
                (repo_root / file)
                .read_text(encoding="utf-8", errors="replace")
                .splitlines()
            )
        except OSError:
            SOURCE_LINE_CACHE[key] = []
    lines = SOURCE_LINE_CACHE[key]
    return lines[line - 1] if 0 < line <= len(lines) else ""


def fenced_lines(repo_root: Path, file: str) -> set[int]:
    """Line numbers inside a fenced code block, so shell examples can be told apart."""
    key = (str(repo_root), file)
    if key not in FENCED_LINES_CACHE:
        inside = False
        numbers: set[int] = set()
        try:
            text = (repo_root / file).read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        for number, line in enumerate(text.splitlines(), start=1):
            if re.match(r"^\s*(?:```|~~~)", line):
                inside = not inside
                continue
            if inside:
                numbers.add(number)
        FENCED_LINES_CACHE[key] = numbers
    return FENCED_LINES_CACHE[key]


def command_on_line(text: str, flag: str) -> list[str] | None:
    """Recover the invocation carrying `flag` from a markdown line."""
    candidates = [text.strip().lstrip("$> ").strip()]
    candidates += [m.strip() for m in INLINE_CODE_RE.findall(text)]
    for candidate in candidates:
        if flag in candidate.split() or any(
            t.startswith(flag + "=") for t in candidate.split()
        ):
            tokens = [t for t in candidate.split() if t]
            if tokens and BINARY_TOKEN_RE.match(tokens[0]):
                return tokens
    return None


def help_subject(
    repo_root: Path, doc: str, tokens: list[str], flag: str
) -> tuple[list[str], str] | Literal["no-script"] | None:
    """The argv prefix to run --help on, plus a human label. None when unsafe.

    ``"no-script"`` when an interpreter names no script this repo holds.
    """
    head = tokens[0]
    if head in NEVER_RUN:
        return None
    if head in INTERPRETERS:
        for token in tokens[1:]:
            if token.endswith(SCRIPT_SUFFIXES):
                for _base, candidate in candidate_paths(repo_root, doc, token):
                    if candidate.is_file():
                        return ([head, str(candidate)], f"{head} {Path(token).name}")
                return "no-script"  # named a script that is not here
        return "no-script"  # an interpreter with no script
    # A bare word before the flag is a subcommand: `git diff --stat`.
    flag_at = next(
        (i for i, t in enumerate(tokens) if t == flag or t.startswith(flag + "=")),
        len(tokens),
    )
    subcommand = None
    if flag_at > 1:
        nxt = tokens[1]
        if SUBCOMMAND_RE.match(nxt) and "/" not in nxt and "." not in nxt:
            subcommand = nxt
    if subcommand:
        return ([head, subcommand], f"{head} {subcommand}")
    return ([head], head)


# --- verifiers -----------------------------------------------------------------

FLAG_CLAIM_RE = re.compile(r"^(?P<binary>\S+)\s+supports\s+(?P<flag>-{1,2}[\w-]+)$")
VERSION_CLAIM_RE = re.compile(
    r"^(?P<binary>\S+)\s+reports version\s+(?P<expected>\S+)$"
)

REGISTRY_API = {
    "npm view": ("npm", "https://registry.npmjs.org/{pkg}"),
    "pip index versions": ("PyPI", "https://pypi.org/pypi/{pkg}/json"),
    "brew info": ("Homebrew", "https://formulae.brew.sh/api/formula/{pkg}.json"),
}


def clip(text: object, width: int = 110) -> str:
    """One line, bounded — an evidence column is not a place for a help screen."""
    flat = " ".join(str(text).split())
    return flat if len(flat) <= width else flat[: width - 1] + "…"


HELP_FLAGS = ("--help", "-h", "--help-extra")
OVERSTRIKE_RE = re.compile(r".\x08")
MAX_SUBCOMMANDS = 6
COMMANDS_HEADING_RE = re.compile(
    r"^\s*(?:[|│╭─\s]*)(?:Commands|COMMANDS|Subcommands)\b"
)
# A word at the start of a help line, after any box drawing: `│ convert   ...`
COMMAND_WORD_RE = re.compile(r"^[\s|│├╰╭─]*([a-z][a-z0-9-]{1,24})(?:\s{2,}|\s*$|\s*\[)")


def advertised_subcommands(help_text: str) -> list[str]:
    """Subcommands a tool lists in its own help, in the order it lists them.

    Needed because a documented flag often lives one level down: docling moved
    its conversion options under `docling convert`, and defuddle's live under
    `defuddle parse`. Reading the tool's own Commands section keeps the search
    bounded and deterministic — no guessing at names that were never advertised.
    """
    found: list[str] = []
    in_section = False
    for line in help_text.splitlines():
        if COMMANDS_HEADING_RE.match(line):
            in_section = True
            continue
        if not in_section:
            continue
        if not line.strip() or set(line.strip()) <= set("─═-_ ╰╯│|"):
            continue
        match = COMMAND_WORD_RE.match(line)
        if match and match.group(1) not in (
            "help",
            "options",
            "usage",
            "commands",
            *found,
        ):
            found.append(match.group(1))
        if len(found) >= MAX_SUBCOMMANDS:
            break
    return found


class Verifier:
    """Runs one mechanical check per claim, caching the expensive subprocesses."""

    def __init__(
        self,
        repo_root: Path,
        online: bool = False,
        allow_globs: tuple[str, ...] = (),
        flag_exemptions: frozenset[tuple[str, str]] = frozenset(),
    ) -> None:
        self.repo_root = repo_root
        self.online = online
        self.allow_globs = allow_globs
        self.flag_exemptions = flag_exemptions
        self.manifests = ManifestIndex(repo_root)
        self._help: dict[tuple[str, ...], str | None] = {}
        self._help_locks: dict[tuple[str, ...], threading.Lock] = {}
        self._version: dict[str, str | None] = {}
        self._version_locks: dict[str, threading.Lock] = {}
        self._cache_guard = threading.Lock()

    # -- process plumbing. shell=False everywhere, on purpose.

    def _run(self, argv: list[str], timeout: int) -> str | None:
        """Combined stdout+stderr, or None when the binary could not be run.

        The exit status is ignored deliberately: plenty of tools print their
        help and then exit 1, and `--version` on a Java wrapper is noisy. What
        is being tested is the *text*, not the status.
        """
        executable = sys.executable if argv[0] in INTERPRETERS else argv[0]
        if not shutil.which(executable):
            return None
        try:
            done = subprocess.run(
                [executable, *argv[1:]],
                check=False,  # the text is under test, not the status
                capture_output=True,
                text=True,
                timeout=timeout,
                errors="replace",
                stdin=subprocess.DEVNULL,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        # A piped man page (`git diff --help`) still carries nroff overstrike:
        # bold is `c\bc` and underline `_\bc`, so `--staged` never matches as text.
        return OVERSTRIKE_RE.sub("", (done.stdout or "") + (done.stderr or ""))

    def help_output(self, argv: list[str], help_flag: str = "--help") -> str | None:
        """One help screen, cached — 148 flag claims share about 23 subjects."""
        key = (*argv, help_flag)
        with self._cache_guard:
            lock = self._help_locks.setdefault(key, threading.Lock())
        with lock:
            with self._cache_guard:
                if key in self._help:
                    return self._help[key]
            output = self._run([*argv, help_flag], HELP_TIMEOUT)
            with self._cache_guard:
                self._help[key] = output
            return output

    def version_text(self, binary: str) -> str | None:
        with self._cache_guard:
            lock = self._version_locks.setdefault(binary, threading.Lock())
        with lock:
            with self._cache_guard:
                if binary in self._version:
                    return self._version[binary]
            output = self._run([binary, "--version"], VERSION_TIMEOUT)
            with self._cache_guard:
                self._version[binary] = output
            return output

    # -- one method per claim kind

    def verify_path(self, claim: Claim) -> tuple[str, str, str]:
        token = claim.claim.strip().strip("`")
        if PLACEHOLDER_RE.search(token):
            return (
                "filesystem",
                f"`{token}` is a placeholder, not a path",
                UNVERIFIABLE,
            )
        if (
            platform.system() == "Windows"
            and token == ".venv/bin/python"
            and WINDOWS_VENV_ALTERNATIVE_RE.search(
                source_line(self.repo_root, claim.file, claim.line)
            )
        ):
            return (
                "filesystem",
                "POSIX venv path has an explicit Windows alternative on this line",
                UNVERIFIABLE,
            )
        # `[text](target)` in a line explaining link syntax yields "target".
        # A token with neither a separator nor an extension is not a path.
        if "/" not in token and not PATH_EXT_RE.search(token):
            return (
                "filesystem",
                f"`{token}` names no directory or file type",
                UNVERIFIABLE,
            )
        # `/plugin` and `/config` are slash commands, not absolute paths.
        if (
            token.startswith("/")
            and token.count("/") == 1
            and not PATH_EXT_RE.search(token)
        ):
            return (
                "filesystem",
                f"`{token}` reads as a command, not a path",
                UNVERIFIABLE,
            )
        if any(fnmatch(token, pattern) for pattern in self.allow_globs):
            # Source-neutral on purpose: `--allow` and ALLOW_FILE_NAME both fill
            # allow_globs and arrive here flattened, so naming either one would be
            # wrong half the time. The notice printed before the run says which
            # file or flag declared what.
            return ("filesystem", "exempt by an allow glob", UNVERIFIABLE)

        if token.startswith(("./", "../")) and claim.line in fenced_lines(
            self.repo_root, claim.file
        ):
            # `ln -sf ../../…/pre-push .git/hooks/pre-push` is relative to the
            # link's own directory, not to the document. The working directory a
            # shell example assumes is prose, not data, so this is not decidable.
            return (
                "filesystem",
                "relative path in a shell block — working directory unknown",
                UNVERIFIABLE,
            )

        candidates = candidate_paths(self.repo_root, claim.file, token)
        if not candidates:
            return ("filesystem", "empty target", UNVERIFIABLE)
        candidate_names = [
            str(candidate.relative_to(self.repo_root)).replace(os.sep, "/")
            for _base, candidate in candidates
            if candidate.is_relative_to(self.repo_root)
        ]
        if any(
            fnmatch(candidate_name, pattern)
            for candidate_name in candidate_names
            for pattern in self.allow_globs
        ):
            return ("filesystem", "exempt by an allow glob", UNVERIFIABLE)
        # A POSIX path on Windows skips the existence check, so the verdict does not
        # depend on the host: `/dev/null` exists on a POSIX box, never on Windows.
        posix_on_windows = token.startswith("/") and platform.system() == "Windows"
        if not posix_on_windows:
            for base, candidate in candidates:
                if candidate.exists() or candidate.is_symlink():
                    return ("filesystem", f"exists, resolved from the {base}", VERIFIED)
        documented_os = recorded_machine_platform(self.repo_root, claim.file)
        if documented_os and documented_os != platform.system():
            return (
                "filesystem",
                f"recorded for {documented_os}; verifier runs on {platform.system()}",
                UNVERIFIABLE,
            )
        if posix_on_windows:
            return (
                "filesystem",
                "POSIX path cannot be verified on Windows",
                UNVERIFIABLE,
            )
        # Outside the repo the filesystem describes this machine, not the docs.
        # `~/.claude/settings.local.json` is documented as deliberately absent.
        if token.startswith("~"):
            return (
                "filesystem",
                f"{token} is absent here — machine state, not repo truth",
                UNVERIFIABLE,
            )
        if (
            "/" in token
            and not token.startswith(("/", "./", "../"))
            and not root_is_known(self.repo_root, claim.file, token)
        ):
            head = token.split("/")[0]
            return (
                "filesystem",
                f"`{head}/` is at neither base — the path's root is unknown",
                UNVERIFIABLE,
            )
        tried = ", ".join(f"{base}: {candidate}" for base, candidate in candidates)
        return ("filesystem", f"no such path — tried {tried}", REFUTED)

    def find_flag(self, argv: list[str], flag: str) -> tuple[str, str] | None:
        """Search a bounded help ladder for `flag`. Returns (label, evidence line).

        Three rungs, cheapest first. `--help` is not universal, and Git for
        Windows opens it in a browser, so Git is restricted to side-effect-free
        `-h`. Other tools also try `--help-extra`, where tesseract keeps `--psm`.
        Then, and only if the flag is still missing, advertised subcommands.
        """
        if flag in ("--version", "-V", "-v"):
            text = self._run([*argv, flag], VERSION_TIMEOUT)
            if text and text.strip():
                return (f"{argv[0]} {flag}", clip(text.splitlines()[0], 80))
        negated = bracket_negation_re(flag)
        is_git = Path(argv[0]).name.lower() in {"git", "git.exe"}
        help_flags = ("-h",) if is_git else HELP_FLAGS
        for help_flag in help_flags:
            line = flag_line(self.help_output(argv, help_flag), flag, negated)
            if line:
                label = " ".join(Path(a).name for a in argv)
                return (f"{label} {help_flag}", clip(line, 80))
        subcommand_help = "-h" if is_git else "--help"
        top = self.help_output(argv, help_flags[0]) or ""
        for sub in advertised_subcommands(top):
            line = flag_line(
                self.help_output([*argv, sub], subcommand_help), flag, negated
            )
            if line:
                label = " ".join(Path(a).name for a in argv)
                return (f"{label} {sub} --help", clip(line, 80))
        return None

    def verify_cli_flag(self, claim: Claim) -> tuple[str, str, str]:
        match = FLAG_CLAIM_RE.match(claim.claim)
        if not match:
            return (
                "help_text",
                f"claim not parseable as a flag: {claim.claim}",
                UNVERIFIABLE,
            )
        binary, flag = match.group("binary"), match.group("flag")
        if PLACEHOLDER_RE.search(binary):
            return ("help_text", f"`{binary}` is a placeholder", UNVERIFIABLE)

        if flag.endswith("-"):
            return (
                "help_text",
                f"`{flag}` is a truncated wildcard, not a flag",
                UNVERIFIABLE,
            )
        tokens = command_on_line(
            source_line(self.repo_root, claim.file, claim.line), flag
        )
        # No invocation on the line means the subject came from the extractor's
        # guess at what the *document* is about — the most frequent command head.
        # That guess crosses tools: the pdf-deliverable skill compares pandoc and
        # WeasyPrint, so WeasyPrint's `--pdf-variant` is attributed to pandoc,
        # whose help has never listed it. A guessed subject may be confirmed but
        # must never be refuted.
        inferred = tokens is None
        if inferred:
            tokens = [binary, flag]
        subject = help_subject(self.repo_root, claim.file, tokens, flag)
        if subject is None:
            return (
                "help_text",
                f"`{tokens[0]}` would install a package to answer — not run in a gate",
                UNVERIFIABLE,
            )
        if subject == "no-script":
            return (
                "help_text",
                f"`{tokens[0]}` runs a script this repo does not hold",
                UNVERIFIABLE,
            )
        argv, label = subject
        if PLACEHOLDER_RE.search(argv[0]):
            return ("help_text", f"`{argv[0]}` is a placeholder", UNVERIFIABLE)

        if not shutil.which(argv[0]):
            return ("help_text", f"{argv[0]} is not on PATH here", UNVERIFIABLE)
        hit = self.find_flag(argv, flag)
        if hit:
            where, line = hit
            return ("help_text", f"`{where}`: {line}", VERIFIED)
        # A subcommand guess that missed must not refute a real top-level flag.
        if len(argv) > 1:
            hit = self.find_flag(argv[:1], flag)
            if hit:
                where, line = hit
                return ("help_text", f"`{where}`: {line}", VERIFIED)
        if not any(self.help_output(argv, hf) for hf in HELP_FLAGS):
            return (
                "help_text",
                f"`{argv[0]}` prints no help — nothing to check against",
                UNVERIFIABLE,
            )
        if inferred:
            return (
                "help_text",
                f"{flag} is not {binary}'s; the subject was inferred from prose, not an invocation",
                UNVERIFIABLE,
            )
        # Last rung, and only ever downgrades a refutation: the repo has declared
        # this exact command-and-flag pair unanswerable from help text. It never
        # reaches a claim the probes confirmed, and it is bound to the command, so
        # an exemption for one subcommand does not travel to another.
        if (label, flag) in self.flag_exemptions:
            return (
                "help_text",
                f"`{label} {flag}` is listed in {FLAG_ALLOW_FILE_NAME}",
                UNVERIFIABLE,
            )
        return (
            "help_text",
            f"{flag} absent from the help of `{' '.join(argv)}`",
            REFUTED,
        )

    def verify_cli_invocation(self, claim: Claim) -> tuple[str, str, str]:
        head = claim.claim.split()[0] if claim.claim.split() else ""
        if not head or PLACEHOLDER_RE.search(head):
            return ("binary_present", f"`{head}` is a placeholder", UNVERIFIABLE)
        found = shutil.which(head)
        if found:
            return ("binary_present", found, VERIFIED)
        return ("binary_present", f"{head} is not on PATH here", UNVERIFIABLE)

    def verify_version(self, claim: Claim) -> tuple[str, str, str]:
        """Diff a documented version against the binary, or against a manifest.

        Manifest first when the subject is named in pyproject.toml/package.json,
        because that file is the declaration of record; otherwise ask the binary
        itself. The subject always comes from a structured source — frontmatter
        `command`, or a manifest key — never from prose adjacency.
        """
        match = VERSION_CLAIM_RE.match(claim.claim)
        if not match:
            return ("version_diff", f"claim not parseable: {claim.claim}", UNVERIFIABLE)
        binary, expected = match.group("binary"), match.group("expected")

        declared = self.manifests.lookup(binary)
        if declared:
            value, source = declared
            if expected.lstrip("v") == value.lstrip("v"):
                return ("manifest_diff", f"{source} declares {value}", VERIFIED)
            return (
                "manifest_diff",
                f"{source} declares {value}, doc says {expected}",
                REFUTED,
            )

        text = self.version_text(binary)
        if text is None:
            return ("binary_version", f"{binary} is not on PATH here", UNVERIFIABLE)
        if not text.strip():
            return (
                "binary_version",
                f"`{binary} --version` produced no output",
                UNVERIFIABLE,
            )
        if expected.lstrip("v") in text.replace("v", ""):
            return ("binary_version", clip(text.splitlines()[0]), VERIFIED)
        found = VERSION_TOKEN_RE.findall(text)
        actual = found[0] if found else clip(text.splitlines()[0])
        return ("binary_version", f"reports {actual}, doc says {expected}", REFUTED)

    def verify_url(self, claim: Claim) -> tuple[str, str, str]:
        url = claim.claim.strip()
        if PLACEHOLDER_RE.search(url):
            return ("http_head", "templated URL, not an address", UNVERIFIABLE)
        request = urllib.request.Request(
            url, method="HEAD", headers={"User-Agent": "verify-claims"}
        )
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
                return ("http_head", f"HTTP {response.status}", VERIFIED)
        except urllib.error.HTTPError as error:
            if error.code in (403, 405, 429):
                # Bot-blocked or HEAD-refused. The address is not disproved.
                return (
                    "http_head",
                    f"HTTP {error.code} — server refused the probe",
                    UNVERIFIABLE,
                )
            return ("http_head", f"HTTP {error.code}", REFUTED)
        except (urllib.error.URLError, OSError, ValueError) as error:
            return ("http_head", f"unreachable: {clip(error, 60)}", UNVERIFIABLE)

    def verify_install(self, claim: Claim) -> tuple[str, str, str]:
        lookup = claim.verification_command
        for prefix, (registry, template) in REGISTRY_API.items():
            if lookup.startswith(prefix):
                # The lookup carries the manager's own flags and trailing
                # subcommands — `brew info --json=v2 sem`, `npm view sem version`.
                # Take the first token that is neither, or the package name comes
                # out as "--json=v2 sem" and every install claim is refuted.
                rest = [
                    token
                    for token in lookup[len(prefix) :].split()
                    if not token.startswith("-")
                ]
                pkg = rest[0] if rest else ""
                if pkg in ("version", "versions"):
                    pkg = ""
                if not pkg or PLACEHOLDER_RE.search(pkg):
                    return (
                        "registry_lookup",
                        "package name is a placeholder",
                        UNVERIFIABLE,
                    )
                url = template.format(pkg=urllib.parse.quote(pkg, safe="@/"))
                try:
                    with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as response:
                        payload = json.loads(response.read().decode("utf-8", "replace"))
                except urllib.error.HTTPError as error:
                    if error.code == 404:
                        return (
                            "registry_lookup",
                            f"{registry} has no package {pkg}",
                            REFUTED,
                        )
                    return (
                        "registry_lookup",
                        f"{registry} returned {error.code}",
                        UNVERIFIABLE,
                    )
                except (urllib.error.URLError, OSError, ValueError) as error:
                    return (
                        "registry_lookup",
                        f"unreachable: {clip(error, 60)}",
                        UNVERIFIABLE,
                    )
                version = ""
                if isinstance(payload, dict):
                    version = (
                        payload.get("dist-tags", {}).get("latest")
                        or payload.get("info", {}).get("version")
                        or payload.get("versions", {}).get("stable")
                        or ""
                    )
                return (
                    "registry_lookup",
                    f"{registry} has {pkg} {version}".strip(),
                    VERIFIED,
                )
        return ("registry_lookup", f"no registry adapter for `{lookup}`", UNVERIFIABLE)

    # -- dispatch

    def verify(self, claim: Claim) -> Result:
        handlers = {
            PATH: self.verify_path,
            CLI_FLAG: self.verify_cli_flag,
            CLI_INVOCATION: self.verify_cli_invocation,
            VERSION: self.verify_version,
            URL: self.verify_url,
            INSTALL: self.verify_install,
        }
        if claim.kind == GIT:
            verifier, evidence, verdict = (
                "git_state",
                "prose assertion about repo state — no single command settles it",
                UNVERIFIABLE,
            )
        elif claim.kind in ONLINE_KINDS and not self.online:
            verifier, evidence, verdict = (
                handlers[claim.kind].__name__.removeprefix("verify_"),
                "skipped — network tier, run with --online",
                UNVERIFIABLE,
            )
        else:
            handler = handlers.get(claim.kind)
            if handler is None:
                verifier, evidence, verdict = (
                    "none",
                    f"no verifier for kind {claim.kind}",
                    UNVERIFIABLE,
                )
            else:
                verifier, evidence, verdict = handler(claim)
        return Result(
            id=claim.id,
            file=claim.file,
            line=claim.line,
            kind=claim.kind,
            claim=claim.claim,
            verifier=verifier,
            evidence=evidence,
            verdict=verdict,
        )


# --- collection ----------------------------------------------------------------


def collect_claims(
    repo_root: Path, files: list[str], kinds: tuple[str, ...] | None = None
) -> list[Claim]:
    """Every claim to be verified, with version claims re-bound to frontmatter.

    The extractor's own `version` kind is dropped rather than filtered later:
    keeping both would report the same tool twice, once against the binary the
    frontmatter names and once against whatever binary the prose mentioned most.
    """
    claims = [c for c in extract_repo(repo_root, files) if c.kind != VERSION]
    claims.extend(frontmatter_version_claims(repo_root, files))
    if kinds:
        claims = [c for c in claims if c.kind in kinds]
    claims.sort(key=lambda c: (c.file, c.line, c.kind, c.claim))
    for index, claim in enumerate(claims, start=1):
        claim.id = f"C{index:04d}"
    return claims


def run(
    repo_root: Path,
    claims: list[Claim],
    online: bool = False,
    allow_globs: tuple[str, ...] = (),
    flag_exemptions: frozenset[tuple[str, str]] = frozenset(),
    workers: int = 8,
) -> list[Result]:
    """Verify every claim. Order, and therefore the report, is independent of workers.

    The wall clock here is almost entirely spent waiting on `--help` and on the
    network, so threads help and the GIL does not get in the way. Each claim's
    verdict depends only on that claim, so `pool.map` — which preserves input
    order — gives byte-identical output at any worker count. `--workers 1` runs
    it sequentially when a reproduction needs to be exact.
    """
    verifier = Verifier(
        repo_root,
        online=online,
        allow_globs=allow_globs,
        flag_exemptions=flag_exemptions,
    )
    if workers <= 1:
        return [verifier.verify(claim) for claim in claims]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(verifier.verify, claims))


# --- report --------------------------------------------------------------------


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def format_report(results: list[Result], online: bool = False) -> str:
    counts = Counter(r.verdict for r in results)
    refuted = [r for r in results if r.verdict == REFUTED]
    unverifiable = [r for r in results if r.verdict == UNVERIFIABLE]

    lines: list[str] = []
    tier = "offline + online" if online else "offline"
    lines.append(f"# Documentation truth gate — {len(results)} claims, {tier} tier")
    lines.append("")
    lines.append(
        f"**{counts[VERIFIED]} verified · {counts[REFUTED]} refuted · "
        f"{counts[UNVERIFIABLE]} unverifiable**"
    )
    lines.append("")

    def table(rows: list[Result], heading: str) -> None:
        if not rows:
            return
        lines.append(f"## {heading}")
        lines.append("")
        lines.append("| id | claim | location | verifier | evidence | verdict |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for r in rows:
            lines.append(
                f"| {r.id} | {cell(clip(r.claim, 70))} | {cell(r.location)} | "
                f"{r.verifier} | {cell(r.evidence)} | {r.verdict} |"
            )
        lines.append("")

    # Refuted first: those are the rows that fail the gate and need acting on.
    table(refuted, "Refuted")
    table(unverifiable, "Unverifiable")

    if refuted:
        by_file = Counter(r.file for r in refuted)
        lines.append(
            "Files to fix: " + ", ".join(f"{f} ({n})" for f, n in by_file.most_common())
        )
    else:
        lines.append("No claim was refuted.")
    return "\n".join(lines)


# Bundles worth pointing an interpreter at, in the order they are usually the
# right answer. Homebrew's is listed first on macOS because it is the one a
# `brew install ca-certificates` keeps current.
CA_BUNDLE_CANDIDATES = (
    "/opt/homebrew/etc/ca-certificates/cert.pem",
    "/usr/local/etc/ca-certificates/cert.pem",
    "/etc/ssl/cert.pem",
    "/etc/ssl/certs/ca-certificates.crt",
)


def tls_advice() -> list[str]:
    """What this interpreter uses for CA certificates, and how to fix it.

    Deliberately says nothing about how Python was installed. The obvious guess
    is wrong often enough to send someone down the wrong path: a machine whose
    owner installs everything through Homebrew can still be running a python.org
    framework build, because that one lands earlier on PATH. So report the
    interpreter actually in use, the paths it actually consults, and a bundle
    that actually exists — and let the facts pick the fix.
    """
    lines = [f"interpreter: {sys.executable}  ({sys.version.split()[0]})"]

    configured = os.environ.get("SSL_CERT_FILE")
    if configured:
        lines.append(
            f"SSL_CERT_FILE={configured}  (exists={Path(configured).exists()})"
        )
    else:
        lines.append("SSL_CERT_FILE is not set.")

    paths = ssl.get_default_verify_paths()
    for label, value in (
        ("cafile", paths.cafile),
        ("openssl_cafile", paths.openssl_cafile),
    ):
        if value:
            lines.append(f"{label}: {value}  (exists={Path(value).exists()})")

    try:
        import certifi  # pyright: ignore[reportMissingImports] — optional; absence handled below

        lines.append(f"certifi is installed: {certifi.where()}")
    except ImportError:
        lines.append("certifi is not importable from this interpreter.")

    usable = next((c for c in CA_BUNDLE_CANDIDATES if Path(c).is_file()), None)
    if usable:
        lines.append(f"A usable bundle is present at {usable}. To use it:")
        lines.append(f'  export SSL_CERT_FILE="{usable}"')
        lines.append(
            '  export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"   # requests ignores the first'
        )
        lines.append(
            "Put both in ~/.zshenv, not ~/.zshrc: a git hook is not an interactive shell."
        )
    else:
        lines.append("No CA bundle found in the usual places. Install one — on macOS,")
        lines.append("  brew install ca-certificates")
    return lines


def transport_failure(results: list[Result]) -> str | None:
    """Is the online tier broken outright, rather than the sites being down?

    176 URLs failing with one identical TLS error is not 176 unverifiable claims;
    it is a gate that cannot run, dressed up as a clean report. The usual cause
    on macOS is a python.org interpreter with no CA bundle — `curl` succeeds and
    `urllib` does not — which makes every URL look individually unreachable.
    """
    urls = [r for r in results if r.kind == URL]
    unreachable = [r for r in urls if r.evidence.startswith("unreachable:")]
    if len(urls) < 10 or len(unreachable) < 0.8 * len(urls):
        return None
    reasons = Counter(r.evidence.split(":", 2)[-1].strip()[:60] for r in unreachable)
    reason, count = reasons.most_common(1)[0]
    if count < 0.8 * len(unreachable):
        return None  # varied failures: the web, not the tier
    return (
        f"{len(unreachable)} of {len(urls)} URL checks failed identically: {reason}. "
        "That is the transport, not the documentation."
    )


# --- entry point ---------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repo", default=".", type=Path, help="repository root")
    parser.add_argument(
        "--files", nargs="*", help="repo-relative files (default: tracked *.md)"
    )
    parser.add_argument(
        "--kind", action="append", help="verify only this claim kind (repeatable)"
    )
    parser.add_argument(
        "--online", action="store_true", help="also verify URLs and registry lookups"
    )
    parser.add_argument(
        "--strict", action="store_true", help="UNVERIFIABLE fails the gate too"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        metavar="N",
        help="parallel verifiers (default 8; 1 forces sequential)",
    )
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="GLOB",
        help=f"exempt path claims matching this glob; adds to {ALLOW_FILE_NAME}",
    )
    parser.add_argument(
        "--no-allow-file",
        action="store_true",
        help=f"ignore the repo's {ALLOW_FILE_NAME} and {FLAG_ALLOW_FILE_NAME}",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable results")
    parser.add_argument(
        "--report-from",
        type=Path,
        metavar="FILE",
        help="render the report from a saved --json run; verifies nothing",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="print only the counts line"
    )
    parser.add_argument(
        "--include-sources", action="store_true", help="include docs/landing-zone/"
    )
    args = parser.parse_args(argv)

    repo = args.repo.resolve()

    # Re-render a run that already happened. Verifying costs a network round trip
    # per URL, so a report and a machine-readable record should not need two.
    if args.report_from:
        try:
            saved = json.loads(args.report_from.read_text(encoding="utf-8"))
            results = [Result(**row) for row in saved]
        except (OSError, json.JSONDecodeError, TypeError) as error:
            print(
                f"verify_claims: cannot read {args.report_from}: {error}",
                file=sys.stderr,
            )
            return EXIT_ERROR
        print(format_report(results, online=args.online))
        failed = [r for r in results if r.verdict == REFUTED]
        if args.strict:
            failed += [r for r in results if r.verdict == UNVERIFIABLE]
        return EXIT_REFUTED if failed else EXIT_OK

    try:
        excludes = () if args.include_sources else ("docs/landing-zone/",)
        files = args.files or tracked_markdown(repo, excludes)
        if not files:
            print(
                "verify_claims: no markdown in scope — refusing to report a pass.",
                file=sys.stderr,
            )
            return EXIT_ERROR
        claims = collect_claims(repo, files, tuple(args.kind) if args.kind else None)
        if not claims:
            print(
                "verify_claims: no claims extracted — refusing to report a pass.",
                file=sys.stderr,
            )
            return EXIT_ERROR
        file_globs: list[str] = []
        exemptions: frozenset[tuple[str, str]] = frozenset()
        if not args.no_allow_file:
            file_globs = read_allow_file(repo)
            exemptions = read_flag_allow_file(repo)
        globs = [*args.allow, *file_globs]
        # Before the run, not after: a full sweep takes minutes, and the reader
        # should know what is being waived while it is happening. `--quiet` and
        # `--json` are consumed by scripts, so they stay clean.
        notice = exemption_notice(
            {
                ALLOW_FILE_NAME: file_globs,
                "--allow": args.allow,
                FLAG_ALLOW_FILE_NAME: [f"{c} {f}" for c, f in exemptions],
            }
        )
        if notice and not (args.quiet or args.json):
            print(notice, file=sys.stderr)
        results = run(
            repo,
            claims,
            online=args.online,
            allow_globs=tuple(dict.fromkeys(globs)),
            flag_exemptions=exemptions,
            workers=args.workers,
        )
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        print(f"verify_claims: the gate could not run: {error}", file=sys.stderr)
        return EXIT_ERROR

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False))
    elif args.quiet:
        counts = Counter(r.verdict for r in results)
        print(
            f"verify_claims: {counts[VERIFIED]} verified, {counts[REFUTED]} refuted, "
            f"{counts[UNVERIFIABLE]} unverifiable, over {len(results)} claims."
        )
    else:
        print(format_report(results, online=args.online))

    broken = transport_failure(results)
    if broken:
        print(f"verify_claims: {broken}", file=sys.stderr)
        print(
            "verify_claims: refusing to report a pass on an online tier that could "
            "not run.",
            file=sys.stderr,
        )
        if "CERTIFICATE" in broken.upper() or "SSL" in broken.upper():
            for line in tls_advice():
                print(f"  {line}", file=sys.stderr)
        print("Re-run without --online to use the offline tier only.", file=sys.stderr)
        return EXIT_ERROR

    failed = [r for r in results if r.verdict == REFUTED]
    if args.strict:
        failed += [r for r in results if r.verdict == UNVERIFIABLE]
    return EXIT_REFUTED if failed else EXIT_OK


if __name__ == "__main__":
    # Windows' default console codepage (cp1252) can't encode the → this
    # script's own report and some source docs use — reconfigure before the
    # first print rather than relying on PYTHONIOENCODING being set by whoever
    # invokes this (a git hook, in particular, won't have it).
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
