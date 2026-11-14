"""Unit tests for check_links.py.

Standard library only (unittest), so the skill has no dependencies of its own:
    python -m unittest discover -s tests -t tests -v
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

# E402: sys.path has to be extended before this import, so it cannot move to the top.
import check_links


class Tree:
    """A temporary folder of Markdown files, written from a {relative path: text} map."""

    def __init__(self, files: dict[str, str]) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel, text in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def check(self, rel: str) -> list[check_links.Broken]:
        return check_links.check_file(self.root / rel)

    def close(self) -> None:
        self._tmp.cleanup()


class CheckFileTests(unittest.TestCase):
    def tree(self, files: dict[str, str]) -> Tree:
        tree = Tree(files)
        self.addCleanup(tree.close)
        return tree

    def test_existing_file_link_passes(self) -> None:
        t = self.tree({"a.md": "See [b](b.md).\n", "b.md": "# B\n"})
        self.assertEqual(t.check("a.md"), [])

    def test_missing_file_is_reported_with_its_line(self) -> None:
        t = self.tree({"a.md": "# A\n\nSee [b](nope.md).\n"})
        broken = t.check("a.md")
        self.assertEqual(
            [(b.line, b.target, b.reason) for b in broken],
            [(3, "nope.md", "missing file")],
        )

    def test_link_into_a_subfolder_and_back_up(self) -> None:
        t = self.tree(
            {
                "docs/a.md": "[r](../README.md) [d](sub/)\n",
                "README.md": "x\n",
                "docs/sub/x.md": "x\n",
            }
        )
        self.assertEqual(t.check("docs/a.md"), [])

    def test_missing_anchor_in_another_file(self) -> None:
        t = self.tree({"a.md": "[b](b.md#nowhere)\n", "b.md": "# Somewhere\n"})
        broken = t.check("a.md")
        self.assertEqual(
            [(b.target, b.reason) for b in broken], [("b.md#nowhere", "missing anchor")]
        )

    def test_same_file_anchor_uses_github_slugs(self) -> None:
        text = "# The `ingest` command: v2.0 & more\n\n## my_var\n\n[a](#the-ingest-command-v20--more) [b](#my_var)\n"
        t = self.tree({"a.md": text})
        self.assertEqual(t.check("a.md"), [])

    def test_duplicate_headings_get_numbered_slugs(self) -> None:
        t = self.tree(
            {"a.md": "# Setup\n\n# Setup\n\n[2nd](#setup-1) [3rd](#setup-2)\n"}
        )
        broken = t.check("a.md")
        self.assertEqual([b.target for b in broken], ["#setup-2"])

    def test_html_anchor_counts(self) -> None:
        t = self.tree({"a.md": '<a id="here"></a>\n\n[x](#here)\n'})
        self.assertEqual(t.check("a.md"), [])

    def test_links_in_code_are_ignored(self) -> None:
        text = "```md\n[x](nope.md)\n# Not a heading\n```\n\nRun `[y](nope.md)` here.\n\n[z](#not-a-heading)\n"
        t = self.tree({"a.md": text})
        self.assertEqual([b.target for b in t.check("a.md")], ["#not-a-heading"])

    def test_external_and_mail_links_are_ignored(self) -> None:
        t = self.tree(
            {"a.md": "[w](https://example.org/x.md) [m](mailto:a@b.c) [f](ftp://h/x)\n"}
        )
        self.assertEqual(t.check("a.md"), [])

    def test_title_angle_brackets_and_percent_encoding(self) -> None:
        text = '[a](b.md "Title") [c](<my file.md>) [d](my%20file.md) ![img](pic.png)\n'
        t = self.tree({"a.md": text, "b.md": "x\n", "my file.md": "x\n", "pic.png": ""})
        self.assertEqual(t.check("a.md"), [])

    def test_reference_definition_is_checked(self) -> None:
        t = self.tree({"a.md": "See [b][ref].\n\n[ref]: missing.md\n"})
        self.assertEqual(
            [(b.line, b.target) for b in t.check("a.md")], [(3, "missing.md")]
        )

    def test_anchor_into_a_non_markdown_file_is_not_checked(self) -> None:
        t = self.tree({"a.md": "[c](code.py#L10)\n", "code.py": "x = 1\n"})
        self.assertEqual(t.check("a.md"), [])


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = check_links.main(list(args))
        return code, out.getvalue()

    def test_exit_zero_when_clean_and_one_when_broken(self) -> None:
        tree = Tree({"ok.md": "[s](#s)\n\n# S\n", "bad.md": "[x](gone.md)\n"})
        self.addCleanup(tree.close)
        code, out = self.run_cli(str(tree.root / "ok.md"))
        self.assertEqual(
            (code, out.strip().splitlines()[-1]), (0, "0 broken links in 1 file")
        )
        code, out = self.run_cli(str(tree.root / "ok.md"), str(tree.root / "bad.md"))
        self.assertEqual(code, 1)
        self.assertIn("bad.md:1: missing file: gone.md", out)

    def test_folder_is_searched_and_skip_dirs_are_left_out(self) -> None:
        tree = Tree(
            {
                "a.md": "x\n",
                "d/b.md": "[g](gone.md)\n",
                "node_modules/c.md": "[g](gone.md)\n",
            }
        )
        self.addCleanup(tree.close)
        code, out = self.run_cli(str(tree.root))
        self.assertEqual(code, 1)
        self.assertEqual(out.strip().splitlines()[-1], "1 broken links in 2 files")

    def test_missing_argument_exits_two(self) -> None:
        self.assertEqual(self.run_cli("/no/such/file.md")[0], 2)

    def test_json_output(self) -> None:
        tree = Tree({"bad.md": "[x](gone.md)\n"})
        self.addCleanup(tree.close)
        code, out = self.run_cli("--json", str(tree.root / "bad.md"))
        self.assertEqual(code, 1)
        rows = json.loads(out)
        self.assertEqual(
            [(r["line"], r["target"], r["reason"]) for r in rows],
            [(1, "gone.md", "missing file")],
        )


if __name__ == "__main__":
    unittest.main()
