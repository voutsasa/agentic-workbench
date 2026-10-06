#!/usr/bin/env python3
"""Print what ``~/.claude/settings.json`` lacks from this repo's reference copy.

The live file is merged by hand, never linked or written
(``workstation/agent/README.md`` § *Settings are merged, never linked*). This
script prints the delta the user types in, and with ``--env`` the checks that
follow the edit. It reads both files and writes neither.

The comparison goes one level into an object-valued key, so
``permissions.defaultMode`` is reported alone rather than the whole of
``permissions``. A list reports only the items the live list lacks: a live
``permissions.allow`` with extra entries is not drift. ``env`` is never
compared, because the reference copy holds none and the live one is
machine-local by design.

``--env`` checks the edited file: that it is valid JSON, which ``env`` keys it
holds (names only), whether ``CLAUDE_CODE_USE_BEDROCK`` is set, and the model
IDs, including the deprecated ``ANTHROPIC_SMALL_FAST_MODEL``. Nothing else from
``env`` is printed.

Exit codes: 0 in sync (or, with ``--env``, readable); 1 keys to add; 2 a file
is missing or is not a JSON object.

Standard library only. Run from anywhere::

    python workstation/scripts/settings_delta.py
    python workstation/scripts/settings_delta.py --env
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE = Path("workstation") / "agent" / "settings.json"

#: The ``env`` members whose values ``--env`` prints. Model IDs are not secret;
#: every other member is reported by name only.
MODEL_KEYS = (
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_SMALL_FAST_MODEL",
)


class Unreadable(Exception):
    """A settings file that is absent or is not a JSON object."""


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Unreadable(f"{path}: not found") from exc
    except (OSError, ValueError) as exc:
        raise Unreadable(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise Unreadable(f"{path}: not a JSON object")
    return data


def _missing(ref: object, live: object) -> object | None:
    """What ``live`` lacks of ``ref`` at one level, or ``None`` if nothing."""
    if isinstance(ref, list) and isinstance(live, list):
        lacking = [item for item in ref if item not in live]
        return lacking or None
    return None if live == ref else ref


def delta(reference: dict, live: dict) -> list[tuple[str, object]]:
    """``(dotted key, value to add)`` for everything ``live`` lacks of ``reference``."""
    out: list[tuple[str, object]] = []
    for key, ref in reference.items():
        if key == "env":
            continue
        have = live.get(key)
        if isinstance(ref, dict) and isinstance(have, dict):
            for member, value in ref.items():
                lacking = _missing(value, have.get(member))
                if lacking is not None:
                    out.append((f"{key}.{member}", lacking))
        else:
            lacking = _missing(ref, have)
            if lacking is not None:
                out.append((key, lacking))
    return out


def env_report(live: dict) -> list[str]:
    found = live.get("env")
    env: dict = found if isinstance(found, dict) else {}
    rows = [
        ("env keys", sorted(env)),
        ("CLAUDE_CODE_USE_BEDROCK", env.get("CLAUDE_CODE_USE_BEDROCK")),
        ("model", live.get("model")),
        *((key, env.get(key)) for key in MODEL_KEYS),
    ]
    width = max(len(label) for label, _ in rows)
    return ["valid JSON", *(f"{label:<{width}} : {value}" for label, value in rows)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--env",
        action="store_true",
        help="check the live file instead: valid JSON, env key names, provider, model IDs",
    )
    parser.add_argument(
        "--home",
        type=Path,
        default=Path.home(),
        help="home directory holding .claude (default: your home)",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=REPO_ROOT,
        help="agentic-workbench clone holding the reference copy (default: this one)",
    )
    args = parser.parse_args(argv)
    try:
        live = load(args.home / ".claude" / "settings.json")
        if args.env:
            print("\n".join(env_report(live)))
            return 0
        missing = delta(load(args.repo / REFERENCE), live)
    except Unreadable as exc:
        print(f"settings_delta: {exc}", file=sys.stderr)
        return 2
    if not missing:
        print("in sync")
        return 0
    for key, value in missing:
        print(f"add {key}: {json.dumps(value)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
