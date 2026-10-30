#!/usr/bin/env python3
"""Deterministic steps of the build-html-presentation skill: Reveal.js versions and deck folders.

Every deck lives in ``<root>/docs/html-presentations/<name>/`` and loads Reveal.js from the copy
stored beside them in ``docs/html-presentations/vendor/reveal.js/<version>/``, so a deck opens
offline and its Reveal.js version only changes when someone decides it should.

Subcommands (``--root`` defaults to the current directory):

    status                       JSON: folder present, stored versions, latest on npm, decks
    fetch <version>              store one Reveal.js release from cdnjs (licence from GitHub)
    new <name> [--title T]       create the folder if needed and scaffold a deck from the template
    use <name> <version>         point a deck at another stored version
    build-artifact <name> <out>  copy for a claude.ai Artifact: no document skeleton, local
                                 reveal.css, scripts from cdnjs

Stdlib-only, so it runs as ``python3`` (macOS) or ``python`` (Windows) before any venv exists.
Exit codes: 0 done, 1 refused or failed (reason on stderr), 2 usage.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

DECKS_DIR = Path("docs") / "html-presentations"
VENDOR_DIR = DECKS_DIR / "vendor" / "reveal.js"
TEMPLATES = Path(__file__).resolve().parents[1] / "templates"

NPM_DIST_TAGS = "https://registry.npmjs.org/-/package/reveal.js/dist-tags"
CDN = "https://cdnjs.cloudflare.com/ajax/libs/reveal.js/{version}/"
LICENSE_URL = "https://raw.githubusercontent.com/hakimel/reveal.js/{version}/LICENSE"

PLUGINS = ("highlight", "notes", "zoom", "search")
#: The files a deck loads, as stored locally: core plus the plugins the template initialises.
#: Stored in Reveal.js 6's flat layout whatever the version, so a deck's paths stay the same.
VENDOR_FILES = (
    "reveal.min.css",
    "reveal.min.js",
    *(f"plugin/{name}.min.js" for name in PLUGINS),
)


def remote_path(version: str, name: str) -> str:
    """Where a stored file lives on cdnjs: 5.x and older nest each plugin in its own folder."""
    if name.startswith("plugin/") and version_key(version)[0] < 6:
        plugin = name.removeprefix("plugin/").removesuffix(".min.js")
        return f"plugin/{plugin}/{plugin}.min.js"
    return name


NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
DECK_VERSION = re.compile(r"\.\./vendor/reveal\.js/(\d+\.\d+\.\d+)/reveal\.min\.css")
#: Whole lines the Artifact host supplies itself, so the published page must not repeat them.
SKELETON = re.compile(
    r"^\s*(?:<!doctype html>|<html\b[^>]*>|</html>|<head>|</head>|<body>|</body>"
    r"|<meta charset=[^>]*>|<meta name=\"viewport\"[^>]*>)\s*$",
    re.IGNORECASE,
)

Opener = Callable[[str], bytes]


class Refused(Exception):
    """A request the script will not carry out; the message says why and what to do."""


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.read()


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def parse_dist_tags(payload: bytes) -> str:
    latest = json.loads(payload).get("latest", "")
    if not VERSION.match(latest):
        raise ValueError(f"npm dist-tags gave no usable 'latest': {latest!r}")
    return latest


def latest_version(opener: Opener = _download) -> str | None:
    """The newest Reveal.js release on npm, or None when npm cannot be reached or parsed."""
    try:
        return parse_dist_tags(opener(NPM_DIST_TAGS))
    except (OSError, ValueError):
        return None


def stored_versions(root: Path) -> list[str]:
    vendor = root / VENDOR_DIR
    if not vendor.is_dir():
        return []
    found = [
        p.name
        for p in vendor.iterdir()
        if VERSION.match(p.name) and (p / "reveal.min.js").is_file()
    ]
    return sorted(found, key=version_key)


def deck_version(index_html: str) -> str | None:
    match = DECK_VERSION.search(index_html)
    return match.group(1) if match else None


def decks(root: Path) -> list[dict[str, str | None]]:
    folder = root / DECKS_DIR
    if not folder.is_dir():
        return []
    return [
        {
            "name": p.name,
            "reveal": deck_version((p / "index.html").read_text(encoding="utf-8")),
        }
        for p in sorted(folder.iterdir())
        if p.is_dir() and p.name != "vendor" and (p / "index.html").is_file()
    ]


def status(root: Path, opener: Opener = _download) -> dict[str, object]:
    stored = stored_versions(root)
    latest = latest_version(opener)
    newest = stored[-1] if stored else None
    return {
        "folder": str(DECKS_DIR).replace("\\", "/"),
        "folder_exists": (root / DECKS_DIR).is_dir(),
        "stored_versions": stored,
        "latest_version": latest,
        "update_available": bool(
            latest and (newest is None or version_key(latest) > version_key(newest))
        ),
        "presentations": decks(root),
    }


def fetch(root: Path, version: str, opener: Opener = _download) -> Path:
    if not VERSION.match(version):
        raise Refused(f"not a release version: {version!r}")
    dest = root / VENDOR_DIR / version
    if dest.exists():
        raise Refused(f"{dest} already exists; delete it first to fetch again")
    partial = dest.with_name(version + ".partial")
    shutil.rmtree(partial, ignore_errors=True)
    try:
        for name in VENDOR_FILES:
            target = partial / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                opener(CDN.format(version=version) + remote_path(version, name))
            )
        (partial / "LICENSE").write_bytes(opener(LICENSE_URL.format(version=version)))
    except OSError as err:
        shutil.rmtree(partial, ignore_errors=True)
        raise Refused(f"fetch of Reveal.js {version} failed: {err}") from err
    partial.rename(dest)
    return dest


def _check_name(name: str) -> None:
    if not NAME.match(name) or name == "vendor":
        raise Refused(
            f"{name!r} is not a usable name: lowercase letters, digits and single hyphens, not 'vendor'"
        )


def _require_stored(root: Path, version: str) -> None:
    if version not in stored_versions(root):
        raise Refused(f"Reveal.js {version} is not stored; run: fetch {version}")


def new(
    root: Path, name: str, title: str | None = None, version: str | None = None
) -> Path:
    _check_name(name)
    stored = stored_versions(root)
    if version is None:
        if not stored:
            raise Refused("no Reveal.js version is stored; run: fetch <version>")
        version = stored[-1]
    _require_stored(root, version)
    deck = root / DECKS_DIR / name
    if deck.exists():
        raise Refused(f"a presentation named {name!r} already exists at {deck}")
    deck.mkdir(parents=True)
    page = (TEMPLATES / "index.html").read_text(encoding="utf-8")
    page = page.replace("{{TITLE}}", title or name.replace("-", " ").title()).replace(
        "{{VERSION}}", version
    )
    (deck / "index.html").write_text(page, encoding="utf-8")
    shutil.copyfile(TEMPLATES / "theme.css", deck / "theme.css")
    return deck


def _deck_index(root: Path, name: str) -> Path:
    _check_name(name)
    index = root / DECKS_DIR / name / "index.html"
    if not index.is_file():
        raise Refused(f"no presentation named {name!r}: {index} does not exist")
    return index


def use(root: Path, name: str, version: str) -> str:
    index = _deck_index(root, name)
    _require_stored(root, version)
    text = index.read_text(encoding="utf-8")
    old = deck_version(text)
    if old is None:
        raise Refused(
            f"{index} does not load ../vendor/reveal.js/<version>/reveal.min.css"
        )
    index.write_text(
        text.replace(f"../vendor/reveal.js/{old}/", f"../vendor/reveal.js/{version}/"),
        encoding="utf-8",
    )
    return old


def to_artifact(index_html: str) -> str:
    """The page as the Artifact host wants it: no skeleton, local reveal.css, scripts from cdnjs."""
    version = deck_version(index_html)
    if version is None:
        raise Refused(
            "index.html does not load ../vendor/reveal.js/<version>/reveal.min.css"
        )
    local = f"../vendor/reveal.js/{version}/"
    lines = [
        line
        for line in index_html.splitlines(keepends=True)
        if not SKELETON.match(line)
    ]
    page = "".join(lines).replace(local + "reveal.min.css", "reveal.css")
    cdn = CDN.format(version=version)
    for name in VENDOR_FILES[1:]:
        page = page.replace(local + name, cdn + remote_path(version, name))
    if "../vendor/" in page:
        raise Refused("a ../vendor/ path from another version is left in the page")
    return page


def build_artifact(root: Path, name: str, out: Path) -> Path:
    index = _deck_index(root, name)
    text = index.read_text(encoding="utf-8")
    page = to_artifact(text)
    version = deck_version(text)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{name}.html"
    target.write_text(page, encoding="utf-8")
    shutil.copyfile(index.parent / "theme.css", out / "theme.css")
    shutil.copyfile(
        root / VENDOR_DIR / str(version) / "reveal.min.css", out / "reveal.css"
    )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n", 1)[0])
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="repository root (default: cwd)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    p = sub.add_parser("fetch")
    p.add_argument("version")
    p = sub.add_parser("new")
    p.add_argument("name")
    p.add_argument("--title")
    p.add_argument("--version")
    p = sub.add_parser("use")
    p.add_argument("name")
    p.add_argument("version")
    p = sub.add_parser("build-artifact")
    p.add_argument("name")
    p.add_argument("out", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()

    try:
        if args.command == "status":
            print(json.dumps(status(root), indent=2))
        elif args.command == "fetch":
            print(f"stored Reveal.js {args.version} in {fetch(root, args.version)}")
        elif args.command == "new":
            print(f"created {new(root, args.name, args.title, args.version)}")
        elif args.command == "use":
            old = use(root, args.name, args.version)
            print(f"{args.name}: Reveal.js {old} -> {args.version}")
        elif args.command == "build-artifact":
            print(f"built {build_artifact(root, args.name, args.out)}")
    except Refused as err:
        print(f"refused: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
