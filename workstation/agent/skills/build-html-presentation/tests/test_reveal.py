"""Tests for the build-html-presentation scripts. No network: every download goes through a stub."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import render_check
import reveal


class stub_opener:
    """An opener that answers npm dist-tags with ``latest`` and any other URL with its own name."""

    def __init__(self, latest: str = "6.0.2", fail: bool = False) -> None:
        self.latest = latest
        self.fail = fail
        self.calls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.calls.append(url)
        if self.fail:
            raise OSError("offline")
        if url == reveal.NPM_DIST_TAGS:
            return json.dumps({"latest": self.latest, "next": "7.0.0-beta.1"}).encode()
        return url.encode()


def store(root: Path, version: str) -> None:
    folder = root / reveal.VENDOR_DIR / version
    folder.mkdir(parents=True)
    for name in reveal.VENDOR_FILES:
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(name, encoding="utf-8")


class VersionTests(unittest.TestCase):
    def test_dist_tags_latest(self):
        self.assertEqual(reveal.parse_dist_tags(b'{"latest":"6.0.2"}'), "6.0.2")

    def test_dist_tags_without_latest_is_rejected(self):
        with self.assertRaises(ValueError):
            reveal.parse_dist_tags(b'{"next":"7.0.0"}')

    def test_latest_is_none_when_offline(self):
        self.assertIsNone(reveal.latest_version(stub_opener(fail=True)))

    def test_versions_sort_numerically(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for v in ("5.10.0", "5.9.1", "10.0.0"):
                store(root, v)
            self.assertEqual(
                reveal.stored_versions(root), ["5.9.1", "5.10.0", "10.0.0"]
            )

    def test_folder_without_reveal_js_is_not_a_stored_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / reveal.VENDOR_DIR / "5.1.0.partial").mkdir(parents=True)
            (root / reveal.VENDOR_DIR / "6.0.0").mkdir()
            self.assertEqual(reveal.stored_versions(root), [])


class StatusTests(unittest.TestCase):
    def test_empty_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = reveal.status(Path(tmp), stub_opener())
        self.assertFalse(s["folder_exists"])
        self.assertEqual(s["stored_versions"], [])
        self.assertEqual(s["presentations"], [])
        self.assertTrue(s["update_available"])

    def test_stored_older_than_latest_and_decks_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store(root, "5.1.0")
            reveal.new(root, "info-session")
            s = reveal.status(root, stub_opener("6.0.2"))
        self.assertEqual(s["stored_versions"], ["5.1.0"])
        self.assertEqual(s["latest_version"], "6.0.2")
        self.assertTrue(s["update_available"])
        self.assertEqual(
            s["presentations"], [{"name": "info-session", "reveal": "5.1.0"}]
        )

    def test_current_version_needs_no_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store(root, "6.0.2")
            self.assertFalse(
                reveal.status(root, stub_opener("6.0.2"))["update_available"]
            )

    def test_offline_reports_no_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store(root, "5.1.0")
            s = reveal.status(root, stub_opener(fail=True))
        self.assertIsNone(s["latest_version"])
        self.assertFalse(s["update_available"])


class FetchTests(unittest.TestCase):
    def test_fetch_stores_every_file_and_licence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            opener = stub_opener()
            dest = reveal.fetch(root, "6.0.2", opener)
            for name in (*reveal.VENDOR_FILES, "LICENSE"):
                self.assertTrue((dest / name).is_file(), name)
            self.assertIn(
                "https://cdnjs.cloudflare.com/ajax/libs/reveal.js/6.0.2/reveal.min.js",
                opener.calls,
            )
            self.assertEqual(reveal.stored_versions(root), ["6.0.2"])

    def test_failed_fetch_leaves_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(reveal.Refused):
                reveal.fetch(root, "6.0.2", stub_opener(fail=True))
            self.assertEqual(list((root / reveal.VENDOR_DIR).iterdir()), [])

    def test_existing_version_is_not_refetched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store(root, "6.0.2")
            with self.assertRaises(reveal.Refused):
                reveal.fetch(root, "6.0.2", stub_opener())

    def test_plugin_paths_follow_the_release_layout(self):
        # Reveal.js 6 moved each plugin's browser build from plugin/<p>/<p>.min.js to plugin/<p>.min.js.
        cdn = "https://cdnjs.cloudflare.com/ajax/libs/reveal.js/"
        for version, remote in (
            ("5.1.0", "plugin/highlight/highlight.min.js"),
            ("6.0.2", "plugin/highlight.min.js"),
        ):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as tmp:
                opener = stub_opener()
                dest = reveal.fetch(Path(tmp), version, opener)
                self.assertIn(f"{cdn}{version}/{remote}", opener.calls)
                self.assertTrue((dest / "plugin" / "highlight.min.js").is_file())

    def test_tag_is_not_a_version(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(reveal.Refused):
            reveal.fetch(Path(tmp), "latest", stub_opener())


class NewAndUseTests(unittest.TestCase):
    def test_new_creates_folder_and_fills_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store(root, "5.1.0")
            deck = reveal.new(root, "q3-review", title="Q3 Review")
            page = (deck / "index.html").read_text(encoding="utf-8")
            self.assertEqual(deck, root / "docs" / "html-presentations" / "q3-review")
            self.assertIn("<title>Q3 Review</title>", page)
            self.assertIn("../vendor/reveal.js/5.1.0/reveal.min.js", page)
            self.assertNotIn("{{", page)
            self.assertTrue((deck / "theme.css").is_file())

    def test_new_uses_newest_stored_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store(root, "5.1.0")
            store(root, "6.0.2")
            deck = reveal.new(root, "deck")
            self.assertEqual(
                reveal.deck_version((deck / "index.html").read_text(encoding="utf-8")),
                "6.0.2",
            )

    def test_duplicate_name_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store(root, "5.1.0")
            reveal.new(root, "deck")
            with self.assertRaises(reveal.Refused):
                reveal.new(root, "deck")

    def test_bad_names_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store(root, "5.1.0")
            for name in ("Deck", "my deck", "a--b", "-a", "vendor", "../x"):
                with self.subTest(name=name), self.assertRaises(reveal.Refused):
                    reveal.new(root, name)

    def test_new_without_stored_version_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(reveal.Refused):
            reveal.new(Path(tmp), "deck")

    def test_use_repoints_every_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store(root, "5.1.0")
            store(root, "6.0.2")
            deck = reveal.new(root, "deck", version="5.1.0")
            self.assertEqual(reveal.use(root, "deck", "6.0.2"), "5.1.0")
            page = (deck / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("5.1.0", page)
            self.assertEqual(page.count("../vendor/reveal.js/6.0.2/"), 6)

    def test_use_requires_stored_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store(root, "5.1.0")
            reveal.new(root, "deck")
            with self.assertRaises(reveal.Refused):
                reveal.use(root, "deck", "6.0.2")


class ArtifactTests(unittest.TestCase):
    PAGE = (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width">\n<title>T</title>\n'
        '<link rel="stylesheet" href="../vendor/reveal.js/5.1.0/reveal.min.css">\n</head>\n<body>\n'
        "<section>slide</section>\n"
        '<script src="../vendor/reveal.js/5.1.0/reveal.min.js"></script>\n</body>\n</html>\n'
    )

    def test_skeleton_stripped_and_paths_rewritten(self):
        page = reveal.to_artifact(self.PAGE)
        self.assertNotRegex(page, r"<(html|head|body|meta)\b|<!doctype")
        self.assertIn('href="reveal.css"', page)
        self.assertIn(
            'src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.1.0/reveal.min.js"',
            page,
        )
        self.assertTrue(page.startswith("<title>T</title>"))

    def test_artifact_plugin_path_follows_the_release_layout(self):
        plugin = '<script src="../vendor/reveal.js/{v}/plugin/zoom.min.js"></script>\n'
        css = '<link rel="stylesheet" href="../vendor/reveal.js/{v}/reveal.min.css">\n'
        cdn = "https://cdnjs.cloudflare.com/ajax/libs/reveal.js/"
        for version, remote in (
            ("5.1.0", "plugin/zoom/zoom.min.js"),
            ("6.0.2", "plugin/zoom.min.js"),
        ):
            with self.subTest(version=version):
                page = reveal.to_artifact((css + plugin).format(v=version))
                self.assertIn(f'src="{cdn}{version}/{remote}"', page)

    def test_page_without_stored_reveal_is_refused(self):
        with self.assertRaises(reveal.Refused):
            reveal.to_artifact("<title>T</title>")

    def test_build_artifact_writes_page_and_both_stylesheets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store(root, "5.1.0")
            reveal.new(root, "deck")
            target = reveal.build_artifact(root, "deck", root / "out")
            self.assertEqual(target.name, "deck.html")
            self.assertEqual(
                {p.name for p in (root / "out").iterdir()},
                {"deck.html", "theme.css", "reveal.css"},
            )

    def test_cli_reports_refusal_with_exit_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                reveal.main(["--root", tmp, "build-artifact", "missing", tmp]), 1
            )


class RenderFindingsTests(unittest.TestCase):
    def test_fitting_slide_has_no_findings(self):
        self.assertEqual(
            render_check.findings(
                "1", {"bottom": 700, "right": 1200, "stacked": 0}, 1280, 720
            ),
            [],
        )

    def test_overflow_and_stacked_code_reported(self):
        issues = [
            f["issue"]
            for f in render_check.findings(
                "7", {"bottom": 980, "right": 1300, "stacked": 1}, 1280, 720
            )
        ]
        self.assertEqual(issues, ["overflow-bottom", "overflow-right", "stacked-code"])


if __name__ == "__main__":
    unittest.main()
