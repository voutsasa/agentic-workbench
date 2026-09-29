#!/usr/bin/env python3
"""Deterministic documentation gate for a markdown repo.

Five checks, all of them plain file operations — no model, no network, no cost:

  links           — every relative markdown link resolves to a file on disk
  bare_paths      — repo paths written as prose rather than as a link resolve too
  terminology     — house glossary, with per-rule carve-outs
  metadata_header — required frontmatter fields, per document family, with the
                    values validated rather than merely present
  register        — a source register and its catalogue stay entry-for-entry
                    identical, every entry is one bracket link to one
                    destination, and its relative links stay within
                    link_allow_globs when that is set. Skipped in a repo that has no register, so the
                    shared config stays safe to link from anywhere.

`--corpus` is the register's other half, deliberately NOT part of the gate: it
reports which destination files are actually on disk. The ingested corpus is
gitignored, so a fresh clone has none and nothing is wrong — failing a push on
that would punish the one checkout where the repo is clean. Run it by hand as
the preflight for an ingestion run.

Deliberately NOT here: "does this document contradict the code?". That needs a
command executed per claim, and the `verify-docs` skill already does it properly
(`scripts/verify-docs.sh` at the repo root drives it headlessly). It is minutes
of work and can fail on a judgement call, so it belongs on demand or in CI —
not in front of every push.

Exit codes:
  0  all enabled checks clean
  1  violations found
  2  the check could not run (bad config, no files, unreadable tree)

Exit 2 is deliberately distinct from 1: a gate that reports success because the
checker broke is worse than no gate. Both fail a push.

Stdlib only, matching fetch-to-markdown's scripts/clean_md_images.py.
"""

from __future__ import annotations

import argparse
import io
import json
import posixpath
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote

DEFAULT_CONFIG = Path(__file__).with_name("checks.toml")

EXIT_OK = 0
EXIT_VIOLATIONS = 1
EXIT_ERROR = 2

# [text](target) and ![alt](target). Angle-bracket targets — [x](<a b.md>) — are
# markdown's own escape for spaces, so the brackets are stripped after matching.
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(\s*(<[^>]*>|[^)\s]+(?:\s+\"[^\"]*\")?)\s*\)")
# [label]: target — a reference definition at the start of a line.
REF_DEFINITION = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(\S+)")
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")

# Targets that are illustrative rather than real: <tool>/, ..., {name}.md
PLACEHOLDER = re.compile(r"[<>{}]|\.\.\.")
NON_FILE_SCHEMES = ("http://", "https://", "mailto:", "tel:", "ftp://", "data:")

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Punctuation that ends a sentence rather than a path: `quick_start.md.` is a
# path followed by a full stop. `.md` survives — only these characters are cut.
TRAILING_PUNCTUATION = """`*_.,;:!?)"'"""


class CheckError(RuntimeError):
    """The check could not be completed — distinct from finding violations."""


# --------------------------------------------------------------------------- #
# config and scope
# --------------------------------------------------------------------------- #


def load_config(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CheckError(f"config not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise CheckError(f"config is not valid TOML: {path}: {exc}") from exc


def enabled_checks(config: dict) -> list[str]:
    return [
        name
        for name, body in config.get("checks", {}).items()
        if body.get("enabled", False)
    ]


def collect_files(repo_root: Path, config: dict, runner=subprocess.run) -> list[str]:
    """Tracked files matching scope.include_globs, minus scope.exclude_globs.

    Uses git rather than a filesystem walk so the ingested corpus — gitignored by
    design — never enters the check. -z because paths contain spaces; UTF-8
    because that is what git emits, whatever the locale codepage is.
    """
    proc = runner(
        ["git", "-C", str(repo_root), "ls-files", "-z"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode != 0:
        raise CheckError(f"git ls-files failed: {proc.stderr.strip()}")

    scope = config.get("scope", {})
    included = scope.get("include_globs", ["**/*.md"])
    excluded = scope.get("exclude_globs", [])
    files = [
        rel
        for rel in proc.stdout.split("\0")
        if rel.strip()
        and any(_matches(rel, pat) for pat in included)
        and not any(_matches(rel, pat) for pat in excluded)
    ]
    return sorted(files)


def _matches(rel_path: str, pattern: str) -> bool:
    """Glob match where ** spans directory separators."""
    regex = re.escape(pattern).replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*")
    regex = regex.replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
    return re.fullmatch(regex, rel_path) is not None


# --------------------------------------------------------------------------- #
# reading
# --------------------------------------------------------------------------- #


def prose_lines(text: str, *, keep_code: bool = False) -> list[tuple[int, str]]:
    """Lines outside fenced code blocks, with inline code spans blanked out.

    Code is not prose: a tree diagram full of `<tool>/` placeholders and a shell
    snippet naming a `--download` flag are not documentation defects.

    `keep_code=True` leaves inline code intact. Exactly one check wants that —
    bare_paths, because a repo path is nearly always written inside backticks,
    so blanking them would blind it to almost every case it exists to catch.
    """
    out: list[tuple[int, str]] = []
    fence_marker: str | None = None
    for lineno, line in enumerate(text.splitlines(), 1):
        fence = FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if fence_marker is None:
                fence_marker = marker
            elif line.strip().startswith(fence_marker):
                fence_marker = None
            continue
        if fence_marker is not None:
            continue
        out.append(
            (
                lineno,
                line
                if keep_code
                else INLINE_CODE.sub(lambda m: " " * len(m.group(0)), line),
            )
        )
    return out


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError(f"cannot read {path}: {exc}") from exc


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #


def _link_targets(line: str) -> list[str]:
    targets = [m.group(1) for m in INLINE_LINK.finditer(line)]
    ref = REF_DEFINITION.match(line)
    if ref:
        targets.append(ref.group(1))
    return targets


def resolve_target(target: str) -> str | None:
    """Normalise a link target to a repo path, or None if it is not ours to check.

    Returns None for external schemes, pure anchors, and placeholders. Percent
    escapes are decoded — `Non-functional%20requirements.md` is a real file.
    """
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]  # markdown's escape for spaces
    else:
        target = target.split(" ", 1)[0].strip()  # drop a trailing "title"
    if not target or target.startswith("#"):
        return None
    if target.lower().startswith(NON_FILE_SCHEMES):
        return None
    if PLACEHOLDER.search(target):
        return None
    path_part = target.split("#", 1)[0].split("?", 1)[0]
    if not path_part:
        return None
    return unquote(path_part)


def check_links(repo_root: Path, files: list[str], config: dict) -> list[dict]:
    """A link's target must resolve — except the ingested reference.md pages.

    Those are gitignored by design (see scope.exclude_globs) and absent on any
    machine that hasn't ingested that source yet, which AGENTS.md calls expected,
    not a fault. allow_globs here is the same escape valve check_bare_paths
    already has for the identical file, just reached through [text](target)
    instead of a bare path in prose.
    """
    allow_globs = config["checks"]["links"].get("allow_globs", [])
    violations = []
    for rel in files:
        path = repo_root / rel
        for lineno, line in prose_lines(read_text(path)):
            for raw in _link_targets(line):
                resolved = resolve_target(raw)
                if resolved is None:
                    continue
                base = repo_root if resolved.startswith("/") else path.parent
                candidate = base / resolved.lstrip("/")
                if candidate.exists():
                    continue
                candidate_rel = (
                    resolved.lstrip("/")
                    if resolved.startswith("/")
                    else posixpath.normpath(
                        posixpath.join(posixpath.dirname(rel), resolved)
                    )
                )
                if any(_matches(candidate_rel, glob) for glob in allow_globs):
                    continue
                violations.append(
                    {
                        "check": "links",
                        "file": rel,
                        "line": lineno,
                        "detail": f"link target does not exist: {resolved}",
                        "evidence": line.strip()[:200],
                    }
                )
    return violations


def strip_link_targets(line: str) -> str:
    """A line with markdown link targets removed, inline code left intact.

    Targets are dropped because check_links already resolves them, and reporting
    one broken path under two checks helps nobody. Link *text* is kept on
    purpose: a label naming a path that was renamed is a defect even when the
    target beside it still resolves.
    """
    if REF_DEFINITION.match(line):
        return ""
    return INLINE_LINK.sub(lambda m: m.group(0).split("](")[0] + "]", line)


def check_bare_paths(repo_root: Path, files: list[str], config: dict) -> list[dict]:
    """Repo-relative paths written as prose rather than as a markdown link.

    check_links only sees [text](target). A folder named in a sentence — or, far
    more often, in backticks — reaches no check at all, which is how a document
    ends up directing a reader to a directory that was renamed a month ago.

    Scoped by prefix rather than applied to every slash-bearing token: a path is
    only checkable when its root is known, and `docs/` or `src/` in someone
    else's quoted example is not this repo's to resolve.
    """
    settings = config["checks"]["bare_paths"]
    prefixes = [p for p in settings.get("prefixes", []) if p]
    if not prefixes:
        return []
    allow_globs = settings.get("allow_globs", [])
    # Stops at whitespace and at the delimiters that end a path in prose: a
    # closing backtick, bracket, brace, paren, quote or comma.
    # Built by concatenation rather than a format string: the tail carries a bare
    # `}` and quotes, which an f-string would need escaped and a .format() would
    # misread as a field.
    alternatives = "|".join(re.escape(p) for p in prefixes)
    pattern = re.compile(r"(?:" + alternatives + r""")[^\s`)\]}>,;"']*""")

    violations = []
    for rel in files:
        path = repo_root / rel
        for lineno, line in prose_lines(read_text(path), keep_code=True):
            for match in pattern.finditer(strip_link_targets(line)):
                # Through resolve_target for the same reason check_links uses it:
                # an anchor, a query string or a percent escape is not part of the
                # path. Skipping it here made `quick_start.md#traps` a violation
                # against a file that exists — and defeated allow_globs, since the
                # suffix no longer matched the glob.
                candidate = resolve_target(match.group(0).rstrip(TRAILING_PUNCTUATION))
                if candidate is None:
                    continue
                if any(_matches(candidate, glob) for glob in allow_globs):
                    continue
                if (repo_root / candidate).exists():
                    continue
                violations.append(
                    {
                        "check": "bare_paths",
                        "file": rel,
                        "line": lineno,
                        "detail": f"path does not exist: {candidate}",
                        "evidence": line.strip()[:200],
                    }
                )
    return violations


def check_terminology(repo_root: Path, files: list[str], config: dict) -> list[dict]:
    rules = [
        r
        for r in config["checks"]["terminology"].get("rules", [])
        if r.get("enabled", True)
    ]
    if not rules:
        return []

    compiled = [
        (
            rule,
            re.compile(rf"\b{re.escape(rule['wrong'])}\w*\b", re.IGNORECASE),
            [a.lower() for a in rule.get("allow_context", [])],
        )
        for rule in rules
    ]
    violations = []
    for rel in files:
        # A rule's allow_paths exempts whole files; the rest of the rules still apply.
        applicable = [
            entry
            for entry in compiled
            if not any(_matches(rel, glob) for glob in entry[0].get("allow_paths", []))
        ]
        if not applicable:
            continue
        path = repo_root / rel
        for lineno, line in prose_lines(read_text(path)):
            # A link target is a path or URL, not prose, so it is stripped before
            # matching — but the carve-outs are tested against the ORIGINAL line,
            # because a target is often the very context that exonerates a word
            # (a [Download] link to imagemagick.org names their page, not ours).
            prose = INLINE_LINK.sub(lambda m: m.group(0).split("](")[0] + "]", line)
            lowered = line.lower()
            for rule, pattern, allowed in applicable:
                match = pattern.search(prose)
                if not match:
                    continue
                if any(phrase in lowered for phrase in allowed):
                    continue
                violations.append(
                    {
                        "check": "terminology",
                        "file": rel,
                        "line": lineno,
                        "detail": f'use "{rule["right"]}" rather than "{match.group(0)}"'
                        f" — {rule.get('why', 'house glossary')}",
                        "evidence": prose.strip()[:200],
                    }
                )
    return violations


def parse_frontmatter(text: str) -> tuple[dict[str, str] | None, str | None]:
    """Return (fields, error). fields is None when there is no usable header.

    A deliberately small YAML subset: `key: value` pairs, one per line, quotes
    stripped. Nothing here needs nesting, and a real YAML parser is a dependency
    this repo does not have.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        opener = lines[0][:40] if lines else "(empty file)"
        return None, f"no YAML frontmatter — file opens with {opener!r}"
    try:
        close = next(i for i, l in enumerate(lines[1:], 1) if l.strip() == "---")
    except StopIteration:
        return None, "frontmatter is opened but never closed"

    fields = {}
    for line in lines[1:close]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip("'\"")
    return fields, None


def schema_for(rel: str, schemas: list[dict]) -> dict | None:
    """First schema whose paths match. Order in checks.toml is precedence."""
    for schema in schemas:
        if any(_matches(rel, pattern) for pattern in schema.get("paths", [])):
            return schema
    return None


def validate_fields(rel: str, fields: dict[str, str], schema: dict) -> list[str]:
    """Every problem with this file's header, as human-readable phrases."""
    problems = []
    for spec in schema.get("fields", []):
        name = spec["name"]
        value = fields.get(name)

        if value is None:
            problems.append(f"missing `{name}`")
            continue
        if not value:
            problems.append(f"`{name}` is empty")
            continue

        allowed = spec.get("allowed_values")
        if allowed and value not in allowed:
            problems.append(
                f"`{name}` is {value!r}, expected one of {', '.join(allowed)}"
            )

        # A sentinel is an honest answer where a date would be a lie: `never`
        # says nobody has checked these claims yet, which is a fact worth
        # recording rather than papering over with today's date.
        if value in spec.get("sentinels", []):
            continue
        if spec.get("format") == "date" and not ISO_DATE.match(value):
            problems.append(f"`{name}` is {value!r}, expected an ISO date (YYYY-MM-DD)")
        if spec.get("equals_directory"):
            expected = Path(rel).parent.name
            if value != expected:
                problems.append(
                    f"`{name}` is {value!r} but its directory is {expected!r}"
                )
    return problems


def check_metadata_header(
    repo_root: Path, files: list[str], config: dict
) -> list[dict]:
    """Validate frontmatter against the schema for each document family.

    A file matching no schema is not checked. That is the exemption mechanism:
    families opt in by being named, rather than opting out one path at a time.
    """
    schemas = config["checks"]["metadata_header"].get("schemas", [])
    if not schemas:
        raise CheckError("metadata_header is enabled but no schemas are defined")

    violations = []
    for rel in files:
        schema = schema_for(rel, schemas)
        if schema is None:
            continue

        fields, error = parse_frontmatter(read_text(repo_root / rel))
        if error or fields is None:
            violations.append(
                {
                    "check": "metadata_header",
                    "file": rel,
                    "line": 1,
                    "detail": error,
                    "evidence": f"schema: {schema.get('name', '?')}",
                }
            )
            continue

        problems = validate_fields(rel, fields, schema)
        if problems:
            violations.append(
                {
                    "check": "metadata_header",
                    "file": rel,
                    "line": 1,
                    "detail": "; ".join(problems),
                    "evidence": f"schema: {schema.get('name', '?')}; "
                    f"present: {', '.join(sorted(fields)) or '(none)'}",
                }
            )
    return violations


# --------------------------------------------------------------------------- #
# register
# --------------------------------------------------------------------------- #

# A register entry is a bullet carrying a bracket link with an http(s) target.
# That is the definition, not a heuristic: a gap placeholder carries no link and
# an italic *see also* cross-reference carries no link either, so neither can be
# mistaken for an entry, and the invariant stays one bracket link to one file.
REGISTER_BULLET = re.compile(r"^\s*[*+-]\s+\S")
REGISTER_LINK = re.compile(r"\[([^\]]+)\]\(\s*(https?://[^)\s]+?)\s*\)")
SEE_ALSO = re.compile(r"^\s*[*_]see also:", re.IGNORECASE)
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")

# The depth at which a heading names a destination subsection rather than a
# layer. `#### CLI tools` routes; `## 4. Technical architecture` does not.
SUBSECTION_DEPTH = 4


def register_filename(name: str) -> str:
    """An entry's title as it is written on disk.

    One transform, from the ingestion invariant: `: ` — the colon *and* the
    space after it — becomes ` - `, because a colon is not a legal filename
    character on Windows. A colon with no space after it is part of the title
    (`C:Drive`) and is left alone.
    """
    return name.replace(": ", " - ")


def parse_register_entries(text: str) -> list[dict]:
    """Every entry in a register or catalogue, in document order.

    Fenced code is skipped — an example bullet in a snippet is not an entry.
    `section` is the innermost subsection heading, or None under a layer.
    """
    entries: list[dict] = []
    section: str | None = None
    for lineno, line in prose_lines(text, keep_code=True):
        heading = HEADING.match(line)
        if heading:
            depth = len(heading.group(1))
            section = heading.group(2) if depth >= SUBSECTION_DEPTH else None
            continue
        if not REGISTER_BULLET.match(line):
            continue
        links = REGISTER_LINK.findall(line)
        if not links:
            continue
        name, url = links[0]
        entries.append(
            {
                "name": name.strip(),
                "url": url,
                "section": section,
                "line": lineno,
                "links": len(links),
            }
        )
    return entries


def register_destinations(entry: dict, settings: dict) -> list[str]:
    """Where this entry's ingested file is allowed to be, most likely first.

    One route per subsection rule, else the default with each extension tried —
    a layer source lands as `.md` or `.pdf` depending on what the source is.
    """
    name = register_filename(entry["name"])
    for rule in settings.get("destinations", []):
        if rule.get("section") == entry.get("section"):
            return [rule["path"].format(name=name)]
    template = settings.get("default_destination", "docs/landing-zone/{name}")
    base = template.format(name=name)
    return [base + ext for ext in settings.get("extensions", [".md"])]


def _register_shape(rel: str, entries: list[dict], text: str) -> list[dict]:
    """The one-to-one rules, inside the register itself."""
    violations = []
    seen: dict[str, int] = {}
    for entry in entries:
        if entry["links"] > 1:
            violations.append(
                {
                    "check": "register",
                    "file": rel,
                    "line": entry["line"],
                    "detail": f"entry carries {entry['links']} bracket links; an "
                    "entry is one bracket link to one ingested file",
                    "evidence": entry["name"],
                }
            )
        if "/" in entry["name"] or "\\" in entry["name"]:
            violations.append(
                {
                    "check": "register",
                    "file": rel,
                    "line": entry["line"],
                    "detail": f"entry name {entry['name']!r} holds a path separator, "
                    "so its destination would fall outside the destination folder",
                    "evidence": entry["name"],
                }
            )
        first = seen.get(entry["name"])
        if first is not None:
            violations.append(
                {
                    "check": "register",
                    "file": rel,
                    "line": entry["line"],
                    "detail": f"{entry['name']!r} appears more than once (first at "
                    f"line {first}); one canonical entry per source",
                    "evidence": entry["name"],
                }
            )
        else:
            seen[entry["name"]] = entry["line"]

    # A cross-reference with a link would be a second canonical entry for a
    # source that already has one, which is exactly what the italic form avoids.
    for lineno, line in prose_lines(text, keep_code=True):
        if SEE_ALSO.match(line) and REGISTER_LINK.search(line):
            violations.append(
                {
                    "check": "register",
                    "file": rel,
                    "line": lineno,
                    "detail": "a *see also* cross-reference carries a bracket link, "
                    "which makes it a second entry for a source that already has one",
                    "evidence": line.strip()[:200],
                }
            )
    return violations


def _register_link_targets(rel: str, text: str, allow_globs: list[str]) -> list[dict]:
    """Relative links out of the register reach only its process documents.

    External targets, anchors and placeholders are not ours to restrict, which
    `resolve_target` already decides for the links check.
    """
    violations = []
    for lineno, line in prose_lines(text):
        for raw in _link_targets(line):
            resolved = resolve_target(raw)
            if resolved is None:
                continue
            target = posixpath.normpath(
                resolved.lstrip("/")
                if resolved.startswith("/")
                else posixpath.join(posixpath.dirname(rel), resolved)
            )
            if any(_matches(target, glob) for glob in allow_globs):
                continue
            violations.append(
                {
                    "check": "register",
                    "file": rel,
                    "line": lineno,
                    "detail": f"the register links {target}, which is not one of "
                    "the process documents it may reference (link_allow_globs)",
                    "evidence": line.strip()[:200],
                }
            )
    return violations


def _register_mirror(
    catalogue_rel: str, entries: list[dict], catalogue: list[dict]
) -> list[dict]:
    """The catalogue mirrors the register entry-for-entry, order included."""
    violations = []
    source_names = [e["name"] for e in entries]
    catalogue_names = [e["name"] for e in catalogue]

    for name in source_names:
        if name not in catalogue_names:
            violations.append(
                {
                    "check": "register",
                    "file": catalogue_rel,
                    "line": 1,
                    "detail": f"{name!r} is in the register but has no catalogue line",
                    "evidence": "the two stay entry-for-entry identical",
                }
            )
    for entry in catalogue:
        if entry["name"] not in source_names:
            violations.append(
                {
                    "check": "register",
                    "file": catalogue_rel,
                    "line": entry["line"],
                    "detail": f"{entry['name']!r} is in the catalogue but not in the "
                    "register, which is the source of truth",
                    "evidence": entry["name"],
                }
            )

    by_name = {e["name"]: e for e in entries}
    for entry in catalogue:
        twin = by_name.get(entry["name"])
        if twin and twin["url"] != entry["url"]:
            violations.append(
                {
                    "check": "register",
                    "file": catalogue_rel,
                    "line": entry["line"],
                    "detail": f"URL for {entry['name']!r} differs from the register: "
                    f"{entry['url']} vs {twin['url']}",
                    "evidence": entry["url"],
                }
            )

    # Order is only meaningful once both hold the same entries; reporting it
    # alongside a missing line would be one fault counted twice.
    if (
        sorted(source_names) == sorted(catalogue_names)
        and source_names != catalogue_names
    ):
        first = next(
            i for i, (a, b) in enumerate(zip(source_names, catalogue_names)) if a != b
        )
        violations.append(
            {
                "check": "register",
                "file": catalogue_rel,
                "line": catalogue[first]["line"],
                "detail": "catalogue order diverges from the register at entry "
                f"{first + 1}: {catalogue_names[first]!r} where the register has "
                f"{source_names[first]!r}",
                "evidence": "one line per entry, in the same order as the register",
            }
        )
    return violations


def check_register(repo_root: Path, files: list[str], config: dict) -> list[dict]:
    """A source register's internal rules, and its catalogue's fidelity to it.

    `files` is unused: this check reads two named documents rather than sweeping
    the tree. A repo with no register at the configured path is not checked at
    all — checks.toml lives in the globally linked skills tree, so one copy of it
    serves every repo that links the hook, and a rule naming SOURCES.md must not
    fire in a repo that has never had one.

    Destination files are NOT checked here. See `corpus_ledger` and --corpus.
    """
    settings = config["checks"]["register"]
    sources_rel = settings.get("sources", "SOURCES.md")
    sources_path = repo_root / sources_rel
    if not sources_path.exists():
        return []

    text = read_text(sources_path)
    entries = parse_register_entries(text)
    violations = _register_shape(sources_rel, entries, text)
    if "link_allow_globs" in settings:
        violations.extend(
            _register_link_targets(sources_rel, text, settings["link_allow_globs"])
        )

    catalogue_rel = settings.get("catalogue")
    if not catalogue_rel:
        return violations
    catalogue_path = repo_root / catalogue_rel
    if not catalogue_path.exists():
        violations.append(
            {
                "check": "register",
                "file": sources_rel,
                "line": 1,
                "detail": f"the register's catalogue is missing: {catalogue_rel}",
                "evidence": f"{len(entries)} entries have nowhere to be summarised",
            }
        )
        return violations

    violations.extend(
        _register_mirror(
            catalogue_rel, entries, parse_register_entries(read_text(catalogue_path))
        )
    )
    return violations


def corpus_ledger(repo_root: Path, config: dict) -> list[dict]:
    """One row per register entry: where its ingested file should be, and if it is.

    This is the ingestion invariant measured rather than asserted — the preflight
    and the progress ledger for an ingestion run, in register order.
    """
    settings = config.get("checks", {}).get("register", {})
    sources_path = repo_root / settings.get("sources", "SOURCES.md")
    if not sources_path.exists():
        return []

    rows = []
    for entry in parse_register_entries(read_text(sources_path)):
        candidates = register_destinations(entry, settings)
        found = next((c for c in candidates if (repo_root / c).exists()), None)
        rows.append(
            {
                "name": entry["name"],
                "section": entry["section"],
                "line": entry["line"],
                "candidates": candidates,
                "found": found,
                "present": found is not None,
            }
        )
    return rows


CHECKS = {
    "links": check_links,
    "bare_paths": check_bare_paths,
    "terminology": check_terminology,
    "metadata_header": check_metadata_header,
    "register": check_register,
}


def run_checks(repo_root: Path, files: list[str], config: dict) -> list[dict]:
    violations: list[dict] = []
    for name in sorted(enabled_checks(config)):
        runner = CHECKS.get(name)
        if runner is None:
            raise CheckError(
                f"checks.toml enables '{name}', which this script does not implement. "
                "Claim-verification lives in the verify-docs skill, not here."
            )
        violations.extend(runner(repo_root, files, config))
    return violations


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #


def format_report(violations: list[dict]) -> str:
    if not violations:
        return "repo_check: all enabled checks passed."

    by_check: dict[str, list[dict]] = {}
    for v in violations:
        by_check.setdefault(v.get("check", "unknown"), []).append(v)

    lines = [f"repo_check: {len(violations)} violation(s)", ""]
    for check, items in sorted(by_check.items()):
        lines.append(f"[{check}] {len(items)}")
        for v in items:
            loc = f"{v['file']}:{v['line']}" if v.get("line") else v.get("file", "?")
            lines.append(f"  {loc} — {v.get('detail', '(no detail)')}")
            if v.get("evidence"):
                lines.append(f"      {v['evidence']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_ledger(rows: list[dict]) -> str:
    present = [r for r in rows if r["present"]]
    missing = [r for r in rows if not r["present"]]
    lines = [f"corpus: {len(present)} of {len(rows)} entries ingested"]
    if missing:
        lines += ["", f"missing ({len(missing)}) — SOURCES.md line, then destination:"]
        lines += [
            f"  {r['line']:>4}  {r['name']} -> {r['candidates'][0]}" for r in missing
        ]
        lines += [
            "",
            "Absent is not broken: the corpus is gitignored and rebuilt from",
            "SOURCES.md on request. Run these through the ingest-source skill.",
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="repo to check (default: the git root above this script)",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--json", action="store_true", help="emit raw violation JSON")
    parser.add_argument(
        "--list-files", action="store_true", help="print the files in scope and stop"
    )
    parser.add_argument(
        "--corpus",
        action="store_true",
        help="report which register entries have an ingested file, and stop "
        "(not part of the gate — the corpus is gitignored)",
    )
    args = parser.parse_args(argv)

    try:
        repo_root = args.repo_root or _git_root(Path(__file__).resolve().parent)
        config = load_config(args.config)

        if args.corpus:
            rows = corpus_ledger(repo_root, config)
            if not rows:
                raise CheckError(
                    "no source register found — checks.register.sources names "
                    f"{config.get('checks', {}).get('register', {}).get('sources', 'SOURCES.md')!r}, "
                    "which does not exist here"
                )
            if args.json:
                print(json.dumps({"corpus": rows}, indent=2))
            else:
                print(format_ledger(rows))
            return EXIT_VIOLATIONS if any(not r["present"] for r in rows) else EXIT_OK

        active = enabled_checks(config)
        if not active:
            print(
                "repo_check: no checks enabled in checks.toml — nothing to do.",
                file=sys.stderr,
            )
            return EXIT_OK

        files = collect_files(repo_root, config)
        if not files:
            raise CheckError("no tracked markdown matched the configured scope")

        if args.list_files:
            print("\n".join(files))
            return EXIT_OK

        violations = run_checks(repo_root, files, config)
    except CheckError as exc:
        print(f"repo_check: ERROR — {exc}", file=sys.stderr)
        print(
            "repo_check: the check did not run; not treating that as a pass.",
            file=sys.stderr,
        )
        return EXIT_ERROR

    if args.json:
        print(json.dumps({"violations": violations}, indent=2))
    else:
        print(format_report(violations))
    return EXIT_VIOLATIONS if violations else EXIT_OK


def _git_root(start: Path) -> Path:
    proc = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise CheckError(f"not inside a git repo: {start}")
    return Path(proc.stdout.strip())


if __name__ == "__main__":
    # A git hook inherits the console codepage (cp1252 on Windows), which cannot
    # encode every tracked path or the report's own dashes. Same fix as
    # verify_claims.py: reconfigure before the first print.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
