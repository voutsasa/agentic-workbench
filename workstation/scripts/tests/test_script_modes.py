"""Tests that every tracked script with a shebang is executable in git's index.

ruff's EXE001 catches a shebang on a non-executable file, but only where the
filesystem has an executable bit: on Windows it never fires, and Git Bash runs
a hook whatever its mode. A script committed from Windows therefore lands as
100644 and breaks only on macOS and Linux. This test reads the mode git records,
which is the same on every platform, so the gate fails wherever it runs.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def tracked_modes() -> dict[str, str]:
    """Map each tracked path to the mode git's index records for it."""
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-s", "-z"],
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    modes = {}
    for entry in filter(None, out.split("\0")):
        meta, path = entry.split("\t", 1)
        modes[path] = meta.split(" ", 1)[0]
    return modes


def has_shebang(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(2) == b"#!"
    except OSError:
        return False


class ScriptModes(unittest.TestCase):
    def test_every_shebang_script_is_executable_in_the_index(self) -> None:
        wrong = sorted(
            f"{path} is {mode}; run `git update-index --chmod=+x {path}`"
            for path, mode in tracked_modes().items()
            if mode == "100644" and has_shebang(REPO / path)
        )
        self.assertEqual(wrong, [], "\n" + "\n".join(wrong))


if __name__ == "__main__":
    unittest.main()
