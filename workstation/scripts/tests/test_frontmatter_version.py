"""Every `version:` in frontmatter must equal `pyproject.toml`'s.

Skills, guides and the agent harness now carry `author`/`version` in their
frontmatter for discoverability, alongside the repo-wide version this
workbench otherwise relies on as the single source of truth. A file that
repeats a fact needs a test, or the two drift the first time a release is
cut without updating every copy. Standard library only.
"""

from __future__ import annotations

import sys
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bump_frontmatter_version import frontmatter_version, versioned_files  # noqa: E402


class TestFrontmatterVersions(unittest.TestCase):
    def setUp(self) -> None:
        with (REPO / "pyproject.toml").open("rb") as handle:
            self.repo_version = tomllib.load(handle)["project"]["version"]

    def test_every_frontmatter_version_matches_pyproject(self) -> None:
        files = versioned_files(REPO)
        self.assertTrue(files, "no files matched — the glob list is stale")
        for path in files:
            with self.subTest(path.relative_to(REPO).as_posix()):
                self.assertEqual(
                    frontmatter_version(path),
                    self.repo_version,
                    f"{path.relative_to(REPO)} version disagrees with "
                    f"pyproject.toml {self.repo_version!r}",
                )


if __name__ == "__main__":
    unittest.main()
