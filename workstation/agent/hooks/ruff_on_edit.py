"""Format and lint the Python file an agent has just written, with the project's own ruff.

A post-tool hook for Claude Code (``PostToolUse`` on ``Edit|Write``) and GitHub
Copilot CLI (``postToolUse`` on ``edit|create|apply_patch``). Both pipe a JSON
payload on stdin; neither sets the edited path in the environment, so it is read
from there: Claude puts it in ``tool_input.file_path``, Copilot in ``toolArgs`` —
JSON for ``edit``/``create``, a raw ``*** Update File: <path>`` patch body for
``apply_patch``.

Run it with the project's venv interpreter — the registration does that and
skips the hook where no ``.venv`` exists — so ``ruff`` is the one installed beside
that interpreter. Nothing is installed or synced: no ruff there, nothing runs.

The whole file is formatted, not just the edited lines. That is a deliberate
choice (workstation/agent/README.md): a file that was not ruff-formatted before shows
formatter changes the edit did not make.

Standard library only. Exit status is ruff's, so a violation ``--fix`` could not
repair is reported back as a non-zero hook result.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

#: Keys that may carry the edited path. Copilot's argument name is not
#: documented, so every spelling seen in its file tools is accepted.
PATH_KEYS = ("file_path", "path", "filePath")

#: Copilot's ``apply_patch`` tool passes a patch body, not JSON, as ``toolArgs``:
#: ``*** Begin Patch\n*** Update File: <path>\n...``. ``Add File`` covers a patch
#: that creates a file instead of editing one. The path is matched non-greedily
#: with an optional trailing ``\r`` before ``$``: on a CRLF patch, plain ``(.+)$``
#: keeps the ``\r`` in the capture (``$`` in MULTILINE mode matches just before
#: the ``\n``), which then never compares equal to a bare ``.py`` suffix.
PATCH_FILE_LINE = re.compile(r"^\*\*\* (?:Update|Add) File: (.+?)\r?$", re.MULTILINE)


def _resolve(value: str | None, cwd: Path) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else cwd / path


def edited_paths(payload: dict) -> list[Path]:
    """Every file the tool wrote, absolute. A multi-file ``apply_patch`` body
    names one per ``Update``/``Add File`` line; any other payload names one."""
    cwd = Path(payload.get("cwd") or os.getcwd())
    args = payload.get("tool_input") or payload.get("toolArgs") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            paths = [
                _resolve(match.group(1), cwd)
                for match in PATCH_FILE_LINE.finditer(args)
            ]
            return [path for path in paths if path is not None]
    if not isinstance(args, dict):
        return []
    value = next((args[k] for k in PATH_KEYS if isinstance(args.get(k), str)), None)
    path = _resolve(value, cwd)
    return [path] if path is not None else []


def edited_path(payload: dict) -> Path | None:
    """The first file the tool wrote, absolute, or None when it names none."""
    paths = edited_paths(payload)
    return paths[0] if paths else None


def ruff_beside(interpreter: str) -> Path:
    """The ruff executable installed next to ``interpreter``."""
    name = "ruff.exe" if os.name == "nt" else "ruff"
    return Path(interpreter).parent / name


def main(stdin=None, interpreter: str = sys.executable, run=subprocess.run) -> int:
    try:
        payload = json.load(stdin if stdin is not None else sys.stdin)
    except ValueError:
        return 0
    paths = edited_paths(payload) if isinstance(payload, dict) else []
    py_paths = [path for path in paths if path.suffix == ".py" and path.is_file()]
    if not py_paths:
        return 0
    ruff = ruff_beside(interpreter)
    if not ruff.is_file():
        return 0
    status = 0
    for path in py_paths:
        for command in (["check", "--fix"], ["format"]):
            done = run(
                [str(ruff), *command, str(path)],
                stdin=subprocess.DEVNULL,
                check=False,
            )
            status = status or done.returncode
    return status


if __name__ == "__main__":
    sys.exit(main())
