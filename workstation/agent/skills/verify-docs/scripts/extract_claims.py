#!/usr/bin/env python3
"""Extract verifiable claims from a repo's markdown docs into a JSONL manifest.

Phase 1 of the verify-docs skill. This step is deliberately *deterministic*: it
finds candidate claims and proposes a verification command for each, but it never
decides whether a claim is true. Verification happens in phase 3, by running the
proposed commands and recording their real output.

Usage:
    python extract_claims.py --repo /path/to/repo --out claims.jsonl
    python extract_claims.py --repo . --files README.md --summary

Corpus defaults to `git ls-files '*.md'`, which excludes untracked and ignored
material (e.g. ingested third-party pages). `docs/landing-zone/` is dropped as well
because it holds external source documents, not claims about this repo.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

# --- claim kinds ---------------------------------------------------------------

INSTALL = "install"
CLI_FLAG = "cli_flag"
CLI_INVOCATION = "cli_invocation"
PATH = "path"
VERSION = "version"
URL = "url"
GIT = "git"

DEFAULT_EXCLUDES = ("docs/landing-zone/",)

FENCE_RE = re.compile(r"^\s*(?:```|~~~)\s*([\w+-]*)")
# Only these fences hold shell. A python/json/text block is not a command list.
SHELL_FENCES = {"", "bash", "sh", "shell", "zsh", "console", "shell-session", "terminal"}
# A binary name, not a word of prose and not a Python identifier expression.
BINARY_RE = re.compile(r"^[a-z][a-z0-9_.+-]*$")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
URL_RE = re.compile(r"https?://[^\s`\)\]<>\"']+")
URL_TRAILING_PUNCT = ".,;:!?"
FLAG_RE = re.compile(r"(?<![\w-])(--[a-zA-Z][\w-]*)")
SHORT_FLAG_RE = re.compile(r"^-([a-zA-Z])$")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
VERSION_RE = re.compile(r"(?<![\w.])v?\d+\.\d+(?:\.\d+)?(?![\w.])")
PROMPT_RE = re.compile(r"^\s*[$>]\s+")

# Package managers we know how to look up in a live registry.
INSTALL_RE = re.compile(
    r"^(?P<mgr>brew install|npm install|npm i|pnpm add|yarn add|pipx install"
    r"|uv tool install|uv add|pip install|pip3 install|cargo install|go install)"
    r"\s+(?P<args>.+)$"
)

# `command -v <pkg>` is wrong for most packages: the brew formula `imagemagick`
# ships `magick`, and `@mermaid-js/mermaid-cli` ships `mmdc`. Ask the manager.
INSTALLED_LOOKUP = {
    "brew install": "brew list --versions {pkg}",
    "npm install": "npm ls -g --depth=0 {pkg}",
    "npm i": "npm ls -g --depth=0 {pkg}",
    "pnpm add": "npm ls -g --depth=0 {pkg}",
    "yarn add": "npm ls -g --depth=0 {pkg}",
    "pipx install": "pipx list --short",
    "uv tool install": "uv tool list",
    "uv add": "pip show {pkg}",
    "pip install": "pip show {pkg}",
    "pip3 install": "pip show {pkg}",
    "cargo install": "cargo install --list",
    "go install": "go version -m $(command -v {pkg})",
}

REGISTRY_LOOKUP = {
    "brew install": "brew info --json=v2 {pkg}",
    "npm install": "npm view {pkg} version",
    "npm i": "npm view {pkg} version",
    "pnpm add": "npm view {pkg} version",
    "yarn add": "npm view {pkg} version",
    "pipx install": "pip index versions {pkg}",
    "uv tool install": "pip index versions {pkg}",
    "uv add": "pip index versions {pkg}",
    "pip install": "pip index versions {pkg}",
    "pip3 install": "pip index versions {pkg}",
    "cargo install": "cargo search --limit 1 {pkg}",
    "go install": "go list -m {pkg}",
}

# Words that make a prose line a claim about repository/git state.
GIT_KEYWORDS = re.compile(
    r"(merged into \w+|already merged|not (?:yet )?merged|unmerged"
    r"|tracked in git|untracked in git|on the (?:main|master) branch"
    r"|latest commit|most recent commit|git tag)",
    re.IGNORECASE,
)

PATH_RE = re.compile(r"^(?:~/|\.{1,2}/|/|[\w.-]+/)[\w./~@-]*$")
PATH_ANCHOR_RE = re.compile(r"^(?:~/|\.{1,2}/|/)")
PATH_EXT_RE = re.compile(r"\.[A-Za-z0-9]{1,5}$")

SHELL_NOISE = {"cd", "echo", "export", "cat", "sudo", "then", "fi", "do", "done", "#"}


@dataclass
class Claim:
    id: str
    file: str
    line: int
    kind: str
    claim: str
    verification_method: str
    verification_command: str
    status: str = "PENDING"


# --- corpus --------------------------------------------------------------------


def tracked_markdown(repo: Path, excludes: tuple[str, ...] = DEFAULT_EXCLUDES) -> list[str]:
    """Return repo-relative markdown paths tracked by git, minus excluded prefixes."""
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "*.md"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    files = [line for line in out.splitlines() if line]
    return [f for f in files if not any(f.startswith(prefix) for prefix in excludes)]


# --- extraction ----------------------------------------------------------------


def strip_prompt(line: str) -> str:
    return PROMPT_RE.sub("", line).strip()


def looks_like_path(token: str) -> bool:
    if not PATH_RE.match(token):
        return False
    if token.startswith(("http", "//")):
        return False
    if "/" not in token:
        return False
    if not re.search(r"[A-Za-z0-9]", token.replace("/", "")):
        return False   # `...`, `../..`, and friends are not paths to test
    # `and/or` is prose. Accept only an anchored path, a filename with an
    # extension, or a multi-segment path. A bare two-segment `docs/guidance`
    # is deliberately missed rather than risk flooding the manifest.
    return bool(
        PATH_ANCHOR_RE.match(token) or PATH_EXT_RE.search(token) or token.count("/") >= 2
    )


def install_claim(command: str) -> tuple[str, str, str] | None:
    """Map an install command to (package, registry lookup, installed check)."""
    match = INSTALL_RE.match(command)
    if not match:
        return None
    mgr = match.group("mgr")
    args = [a for a in match.group("args").split() if not a.startswith("-")]
    if not args:
        return None
    pkg = args[0]
    return (
        pkg,
        REGISTRY_LOOKUP[mgr].format(pkg=pkg),
        INSTALLED_LOOKUP[mgr].format(pkg=pkg),
    )


def looks_like_command(line: str, head: str) -> bool:
    """Is this fenced line a shell invocation, or prose/Python/a directory tree?"""
    if not BINARY_RE.match(head):
        return False
    if line.rstrip().endswith(":"):        # `with sync_playwright() as p:`
        return False
    if "=" in line.split(" ")[0] or " = " in line:   # `page = browser.new_page()`
        return False
    # Two spaces mid-line means a column-aligned tree or table, not a command.
    return "  " not in line.strip()


def subject_binary(text: str, path: str) -> str | None:
    """Infer the binary a document is about.

    Preference order: the most frequent command head inside fenced blocks (which
    is correct even when the folder name and the binary differ, e.g. mermaid-cli
    ships `mmdc`), then the containing `workstation/cli/<tool>` folder name.
    """
    heads: Counter[str] = Counter()
    fence_lang: str | None = None
    for raw in text.splitlines():
        fence = FENCE_RE.match(raw)
        if fence:
            fence_lang = None if fence_lang is not None else fence.group(1).lower()
            continue
        if fence_lang is None or fence_lang not in SHELL_FENCES:
            continue
        command = strip_prompt(raw)
        if not command or command.startswith("#"):
            continue
        head = command.split()[0]
        if head in SHELL_NOISE or not looks_like_command(command, head):
            continue
        heads[head] += 1
    if heads:
        return heads.most_common(1)[0][0]
    parts = Path(path).parts
    if "cli" in parts:
        index = parts.index("cli")
        if index + 1 < len(parts):
            return parts[index + 1].removesuffix("-cli")
    return None


def flag_claim(subject: str | None, flag: str) -> tuple[str, str] | None:
    """Build a (claim, command) pair for a flag, or None when no binary is known."""
    if not subject:
        return None
    return (
        f"{subject} supports {flag}",
        f"{subject} --help 2>&1 | grep -F -- '{flag}'",
    )


def extract_from_text(path: str, text: str, start_id: int = 1) -> list[Claim]:
    """Extract candidate claims from one markdown document."""
    claims: list[Claim] = []
    counter = start_id
    fence_lang: str | None = None
    seen: set[tuple[str, str]] = set()
    subject = subject_binary(text, path)
    doc_dir = Path(path).parent

    def add(line_no: int, kind: str, claim: str, method: str, command: str) -> None:
        nonlocal counter
        key = (kind, command)
        if key in seen:
            return
        seen.add(key)
        claims.append(
            Claim(
                id=f"C{counter:04d}",
                file=path,
                line=line_no,
                kind=kind,
                claim=claim.strip(),
                verification_method=method,
                verification_command=command,
            )
        )
        counter += 1

    for line_no, raw in enumerate(text.splitlines(), start=1):
        fence = FENCE_RE.match(raw)
        if fence:
            fence_lang = None if fence_lang is not None else fence.group(1).lower()
            continue

        for match in URL_RE.finditer(raw):
            url = match.group(0).rstrip(URL_TRAILING_PUNCT)
            # `https://registry.npmjs.org/<pkg>` is a fetch template, not an
            # address. Fetching it 404s forever and refutes nothing.
            if raw[match.end() : match.end() + 1] == "<":
                continue
            add(
                line_no,
                URL,
                url,
                "http_head",
                f"curl -sS -o /dev/null -w '%{{http_code}}' -I -L '{url}'",
            )

        if fence_lang is not None:
            if fence_lang not in SHELL_FENCES:
                continue
            command = strip_prompt(raw)
            if not command or command.startswith("#"):
                continue
            tokens = command.split()
            head = tokens[0]

            installed = install_claim(command)
            if installed:
                pkg, lookup, present = installed
                add(line_no, INSTALL, command, "registry_lookup", lookup)
                add(line_no, INSTALL, f"{pkg} is installed here", "installed_check", present)
                continue

            if head in SHELL_NOISE or not looks_like_command(command, head):
                continue

            add(line_no, CLI_INVOCATION, command, "binary_present", f"command -v {head}")
            for flag in dict.fromkeys(FLAG_RE.findall(command)):
                built = flag_claim(head, flag)
                if built:
                    add(line_no, CLI_FLAG, built[0], "help_text", built[1])
            for token in tokens[1:]:
                token = token.strip("'\"`,;")
                if looks_like_path(token) and not token.startswith("-"):
                    add(line_no, PATH, token, "filesystem", f"test -e {token}")
            continue

        # Prose lines.
        if GIT_KEYWORDS.search(raw):
            add(line_no, GIT, raw.strip(), "git_state", "git log --oneline -5 && git branch --merged")

        for target in MD_LINK_RE.findall(raw):
            target = target.split("#", 1)[0]
            if not target or target.startswith(("http", "mailto:", "//")):
                continue
            resolved = target if target.startswith("/") else os.path.normpath(doc_dir / target)
            add(line_no, PATH, target, "filesystem", f"test -e {resolved}")

        for snippet in INLINE_CODE_RE.findall(raw):
            snippet = snippet.strip()
            if not snippet:
                continue
            if looks_like_path(snippet):
                add(line_no, PATH, snippet, "filesystem", f"test -e {snippet}")
                continue
            installed = install_claim(snippet)
            if installed:
                add(line_no, INSTALL, snippet, "registry_lookup", installed[1])
                continue
            head = snippet.split()[0]
            flags = list(dict.fromkeys(FLAG_RE.findall(snippet)))
            short = SHORT_FLAG_RE.match(head)
            if short:
                flags = [head]
            # A snippet that starts with a flag has no binary of its own; it
            # belongs to whatever tool the document is about.
            binary = subject if head.startswith("-") else head
            if flags and head not in SHELL_NOISE:
                for flag in flags:
                    built = flag_claim(binary, flag)
                    if built:
                        add(line_no, CLI_FLAG, built[0], "help_text", built[1])
            elif VERSION_RE.search(snippet) and len(snippet.split()) <= 3:
                binary = head if BINARY_RE.match(head) else subject
                if binary:
                    add(
                        line_no,
                        VERSION,
                        f"`{binary} --version` reports {snippet}",
                        "binary_version",
                        f"{binary} --version",
                    )

    return claims


def extract_repo(repo: Path, files: list[str]) -> list[Claim]:
    claims: list[Claim] = []
    for rel in files:
        target = repo / rel
        if not target.is_file():
            continue
        text = target.read_text(encoding="utf-8", errors="replace")
        claims.extend(extract_from_text(rel, text, start_id=len(claims) + 1))
    # Renumber so ids are globally unique and stable in file order.
    for index, claim in enumerate(claims, start=1):
        claim.id = f"C{index:04d}"
    return claims


# --- output --------------------------------------------------------------------


def summarise(claims: list[Claim]) -> str:
    by_kind = Counter(c.kind for c in claims)
    by_file = Counter(c.file for c in claims)
    lines = ["| kind | claims |", "| --- | ---: |"]
    lines += [f"| {kind} | {count} |" for kind, count in sorted(by_kind.items())]
    lines += ["", "| file | claims |", "| --- | ---: |"]
    lines += [f"| {file} | {count} |" for file, count in by_file.most_common()]
    lines += ["", f"**Total: {len(claims)} claims across {len(by_file)} files.**"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", type=Path, help="repository root")
    parser.add_argument("--files", nargs="*", help="repo-relative files (default: tracked *.md)")
    parser.add_argument("--out", type=Path, help="write JSONL manifest here (default: stdout)")
    parser.add_argument("--summary", action="store_true", help="print a markdown summary to stderr")
    parser.add_argument(
        "--include-sources",
        action="store_true",
        help="include docs/landing-zone/, normally excluded as external material",
    )
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    excludes = () if args.include_sources else DEFAULT_EXCLUDES
    files = args.files or tracked_markdown(repo, excludes)
    claims = extract_repo(repo, files)

    payload = "\n".join(json.dumps(asdict(c), ensure_ascii=False) for c in claims)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    if args.summary:
        print(summarise(claims), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
