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
#: that creates a file instead of editing one.
PATCH_FILE_LINE = re.compile(r"^\*\*\* (?:Update|Add) File: (.+)$", re.MULTILINE)


def edited_path(payload: dict) -> Path | None:
    """The file the tool wrote, absolute, or None when the payload names none."""
    args = payload.get("tool_input") or payload.get("toolArgs") or {}
    value = None
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            match = PATCH_FILE_LINE.search(args)
            value = match.group(1) if match else None
            args = {}
    if value is None:
        if not isinstance(args, dict):
            return None
        value = next((args[k] for k in PATH_KEYS if isinstance(args.get(k), str)), None)
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = Path(payload.get("cwd") or os.getcwd()) / path
    return path


def ruff_beside(interpreter: str) -> Path:
    """The ruff executable installed next to ``interpreter``."""
    name = "ruff.exe" if os.name == "nt" else "ruff"
    return Path(interpreter).parent / name


def main(stdin=None, interpreter: str = sys.executable, run=subprocess.run) -> int:
    try:
        payload = json.load(stdin if stdin is not None else sys.stdin)
    except ValueError:
        return 0
    path = edited_path(payload) if isinstance(payload, dict) else None
    if path is None or path.suffix != ".py" or not path.is_file():
        return 0
    ruff = ruff_beside(interpreter)
    if not ruff.is_file():
        return 0
    status = 0
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
