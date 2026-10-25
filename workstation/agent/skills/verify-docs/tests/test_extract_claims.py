"""Unit tests for the verify-docs claims extractor.

Standard library only (unittest), so the skill has no dependencies of its own:
    python -m unittest discover -s tests -v
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# E402: sys.path has to be extended before this import, so it cannot move to the top.
from extract_claims import (
    extract_from_text,
    install_claim,
    looks_like_command,
    looks_like_path,
    subject_binary,
    summarise,
    tracked_markdown,
)


def kinds(claims):
    return [c.kind for c in claims]


def by_kind(claims, kind):
    return [c for c in claims if c.kind == kind]


class TestInstallClaim(unittest.TestCase):
    def test_brew_maps_to_registry_and_local_checks(self):
        self.assertEqual(
            install_claim("brew install pandoc"),
            ("pandoc", "brew info --json=v2 pandoc", "brew list --versions pandoc"),
        )

    def test_npm_global_flag_is_not_the_package(self):
        claim = install_claim("npm install -g @mermaid-js/mermaid-cli")
        assert claim is not None
        pkg, registry, present = claim
        self.assertEqual(pkg, "@mermaid-js/mermaid-cli")
        self.assertEqual(registry, "npm view @mermaid-js/mermaid-cli version")
        # `command -v @mermaid-js/mermaid-cli` would be meaningless: the package
        # ships a binary called `mmdc`. Ask npm instead.
        self.assertEqual(present, "npm ls -g --depth=0 @mermaid-js/mermaid-cli")

    def test_uv_tool_install_uses_pypi(self):
        claim = install_claim("uv tool install docling")
        assert claim is not None
        self.assertEqual(claim[1], "pip index versions docling")

    def test_non_install_command_returns_none(self):
        self.assertIsNone(install_claim("pandoc input.md -o out.pdf"))


class TestPathHeuristic(unittest.TestCase):
    def test_accepts_relative_and_absolute_paths(self):
        self.assertTrue(looks_like_path("~/.claude/settings.json"))
        self.assertTrue(looks_like_path("workstation/cli/README.md"))
        self.assertTrue(looks_like_path("./scripts/run.sh"))

    def test_rejects_prose_and_urls(self):
        self.assertFalse(looks_like_path("pandoc"))
        self.assertFalse(looks_like_path("https://example.com/x"))
        self.assertFalse(looks_like_path("and/or"))  # one slash, no extension
        self.assertFalse(looks_like_path("..."))  # ellipsis in prose
        self.assertFalse(looks_like_path("../.."))  # no name component


class TestSubjectBinary(unittest.TestCase):
    def test_prefers_the_command_head_over_the_folder_name(self):
        text = "# mermaid-cli\n\n```\nmmdc -i a.mmd -o a.svg\nmmdc -i b.mmd -o b.svg\n```\n"
        self.assertEqual(
            subject_binary(text, "workstation/cli/mermaid-cli/quick_start.md"), "mmdc"
        )

    def test_falls_back_to_the_cli_folder_name(self):
        self.assertEqual(
            subject_binary(
                "# d2\n\nProse only.\n", "workstation/cli/d2-cli/quick_start.md"
            ),
            "d2",
        )

    def test_returns_none_outside_the_cli_tree(self):
        self.assertIsNone(subject_binary("# Readme\n\nProse.\n", "README.md"))


class TestExtraction(unittest.TestCase):
    def test_install_command_yields_registry_and_presence_claims(self):
        claims = extract_from_text("install.md", "```\nbrew install pandoc\n```\n")
        self.assertEqual(kinds(claims), ["install", "install"])
        self.assertEqual(claims[0].verification_command, "brew info --json=v2 pandoc")
        self.assertEqual(claims[1].verification_command, "brew list --versions pandoc")

    def test_bare_flag_in_prose_binds_to_the_document_subject(self):
        text = "```\npandoc a.md -o b.pdf\n```\n\nOverride with `--wrap=none`.\n"
        claim = by_kind(
            extract_from_text("workstation/cli/pandoc/quick_start.md", text), "cli_flag"
        )[0]
        self.assertEqual(claim.claim, "pandoc supports --wrap")
        self.assertEqual(
            claim.verification_command, "pandoc --help 2>&1 | grep -F -- '--wrap'"
        )

    def test_flags_after_a_bare_double_dash_are_not_the_outer_commands(self):
        """`claude mcp add … -- npx … --authentication pat`: `--authentication`
        belongs to the command after `--`, so `claude` must not be asked about it."""
        text = (
            "```\nclaude mcp add --transport stdio ado -e X=1 -- "
            "npx -y @azure-devops/mcp org --authentication pat\n```\n"
        )
        found = [c.claim for c in by_kind(extract_from_text("s.md", text), "cli_flag")]
        self.assertEqual(found, ["claude mcp add supports --transport"])

    def test_local_script_flags_bind_to_the_interpreter_and_script(self):
        text = "```\npython workstation/scripts/databricks_mcp.py --profile demo\n```\n"
        found = [
            c.claim
            for c in by_kind(
                extract_from_text("workstation/scripts/README.md", text), "cli_flag"
            )
        ]
        self.assertEqual(
            found,
            ["python workstation/scripts/databricks_mcp.py supports --profile"],
        )

    def test_uv_run_flags_split_between_uv_and_the_wrapped_command(self):
        """`uv run --no-sync --project R python s.py --repo .`: uv's options end at
        the first positional; `--repo` belongs to the script, not to `uv run`."""
        text = (
            "```\n"
            'uv run --no-sync --project "$R" python s.py --repo .\n'
            "uv run --frozen -- confluence-sync-md --help\n"
            "```\n"
        )
        found = [c.claim for c in by_kind(extract_from_text("s.md", text), "cli_flag")]
        self.assertEqual(
            found,
            [
                "uv run supports --no-sync",
                "uv run supports --project",
                "python s.py supports --repo",
                "uv run supports --frozen",
            ],
        )

        snippet = "Run `uv run --no-sync python s.py --apply` first.\n"
        found = [
            c.claim for c in by_kind(extract_from_text("s.md", snippet), "cli_flag")
        ]
        self.assertEqual(
            found, ["uv run supports --no-sync", "python s.py supports --apply"]
        )

    def test_subcommand_flags_bind_to_the_complete_command(self):
        text = (
            "```\n"
            "ug mcp-proxy --url endpoint --host workspace --profile profile\n"
            "ug configure --agents claude\n"
            "ug mcp add --names system.ai.genie_one_mcp\n"
            "```\n"
        )
        found = [
            c.claim
            for c in by_kind(extract_from_text("quick_start.md", text), "cli_flag")
        ]
        self.assertEqual(
            found,
            [
                "ug mcp-proxy supports --url",
                "ug mcp-proxy supports --host",
                "ug mcp-proxy supports --profile",
                "ug configure supports --agents",
                "ug mcp add supports --names",
            ],
        )

    def test_inline_snippet_stops_at_a_bare_double_dash_too(self):
        text = "Run `copilot mcp add db --timeout 5 -- ug mcp-proxy --url x --profile p`.\n"
        found = [c.claim for c in by_kind(extract_from_text("s.md", text), "cli_flag")]
        self.assertEqual(found, ["copilot mcp add supports --timeout"])

    def test_a_double_dash_inside_a_flag_or_word_is_not_a_separator(self):
        text = "```\ngit log --oneline --no-merges a--b\n```\n"
        found = [c.claim for c in by_kind(extract_from_text("s.md", text), "cli_flag")]
        self.assertEqual(
            found,
            ["git log supports --oneline", "git log supports --no-merges"],
        )

    def test_flag_claim_is_dropped_when_no_binary_can_be_inferred(self):
        # No fenced block and not under workstation/cli, so there is no subject.
        self.assertEqual(
            by_kind(
                extract_from_text("README.md", "Use `--wrap=none` here.\n"), "cli_flag"
            ),
            [],
        )

    def test_short_flags_in_prose_are_captured(self):
        text = "```\npandoc a.md\n```\n\nOverride with `-f` and `-t`.\n"
        found = by_kind(
            extract_from_text("workstation/cli/pandoc/quick_start.md", text), "cli_flag"
        )
        self.assertEqual(
            [c.claim for c in found], ["pandoc supports -f", "pandoc supports -t"]
        )

    def test_markdown_link_targets_resolve_against_the_document_directory(self):
        text = (
            "See [install](install.md) and [sibling](../weasyprint/quick_start.md).\n"
        )
        found = by_kind(
            extract_from_text("workstation/cli/pandoc/quick_start.md", text), "path"
        )
        self.assertEqual(
            [c.verification_command for c in found],
            [
                "test -e workstation/cli/pandoc/install.md",
                "test -e workstation/cli/weasyprint/quick_start.md",
            ],
        )

    def test_anchors_are_stripped_and_external_links_ignored(self):
        text = "See [a](README.md#section) and [b](https://example.com/page).\n"
        found = by_kind(extract_from_text("docs/x.md", text), "path")
        self.assertEqual(
            [c.verification_command for c in found], ["test -e docs/README.md"]
        )

    def test_urls_become_http_head_claims(self):
        claim = by_kind(
            extract_from_text("README.md", "Docs: <https://pandoc.org/>\n"), "url"
        )[0]
        self.assertIn(
            "curl -sS -o /dev/null -w '%{http_code}' -I -L 'https://pandoc.org/'",
            claim.verification_command,
        )

    def test_placeholder_url_templates_are_not_claims(self):
        for line in (
            "curl -s https://registry.npmjs.org/<pkg>",
            "curl -s https://raw.githubusercontent.com/<owner>/<repo>/<branch>/README.md",
        ):
            with self.subTest(line=line):
                self.assertEqual(by_kind(extract_from_text("x.md", line), "url"), [])

    def test_trailing_sentence_punctuation_is_stripped(self):
        claim = by_kind(
            extract_from_text("x.md", "See https://pandoc.org/index.html.\n"), "url"
        )[0]
        self.assertEqual(claim.claim, "https://pandoc.org/index.html")

    def test_git_state_prose_is_flagged(self):
        claims = by_kind(
            extract_from_text(
                "README.md", "The refactor was merged into main last week.\n"
            ),
            "git",
        )
        self.assertEqual(len(claims), 1)
        self.assertIn("git branch --merged", claims[0].verification_command)

    def test_comments_and_shell_noise_are_skipped(self):
        claims = extract_from_text(
            "x.md", "```\n# just a comment\ncd /tmp\nexport FOO=1\n```\n"
        )
        self.assertEqual(claims, [])

    def test_duplicate_claims_are_collapsed(self):
        text = "```\npandoc a.md --toc\npandoc b.md --toc\n```\n"
        self.assertEqual(len(by_kind(extract_from_text("x.md", text), "cli_flag")), 1)

    def test_every_claim_carries_a_command_and_starts_pending(self):
        text = "```\nbrew install pandoc\npandoc a.md --toc -o b.pdf\n```\n\nSee [x](x.md) at https://example.com\n"
        for claim in extract_from_text("workstation/cli/pandoc/quick_start.md", text):
            self.assertTrue(claim.verification_command.strip(), claim)
            self.assertEqual(claim.status, "PENDING")
            self.assertGreater(claim.line, 0)

    def test_ids_are_sequential_and_unique(self):
        claims = extract_from_text(
            "x.md", "```\nbrew install pandoc\nbrew install pandoc-crossref\n```\n"
        )
        ids = [c.id for c in claims]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))


class TestCommandPlausibility(unittest.TestCase):
    """Fenced blocks hold Python, directory trees and prose as well as shell."""

    def test_accepts_a_plain_invocation(self):
        self.assertTrue(looks_like_command("pandoc a.md -o b.pdf", "pandoc"))

    def test_rejects_python_assignment_and_block_headers(self):
        self.assertFalse(looks_like_command("page = browser.new_page()", "page"))
        self.assertFalse(looks_like_command("with sync_playwright() as p:", "with"))

    def test_rejects_column_aligned_directory_trees(self):
        self.assertFalse(
            looks_like_command("CLAUDE.md          instructions", "CLAUDE.md")
        )
        self.assertFalse(
            looks_like_command("install.md      authored — how to", "install.md")
        )

    def test_rejects_prose_fragments(self):
        self.assertFalse(
            looks_like_command("involved) then extract with defuddle", "involved)")
        )
        self.assertFalse(looks_like_command("Ordered, concrete, each one", "Ordered,"))


class TestFenceLanguages(unittest.TestCase):
    def test_python_fences_yield_no_commands(self):
        text = "```python\nfrom playwright.sync_api import sync_playwright\npage.goto('/')\n```\n"
        self.assertEqual(extract_from_text("x.md", text), [])

    def test_bash_and_untagged_fences_are_both_read(self):
        for fence in ("```bash", "```"):
            with self.subTest(fence=fence):
                claims = extract_from_text("x.md", f"{fence}\npandoc a.md --toc\n```\n")
                self.assertIn("cli_invocation", kinds(claims))

    def test_text_fences_are_skipped(self):
        self.assertEqual(
            extract_from_text("x.md", "```text\npandoc a.md --toc\n```\n"), []
        )


class TestVersionClaims(unittest.TestCase):
    def test_a_bare_version_string_binds_to_the_document_subject(self):
        # `0.7.1` is the output of `d2 --version`, not a command in its own right.
        text = "```\nd2 in.d2 out.svg\n```\n\nExpect `0.7.1`.\n"
        claim = by_kind(
            extract_from_text("workstation/cli/d2-cli/install.md", text), "version"
        )[0]
        self.assertEqual(claim.claim, "`d2 --version` reports 0.7.1")
        self.assertEqual(claim.verification_command, "d2 --version")

    def test_version_is_dropped_when_no_binary_can_be_inferred(self):
        self.assertEqual(
            by_kind(extract_from_text("README.md", "Expect `0.7.1`.\n"), "version"), []
        )


class TestGitClaims(unittest.TestCase):
    def test_matches_real_merge_language(self):
        for line in ("It was merged into main.", "Everything here is tracked in git."):
            with self.subTest(line=line):
                self.assertEqual(
                    len(by_kind(extract_from_text("x.md", line), "git")), 1
                )

    def test_does_not_match_pdf_tagging_or_prose_commitment(self):
        for line in (
            "`--pdf-tags` produces a tagged PDF.",
            "The team committed to the plan.",
        ):
            with self.subTest(line=line):
                self.assertEqual(by_kind(extract_from_text("x.md", line), "git"), [])


class TestSummary(unittest.TestCase):
    def test_summary_reports_totals(self):
        claims = extract_from_text("x.md", "```\nbrew install pandoc\n```\n")
        report = summarise(claims)
        self.assertIn("| install | 2 |", report)
        self.assertIn("**Total: 2 claims across 1 files.**", report)


class TestTrackedMarkdown(unittest.TestCase):
    def test_non_ascii_names_are_returned_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "café.md").write_text("x\n", encoding="utf-8")
            (repo / "plain.md").write_text("x\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            self.assertEqual(sorted(tracked_markdown(repo)), ["café.md", "plain.md"])


if __name__ == "__main__":
    unittest.main()
