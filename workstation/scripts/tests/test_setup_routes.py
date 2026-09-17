"""Documentation contracts for platform-specific setup routes."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
WINDOWS_SETUP = REPO / "workstation" / "agent" / "setup" / "windows.md"


class WindowsSetupRouteTests(unittest.TestCase):
    def test_machine_note_uses_link_config(self) -> None:
        text = WINDOWS_SETUP.read_text(encoding="utf-8")
        self.assertIn("link_config.py --apply", text)
        self.assertNotIn("New-Item -ItemType HardLink", text)


if __name__ == "__main__":
    unittest.main()
