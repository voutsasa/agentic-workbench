"""Unit tests for clean_publisher_md.py — stdlib only, no network, no model calls.

    python3 -m unittest discover -s workstation/agent/skills/fetch-to-markdown/tests

Every case below is a rule the ingestion guide's §2 checks would otherwise have
to catch by eye, plus the one they cannot see: content inside a fenced code
block must survive byte-identical, because a `<Note>` or a `</li>` in an example
is that example's text.

The fixtures are the two publishers actually measured on 2026-09-26 — Mintlify
(`code.claude.com`) and GitHub Docs.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# E402: sys.path has to be extended before this import, so it cannot move to the top.
import clean_publisher_md as cleaner

# The page's own URL, not the site root: `./x` and `../x` resolve against it.
PAGE = "https://docs.github.com/en/copilot/concepts/prompting/response-customization"


def convert(text: str, base: str = PAGE) -> str:
    return cleaner.convert(text, base)


class FencedCodeIsUntouched(unittest.TestCase):
    """The failure this script must not have."""

    def test_component_tags_inside_a_fence_survive(self):
        source = (
            '# T\n\n```html\n<Note>keep me</Note>\n<div class="x">and me</div>\n```\n'
        )
        self.assertIn("<Note>keep me</Note>", convert(source))
        self.assertIn('<div class="x">and me</div>', convert(source))

    def test_relative_links_inside_a_fence_are_not_rewritten(self):
        """An example instructions file quotes links into its own repo, not the site."""
        source = "# T\n\n```\nsee [Form](../docs/Form.md) and [x](/y)\n```\n"
        result = convert(source)
        self.assertIn("[x](/y)", result)
        self.assertIn("[Form](../docs/Form.md)", result)

    def test_tilde_fences_count_too(self):
        source = "# T\n\n~~~\n<Note>kept</Note>\n~~~\n"
        self.assertIn("<Note>kept</Note>", convert(source))

    def test_indented_fence_inside_a_component_still_opens(self):
        source = (
            '# T\n\n<Tab title="macOS">\n  ```sh\n  <Note>kept</Note>\n  ```\n</Tab>\n'
        )
        result = convert(source)
        self.assertIn("**macOS**", result)
        self.assertIn("<Note>kept</Note>", result)


class Frontmatter(unittest.TestCase):
    def test_mintlify_frontmatter_is_dropped(self):
        source = (
            "---\n"
            'title: "Trace GitHub Copilot with Langfuse"\n'
            "sidebarTitle: GitHub Copilot\n"
            "---\n\n"
            "# Trace GitHub Copilot with Langfuse\n\nBody.\n"
        )
        result = convert(source)
        self.assertTrue(result.startswith("# Trace GitHub Copilot with Langfuse"))
        self.assertNotIn("sidebarTitle", result)

    def test_a_page_without_frontmatter_is_untouched(self):
        source = "# Title\n\nBody.\n"
        self.assertEqual(convert(source).strip(), source.strip())

    def test_a_horizontal_rule_mid_document_is_not_mistaken_for_frontmatter(self):
        source = "# Title\n\nAbove.\n\n---\n\nBelow.\n"
        result = convert(source)
        self.assertIn("Above.", result)
        self.assertIn("---", result)
        self.assertIn("Below.", result)

    def test_frontmatter_then_blockquote_preamble_both_go(self):
        source = "---\ntitle: X\n---\n\n> ## Documentation Index\n\n# Title\n\nBody.\n"
        self.assertTrue(convert(source).startswith("# Title"))


class Preamble(unittest.TestCase):
    def test_mintlify_index_blockquote_is_dropped(self):
        source = (
            "> ## Documentation Index\n"
            "> Fetch the complete documentation index at: https://example/llms.txt\n"
            "\n"
            "# Hooks reference\n\nBody.\n"
        )
        self.assertTrue(convert(source).startswith("# Hooks reference"))

    def test_real_content_above_the_h1_is_kept(self):
        source = "Intro paragraph.\n\n# Title\n\nBody.\n"
        self.assertTrue(convert(source).startswith("Intro paragraph."))

    def test_a_page_without_an_h1_is_returned_whole(self):
        source = "## Only a subheading\n\nBody.\n"
        self.assertEqual(convert(source).strip(), source.strip())


class MintlifyComponents(unittest.TestCase):
    def test_callout_becomes_a_bold_label(self):
        result = convert("# T\n\n<Note>\n  Mind this.\n</Note>\n")
        self.assertIn("**Note**", result)
        self.assertNotIn("<Note>", result)
        self.assertNotIn("</Note>", result)
        self.assertIn("Mind this.", result)

    def test_titled_component_becomes_its_title(self):
        result = convert(
            '# T\n\n<Steps>\n<Step title="Event fires">\nThen.\n</Step>\n</Steps>\n'
        )
        self.assertIn("**Event fires**", result)
        self.assertNotIn("<Step", result)
        self.assertNotIn("<Steps>", result)

    def test_anchor_only_tags_go_but_their_line_stays(self):
        result = convert('# T\n\n<span id="bash" />For Bash patterns, this applies.\n')
        self.assertIn("For Bash patterns, this applies.", result)
        self.assertNotIn("<span", result)

    def test_img_tag_becomes_a_markdown_image(self):
        result = convert('# T\n\n  <img src="https://cdn/x.svg" alt="Lifecycle" />\n')
        self.assertIn("![Lifecycle](https://cdn/x.svg)", result)

    def test_inline_img_keeps_the_sentence_around_it(self):
        """modelcontextprotocol.io drops an icon mid-sentence."""
        result = convert(
            '# T\n\nLook for the <img src="https://cdn/icon.png" width="33" /> icon:\n'
        )
        self.assertIn("Look for the ![](https://cdn/icon.png) icon:", result)


class GitHubDocsComponents(unittest.TestCase):
    def test_tool_tab_div_wrapper_is_dropped(self):
        source = '# T\n\n<div class="ghd-tool vscode">\n\nBody for VS Code.\n\n</div>\n'
        result = convert(source)
        self.assertNotIn("<div", result)
        self.assertNotIn("</div>", result)
        self.assertIn("Body for VS Code.", result)

    def test_list_in_a_table_cell_is_flattened(self):
        source = (
            "# T\n\n| Symptom | Fix |\n| --- | --- |\n"
            "| Hooks not running | <ul><li>Check the path.</li><li>Check the JSON.</li></ul> |\n"
        )
        result = convert(source)
        self.assertIn(
            "| Hooks not running | Check the path.; Check the JSON. |", result
        )
        self.assertNotIn("<ul>", result)
        self.assertNotIn("<li>", result)

    def test_kbd_becomes_code(self):
        self.assertIn("Press `Ctrl`", convert("# T\n\nPress <kbd>Ctrl</kbd>\n"))


class Links(unittest.TestCase):
    def test_site_relative_target_is_absolutised(self):
        result = convert("# T\n\nSee [hooks](/en/copilot/hooks).\n")
        self.assertIn("[hooks](https://docs.github.com/en/copilot/hooks)", result)

    def test_trailing_slash_on_the_base_does_not_double(self):
        result = convert("# T\n\n[x](/a)\n", base="https://agents.md/")
        self.assertIn("[x](https://agents.md/a)", result)

    def test_sibling_relative_target_resolves_against_the_page(self):
        """modelcontextprotocol.io links siblings as `./server-concepts`."""
        result = convert(
            "# T\n\nSee [server concepts](./server-concepts).\n",
            base="https://modelcontextprotocol.io/docs/learn/architecture",
        )
        self.assertIn(
            "[server concepts](https://modelcontextprotocol.io/docs/learn/server-concepts)",
            result,
        )

    def test_parent_relative_target_resolves_against_the_page(self):
        result = convert("# T\n\n[up](../prompting/x).\n")
        self.assertIn(
            "[up](https://docs.github.com/en/copilot/concepts/prompting/x)", result
        )

    def test_bare_relative_target_resolves_against_the_page(self):
        """The unity-gateway README links `tests/integration/README.md` with no `./`."""
        result = convert(
            "# T\n\nSee [tests](tests/integration/README.md).\n",
            base="https://github.com/databricks/unity-gateway/blob/main/README.md",
        )
        self.assertIn(
            "[tests](https://github.com/databricks/unity-gateway/blob/main/tests/integration/README.md)",
            result,
        )

    def test_fragments_schemes_and_absolute_targets_are_untouched(self):
        source = "# T\n\n[a](#install) [b](mailto:x@y.org) [c](https://z.org/p) [d](http://q.org)\n"
        result = convert(source)
        for target in (
            "(#install)",
            "(mailto:x@y.org)",
            "(https://z.org/p)",
            "(http://q.org)",
        ):
            self.assertIn(target, result)

    def test_autolinks_are_not_treated_as_tags(self):
        result = convert("# T\n\nSee <https://example.com/a> for more.\n")
        self.assertIn("<https://example.com/a>", result)


class Idempotence(unittest.TestCase):
    def test_running_twice_changes_nothing(self):
        source = (
            "> ## Documentation Index\n\n# T\n\n<Note>\nA.\n</Note>\n\n"
            '<div class="ghd-tool webui">\n\n[x](/y)\n\n</div>\n\n```\n<Note>kept</Note>\n```\n'
        )
        once = convert(source)
        self.assertEqual(once, convert(once))


if __name__ == "__main__":
    unittest.main()
