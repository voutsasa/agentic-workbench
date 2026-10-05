"""The plugin manifests' `version` must equal `pyproject.toml`'s.

`VERSIONING.md` holds one source of truth for the repository's version; a
manifest that repeats it needs a test, or the two drift the first time a
release is cut without updating all four. Standard library only.
"""

from __future__ import annotations

import json
import tomllib
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
AGENT = REPO / "workstation" / "agent"

#: label -> (manifest path, how to read its version field)
MANIFESTS: dict[str, tuple[Path, Callable[[Any], str]]] = {
    "claude plugin.json": (
        AGENT / ".claude-plugin" / "plugin.json",
        lambda d: d["version"],
    ),
    "claude marketplace.json": (
        AGENT / ".claude-plugin" / "marketplace.json",
        lambda d: d["plugins"][0]["version"],
    ),
    "copilot plugin.json": (AGENT / "plugin.json", lambda d: d["version"]),
    "copilot marketplace.json": (
        AGENT / "marketplace.json",
        lambda d: d["plugins"][0]["version"],
    ),
}


class TestPluginManifestVersions(unittest.TestCase):
    def setUp(self) -> None:
        with (REPO / "pyproject.toml").open("rb") as handle:
            self.repo_version = tomllib.load(handle)["project"]["version"]

    def test_each_manifest_version_matches_pyproject(self) -> None:
        for label, (path, read_version) in MANIFESTS.items():
            with self.subTest(label):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    read_version(data),
                    self.repo_version,
                    f"{label} version disagrees with pyproject.toml {self.repo_version!r}",
                )


if __name__ == "__main__":
    unittest.main()
