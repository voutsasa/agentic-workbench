"""Unit tests for repo_check.py — stdlib only, no network, no model calls.

python3 -m unittest discover -s tests
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# E402: sys.path has to be extended before this import, so it cannot move to the top.
import repo_check


def _cfg(**overrides) -> dict:
    base = {
        "checks": {
            "links": {"enabled": True},
            "terminology": {
                "enabled": True,
                "rules": [
                    {
                        "wrong": "download",
                        "right": "export",
                        "why": "it is an export",
                        "allow_context": [
                            "download browser binaries",
                            "imagemagick.org",
                        ],
                    },
                    {"wrong": "workbench", "right": "workstation", "enabled": False},
                ],
            },
            "bare_paths": {
                "enabled": False,
                "prefixes": ["workstation/cli/"],
                "allow_globs": ["workstation/cli/*/reference.md"],
            },
            "metadata_header": {
                "enabled": False,
                "schemas": [
                    {
                        "name": "tool-doc",
                        "paths": ["tools/*/install.md"],
                        "fields": [
                            {"name": "tool", "equals_directory": True},
                            {
                                "name": "verified",
                                "format": "date",
                                "sentinels": ["never"],
                            },
                            {
                                "name": "status",
                                "allowed_values": ["installed", "route-recorded"],
                            },
                        ],
                    },
                ],
            },
        },
        "scope": {"exclude_globs": ["docs/landing-zone/**"]},
    }
    base.update(overrides)
    return base


class TempRepo:
    """A throwaway directory with markdown files written into it."""

    def __init__(self, files: dict[str, str]):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel, body in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()


class TestProseLines(unittest.TestCase):
    def test_fenced_code_is_skipped(self):
        text = "prose one\n```bash\nrm -rf [x](gone.md)\n```\nprose two\n"
        self.assertEqual(
            [l for _, l in repo_check.prose_lines(text)], ["prose one", "prose two"]
        )

    def test_tilde_fence_is_skipped(self):
        text = "a\n~~~\nhidden\n~~~\nb\n"
        self.assertEqual([l for _, l in repo_check.prose_lines(text)], ["a", "b"])

    def test_line_numbers_survive_skipping(self):
        text = "a\n```\nx\n```\nb\n"
        self.assertEqual([n for n, _ in repo_check.prose_lines(text)], [1, 5])

    def test_inline_code_is_blanked_not_removed(self):
        ((_lineno, line),) = repo_check.prose_lines("run `download all` now")
        self.assertNotIn("download", line)
        self.assertEqual(len(line), len("run `download all` now"))

    def test_keep_code_leaves_inline_code_intact(self):
        ((_, line),) = repo_check.prose_lines("run `download all` now", keep_code=True)
        self.assertEqual(line, "run `download all` now")

    def test_keep_code_still_skips_fenced_blocks(self):
        text = "a\n```\n`hidden`\n```\nb\n"
        self.assertEqual(
            [l for _, l in repo_check.prose_lines(text, keep_code=True)], ["a", "b"]
        )


class TestResolveTarget(unittest.TestCase):
    def test_external_schemes_are_skipped(self):
        for url in ["https://x.com/a.md", "http://x.com", "mailto:a@b.c"]:
            self.assertIsNone(repo_check.resolve_target(url))

    def test_pure_anchor_is_skipped(self):
        self.assertIsNone(repo_check.resolve_target("#section"))

    def test_placeholders_are_skipped(self):
        for ph in ["<tool>/", "...", "{name}.md"]:
            self.assertIsNone(repo_check.resolve_target(ph))

    def test_percent_escapes_are_decoded(self):
        self.assertEqual(
            repo_check.resolve_target("docs/Non-functional%20requirements.md"),
            "docs/Non-functional requirements.md",
        )

    def test_anchor_is_stripped_from_a_real_path(self):
        self.assertEqual(repo_check.resolve_target("guide.md#step-2"), "guide.md")

    def test_angle_brackets_are_unwrapped(self):
        self.assertEqual(repo_check.resolve_target("<a file.md>"), "a file.md")

    def test_trailing_title_is_dropped(self):
        self.assertEqual(repo_check.resolve_target('a.md "The title"'), "a.md")


class TestCheckLinks(unittest.TestCase):
    def test_broken_link_is_reported_with_its_line(self):
        with TempRepo({"a.md": "intro\n\n[gone](missing.md)\n"}) as repo:
            (v,) = repo_check.check_links(repo.root, ["a.md"], _cfg())
            self.assertEqual((v["file"], v["line"], v["check"]), ("a.md", 3, "links"))

    def test_resolving_link_passes(self):
        with TempRepo({"a.md": "[ok](b.md)\n", "b.md": "hi\n"}) as repo:
            self.assertEqual(repo_check.check_links(repo.root, ["a.md"], _cfg()), [])

    def test_link_in_code_block_is_ignored(self):
        with TempRepo({"a.md": "```\n[x](missing.md)\n```\n"}) as repo:
            self.assertEqual(repo_check.check_links(repo.root, ["a.md"], _cfg()), [])

    def test_percent_encoded_target_resolves_to_a_real_file(self):
        with TempRepo(
            {
                "a.md": "[x](Non-functional%20requirements.md)\n",
                "Non-functional requirements.md": "hi\n",
            }
        ) as repo:
            self.assertEqual(repo_check.check_links(repo.root, ["a.md"], _cfg()), [])

    def test_relative_link_resolves_against_its_own_directory(self):
        with TempRepo({"docs/a.md": "[x](b.md)\n", "docs/b.md": "hi\n"}) as repo:
            self.assertEqual(
                repo_check.check_links(repo.root, ["docs/a.md"], _cfg()), []
            )

    def test_image_link_is_checked(self):
        with TempRepo({"a.md": "![alt](missing.png)\n"}) as repo:
            self.assertEqual(
                len(repo_check.check_links(repo.root, ["a.md"], _cfg())), 1
            )

    def test_reference_definition_is_checked(self):
        with TempRepo({"a.md": "see [ref]\n\n[ref]: missing.md\n"}) as repo:
            (v,) = repo_check.check_links(repo.root, ["a.md"], _cfg())
            self.assertEqual(v["line"], 3)


def _bare(**over):
    """_cfg with bare_paths switched on, plus any per-test overrides."""
    cfg = _cfg()
    cfg["checks"]["bare_paths"].update({"enabled": True, **over})
    return cfg


class TestCheckBarePaths(unittest.TestCase):
    """Paths named in prose or backticks, which check_links never sees."""

    def test_missing_path_in_backticks_is_reported(self):
        with TempRepo(
            {"a.md": "intro\n\nread `workstation/cli/gone/quick_start.md`\n"}
        ) as repo:
            (v,) = repo_check.check_bare_paths(repo.root, ["a.md"], _bare())
            self.assertEqual(
                (v["file"], v["line"], v["check"]), ("a.md", 3, "bare_paths")
            )
            self.assertIn("workstation/cli/gone/quick_start.md", v["detail"])

    def test_missing_path_in_plain_prose_is_reported(self):
        with TempRepo(
            {"a.md": "see workstation/cli/gone/install.md for setup\n"}
        ) as repo:
            self.assertEqual(
                len(repo_check.check_bare_paths(repo.root, ["a.md"], _bare())), 1
            )

    def test_existing_path_passes(self):
        with TempRepo(
            {
                "a.md": "read `workstation/cli/pandoc/quick_start.md`\n",
                "workstation/cli/pandoc/quick_start.md": "hi\n",
            }
        ) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_existing_directory_passes(self):
        with TempRepo(
            {
                "a.md": "the `workstation/cli/pandoc/` folder\n",
                "workstation/cli/pandoc/install.md": "hi\n",
            }
        ) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_placeholder_is_not_a_path(self):
        with TempRepo(
            {"a.md": "read `workstation/cli/<tool>/quick_start.md`\n"}
        ) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_fenced_code_is_ignored(self):
        with TempRepo(
            {"a.md": "```sh\ncat workstation/cli/gone/install.md\n```\n"}
        ) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_trailing_sentence_punctuation_is_stripped(self):
        with TempRepo(
            {
                "a.md": "see workstation/cli/pandoc/quick_start.md.\n",
                "workstation/cli/pandoc/quick_start.md": "hi\n",
            }
        ) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_path_inside_a_longer_absolute_path_still_resolves(self):
        with TempRepo(
            {
                "a.md": "read `~/dev/repo/workstation/cli/pandoc/quick_start.md`\n",
                "workstation/cli/pandoc/quick_start.md": "hi\n",
            }
        ) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_allow_globs_exempt_the_gitignored_reference_pages(self):
        with TempRepo(
            {"a.md": "full detail in `workstation/cli/pandoc/reference.md`\n"}
        ) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_anchor_is_not_part_of_the_path(self):
        with TempRepo(
            {
                "a.md": "read `workstation/cli/pandoc/quick_start.md#traps`\n",
                "workstation/cli/pandoc/quick_start.md": "hi\n",
            }
        ) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_anchor_does_not_defeat_allow_globs(self):
        with TempRepo(
            {"a.md": "see `workstation/cli/pandoc/reference.md#flags`\n"}
        ) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_query_string_is_not_part_of_the_path(self):
        with TempRepo(
            {
                "a.md": "see `workstation/cli/pandoc/quick_start.md?raw=1`\n",
                "workstation/cli/pandoc/quick_start.md": "hi\n",
            }
        ) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_percent_escapes_are_decoded(self):
        with TempRepo(
            {
                "a.md": "see `workstation/cli/pandoc/quick%20start.md`\n",
                "workstation/cli/pandoc/quick start.md": "hi\n",
            }
        ) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_a_broken_path_carrying_an_anchor_is_still_reported(self):
        """Normalising the suffix must not turn the check off."""
        with TempRepo(
            {"a.md": "read `workstation/cli/gone/quick_start.md#traps`\n"}
        ) as repo:
            (v,) = repo_check.check_bare_paths(repo.root, ["a.md"], _bare())
            self.assertIn("workstation/cli/gone/quick_start.md", v["detail"])
            self.assertNotIn("#traps", v["detail"])

    def test_link_target_is_left_to_check_links(self):
        with TempRepo({"a.md": "[x](workstation/cli/gone/quick_start.md)\n"}) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_link_text_naming_a_stale_path_is_still_caught(self):
        with TempRepo(
            {"a.md": "[`workstation/cli/gone/`](README.md)\n", "README.md": "hi\n"}
        ) as repo:
            self.assertEqual(
                len(repo_check.check_bare_paths(repo.root, ["a.md"], _bare())), 1
            )

    def test_reference_definition_is_left_to_check_links(self):
        with TempRepo({"a.md": "[ref]: workstation/cli/gone/quick_start.md\n"}) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_a_prefix_not_configured_is_not_checked(self):
        with TempRepo({"a.md": "see `docs/gone/thing.md`\n"}) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare()), []
            )

    def test_added_prefix_is_honoured_without_touching_the_script(self):
        with TempRepo({"a.md": "see `workstation/mcp/gone/setup.md`\n"}) as repo:
            cfg = _bare(prefixes=["workstation/cli/", "workstation/mcp/"])
            self.assertEqual(
                len(repo_check.check_bare_paths(repo.root, ["a.md"], cfg)), 1
            )

    def test_no_prefixes_is_a_no_op(self):
        with TempRepo({"a.md": "see `workstation/cli/gone/install.md`\n"}) as repo:
            self.assertEqual(
                repo_check.check_bare_paths(repo.root, ["a.md"], _bare(prefixes=[])), []
            )

    def test_two_paths_on_one_line_are_reported_separately(self):
        body = "`workstation/cli/gone/a.md` and `workstation/cli/also-gone/b.md`\n"
        with TempRepo({"a.md": body}) as repo:
            self.assertEqual(
                len(repo_check.check_bare_paths(repo.root, ["a.md"], _bare())), 2
            )

    def test_the_check_is_reachable_through_run_checks(self):
        with TempRepo({"a.md": "see `workstation/cli/gone/install.md`\n"}) as repo:
            (v,) = repo_check.run_checks(repo.root, ["a.md"], _bare())
            self.assertEqual(v["check"], "bare_paths")


class TestCheckTerminology(unittest.TestCase):
    def test_disfavoured_term_is_flagged(self):
        with TempRepo({"a.md": "You can download the report.\n"}) as repo:
            (v,) = repo_check.check_terminology(repo.root, ["a.md"], _cfg())
            self.assertIn("export", v["detail"])

    def test_carve_out_phrase_suppresses_the_flag(self):
        with TempRepo({"a.md": "This will download browser binaries.\n"}) as repo:
            self.assertEqual(
                repo_check.check_terminology(repo.root, ["a.md"], _cfg()), []
            )

    def test_carve_out_matches_against_the_link_target(self):
        """Regression: the URL is the context that exonerates the word.

        `[Download](https://imagemagick.org/...)` names their page, not ours —
        matching carve-outs on target-stripped prose made this unreachable.
        """
        with TempRepo(
            {"a.md": "Docs: [Download](https://imagemagick.org/script/x.php)\n"}
        ) as repo:
            self.assertEqual(
                repo_check.check_terminology(repo.root, ["a.md"], _cfg()), []
            )

    def test_disabled_rule_is_not_applied(self):
        with TempRepo({"a.md": "The workbench is here.\n"}) as repo:
            self.assertEqual(
                repo_check.check_terminology(repo.root, ["a.md"], _cfg()), []
            )

    def test_term_inside_code_fence_is_ignored(self):
        with TempRepo({"a.md": "```\nwget --download x\n```\n"}) as repo:
            self.assertEqual(
                repo_check.check_terminology(repo.root, ["a.md"], _cfg()), []
            )

    def test_match_is_case_insensitive(self):
        with TempRepo({"a.md": "Download the file.\n"}) as repo:
            self.assertEqual(
                len(repo_check.check_terminology(repo.root, ["a.md"], _cfg())), 1
            )

    def test_inflections_are_caught(self):
        with TempRepo({"a.md": "Downloading it now.\n"}) as repo:
            self.assertEqual(
                len(repo_check.check_terminology(repo.root, ["a.md"], _cfg())), 1
            )


class TestParseFrontmatter(unittest.TestCase):
    def test_missing_header_is_reported(self):
        fields, err = repo_check.parse_frontmatter("# Title\n")
        self.assertIsNone(fields)
        assert err is not None
        self.assertIn("no YAML frontmatter", err)

    def test_unclosed_header_is_reported(self):
        fields, err = repo_check.parse_frontmatter("---\ntool: a\n")
        self.assertIsNone(fields)
        assert err is not None
        self.assertIn("never closed", err)

    def test_pairs_are_parsed_and_quotes_stripped(self):
        fields, err = repo_check.parse_frontmatter(
            '---\ntool: "a"\nstatus: b\n---\nbody\n'
        )
        self.assertIsNone(err)
        self.assertEqual(fields, {"tool": "a", "status": "b"})

    def test_value_containing_a_colon_survives(self):
        fields, _ = repo_check.parse_frontmatter(
            "---\nrole: Register: the truth\n---\n"
        )
        assert fields is not None
        self.assertEqual(fields["role"], "Register: the truth")

    def test_body_is_not_parsed_as_fields(self):
        fields, _ = repo_check.parse_frontmatter(
            "---\ntool: a\n---\nnope: not a field\n"
        )
        self.assertEqual(fields, {"tool": "a"})


class TestSchemaFor(unittest.TestCase):
    def _schemas(self):
        return [
            {"name": "install", "paths": ["workstation/cli/*/install.md"]},
            {"name": "quick", "paths": ["workstation/cli/*/quick_start.md"]},
        ]

    def test_matching_path_selects_its_schema(self):
        # A deliberately fictional folder: schema_for only glob-matches the
        # string and never touches the filesystem, so naming a real tool here
        # makes the fixture look like a stale path to anyone grepping for one.
        got = repo_check.schema_for(
            "workstation/cli/<tool>/install.md", self._schemas()
        )
        assert got is not None
        self.assertEqual(got["name"], "install")

    def test_unmatched_path_returns_none(self):
        """Files opt IN by being named — no exemption list to maintain."""
        self.assertIsNone(repo_check.schema_for("README.md", self._schemas()))

    def test_first_match_wins(self):
        schemas = [
            {"name": "first", "paths": ["a/*.md"]},
            {"name": "second", "paths": ["a/b.md"]},
        ]
        got = repo_check.schema_for("a/b.md", schemas)
        assert got is not None
        self.assertEqual(got["name"], "first")


class TestValidateFields(unittest.TestCase):
    SCHEMA: ClassVar[dict] = {
        "name": "t",
        "fields": [
            {"name": "tool", "equals_directory": True},
            {"name": "verified", "format": "date", "sentinels": ["never"]},
            {"name": "status", "allowed_values": ["installed", "route-recorded"]},
        ],
    }

    def _run(self, fields, rel="tools/sem/install.md"):
        return repo_check.validate_fields(rel, fields, self.SCHEMA)

    def test_complete_valid_header_passes(self):
        self.assertEqual(
            self._run({"tool": "sem", "verified": "2026-08-20", "status": "installed"}),
            [],
        )

    def test_missing_field_is_named(self):
        problems = self._run({"tool": "sem", "verified": "2026-08-20"})
        self.assertEqual(problems, ["missing `status`"])

    def test_empty_value_is_distinguished_from_missing(self):
        problems = self._run({"tool": "sem", "verified": "2026-08-20", "status": ""})
        self.assertIn("is empty", problems[0])

    def test_value_outside_the_enum_is_rejected(self):
        problems = self._run(
            {"tool": "sem", "verified": "2026-08-20", "status": "banana"}
        )
        self.assertIn("expected one of", problems[0])

    def test_non_iso_date_is_rejected(self):
        problems = self._run(
            {"tool": "sem", "verified": "1 August 2026", "status": "installed"}
        )
        self.assertIn("ISO date", problems[0])

    def test_sentinel_is_accepted_in_place_of_a_date(self):
        """`never` says nobody has checked — honest, and not a format error."""
        self.assertEqual(
            self._run({"tool": "sem", "verified": "never", "status": "installed"}), []
        )

    def test_sentinel_does_not_leak_into_other_fields(self):
        problems = self._run(
            {"tool": "never", "verified": "never", "status": "installed"}
        )
        self.assertIn("its directory is 'sem'", problems[0])

    def test_directory_mismatch_is_caught(self):
        problems = self._run(
            {"tool": "semm", "verified": "2026-08-20", "status": "installed"}
        )
        self.assertIn("but its directory is 'sem'", problems[0])

    def test_all_problems_are_reported_together(self):
        problems = self._run({"tool": "wrong", "verified": "nope", "status": "bad"})
        self.assertEqual(len(problems), 3)


class TestCheckMetadataHeader(unittest.TestCase):
    def _cfg_on(self):
        cfg = _cfg()
        cfg["checks"]["metadata_header"]["enabled"] = True
        return cfg

    def test_file_outside_every_schema_is_skipped(self):
        with TempRepo({"README.md": "# no header\n"}) as repo:
            self.assertEqual(
                repo_check.check_metadata_header(
                    repo.root, ["README.md"], self._cfg_on()
                ),
                [],
            )

    def test_valid_header_passes(self):
        body = "---\ntool: sem\nverified: 2026-08-20\nstatus: installed\n---\n# sem\n"
        with TempRepo({"tools/sem/install.md": body}) as repo:
            self.assertEqual(
                repo_check.check_metadata_header(
                    repo.root, ["tools/sem/install.md"], self._cfg_on()
                ),
                [],
            )

    def test_missing_header_is_reported_once_with_its_schema(self):
        with TempRepo({"tools/sem/install.md": "# sem\n"}) as repo:
            (v,) = repo_check.check_metadata_header(
                repo.root, ["tools/sem/install.md"], self._cfg_on()
            )
            self.assertIn("no YAML frontmatter", v["detail"])
            self.assertIn("tool-doc", v["evidence"])

    def test_one_violation_per_file_not_per_problem(self):
        body = "---\ntool: wrong\nverified: nope\nstatus: bad\n---\n"
        with TempRepo({"tools/sem/install.md": body}) as repo:
            violations = repo_check.check_metadata_header(
                repo.root, ["tools/sem/install.md"], self._cfg_on()
            )
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0]["detail"].count(";"), 2)

    def test_enabled_without_schemas_raises(self):
        cfg = self._cfg_on()
        cfg["checks"]["metadata_header"]["schemas"] = []
        with (
            TempRepo({"a.md": "x\n"}) as repo,
            self.assertRaises(repo_check.CheckError),
        ):
            repo_check.check_metadata_header(repo.root, ["a.md"], cfg)


REGISTER_CFG = {
    "enabled": True,
    "sources": "SOURCES.md",
    "catalogue": "SOURCE_CATALOGUE.md",
    "default_destination": "docs/landing-zone/{name}",
    "extensions": [".md", ".pdf"],
    "destinations": [
        {"section": "CLI tools", "path": "workstation/cli/{name}/reference.md"},
        {"section": "MCP servers", "path": "workstation/mcp/{name}/reference.md"},
    ],
}

# Two layer entries, one CLI tool, one MCP server — the four destination routes
# the invariant defines, in the heading structure SOURCES.md actually uses.
SOURCES_OK = """\
# Register

## 1. Business domain

* [DDD Reference](https://example.com/ddd.pdf)

*See also:* Something Else — a cross-reference, not an entry (§2).

**Gaps — not yet sourced**

- A gap bullet carries no link and is not an entry

## Cross-cutting aspects

### 2. Workstation tooling

#### CLI tools

* [pandoc](https://pandoc.org/)

#### MCP servers

* [drawio-mcp](https://example.com/drawio)
"""

CATALOGUE_OK = """\
# Catalogue

## 1. Business domain

* [DDD Reference](https://example.com/ddd.pdf) — Condensed DDD reference.

## Cross-cutting aspects

### 2. Workstation tooling

#### CLI tools

* [pandoc](https://pandoc.org/) — Converts any document format to any other.

#### MCP servers

* [drawio-mcp](https://example.com/drawio) — Drives draw.io from an MCP client.
"""


def _register_cfg(**overrides) -> dict:
    cfg = _cfg()
    register = dict(REGISTER_CFG)
    register.update(overrides)
    cfg["checks"]["register"] = register
    return cfg


def _register_repo(sources: str = SOURCES_OK, catalogue: str = CATALOGUE_OK, **extra):
    files = {"SOURCES.md": sources, "SOURCE_CATALOGUE.md": catalogue}
    files.update(extra)
    return TempRepo(files)


class TestRegisterFilename(unittest.TestCase):
    """The one transform in the invariant: `: ` in a title is ` - ` on disk."""

    def test_colon_space_becomes_dash(self):
        self.assertEqual(
            repo_check.register_filename("Clean Architecture: The Book"),
            "Clean Architecture - The Book",
        )

    def test_every_colon_space_is_rewritten(self):
        self.assertEqual(repo_check.register_filename("A: B: C"), "A - B - C")

    def test_bare_colon_without_a_space_is_left_alone(self):
        """AGENTS.md names `: ` — the colon AND the space — not every colon."""
        self.assertEqual(repo_check.register_filename("C:Drive"), "C:Drive")

    def test_plain_title_is_unchanged(self):
        self.assertEqual(repo_check.register_filename("pandoc"), "pandoc")


class TestParseRegisterEntries(unittest.TestCase):
    def test_entries_carry_name_url_section_and_line(self):
        entries = repo_check.parse_register_entries(SOURCES_OK)
        self.assertEqual(
            [(e["name"], e["section"]) for e in entries],
            [
                ("DDD Reference", None),
                ("pandoc", "CLI tools"),
                ("drawio-mcp", "MCP servers"),
            ],
        )
        self.assertEqual(entries[0]["url"], "https://example.com/ddd.pdf")
        self.assertEqual(entries[0]["line"], 5)

    def test_see_also_lines_are_not_entries(self):
        self.assertNotIn(
            "Something Else",
            [e["name"] for e in repo_check.parse_register_entries(SOURCES_OK)],
        )

    def test_gap_bullets_are_not_entries(self):
        """A gap has no link, so it cannot be mistaken for an entry."""
        self.assertEqual(len(repo_check.parse_register_entries(SOURCES_OK)), 3)

    def test_a_subsection_is_cleared_by_the_next_higher_heading(self):
        text = "#### CLI tools\n\n* [a](https://a.test)\n\n## Next\n\n* [b](https://b.test)\n"
        self.assertEqual(
            [e["section"] for e in repo_check.parse_register_entries(text)],
            ["CLI tools", None],
        )

    def test_links_inside_fenced_code_are_not_entries(self):
        text = "```\n* [fake](https://fake.test)\n```\n\n* [real](https://real.test)\n"
        self.assertEqual(
            [e["name"] for e in repo_check.parse_register_entries(text)], ["real"]
        )


class TestRegisterDestination(unittest.TestCase):
    def test_layer_entry_lands_in_the_landing_zone(self):
        self.assertEqual(
            repo_check.register_destinations(
                {"name": "DDD Reference", "section": None}, REGISTER_CFG
            ),
            [
                "docs/landing-zone/DDD Reference.md",
                "docs/landing-zone/DDD Reference.pdf",
            ],
        )

    def test_cli_tool_lands_beside_its_authored_guidance(self):
        self.assertEqual(
            repo_check.register_destinations(
                {"name": "pandoc", "section": "CLI tools"}, REGISTER_CFG
            ),
            ["workstation/cli/pandoc/reference.md"],
        )

    def test_mcp_server_lands_in_the_other_tree(self):
        self.assertEqual(
            repo_check.register_destinations(
                {"name": "drawio-mcp", "section": "MCP servers"}, REGISTER_CFG
            ),
            ["workstation/mcp/drawio-mcp/reference.md"],
        )

    def test_the_filename_transform_is_applied_to_the_destination(self):
        self.assertEqual(
            repo_check.register_destinations(
                {"name": "Spec: A Guide", "section": None}, REGISTER_CFG
            )[0],
            "docs/landing-zone/Spec - A Guide.md",
        )


class TestCheckRegister(unittest.TestCase):
    def _run(self, **kw):
        cfg = kw.pop("cfg", None) or _register_cfg()
        with _register_repo(**kw) as repo:
            return repo_check.check_register(repo.root, ["SOURCES.md"], cfg)

    def test_a_mirrored_pair_is_clean(self):
        self.assertEqual(self._run(), [])

    def test_a_repo_without_a_register_is_not_checked(self):
        """checks.toml is shared by every repo that links this skill."""
        with TempRepo({"README.md": "hi\n"}) as repo:
            self.assertEqual(
                repo_check.check_register(repo.root, ["README.md"], _register_cfg()), []
            )

    def test_an_entry_missing_from_the_catalogue_is_a_violation(self):
        catalogue = CATALOGUE_OK.replace(
            "* [pandoc](https://pandoc.org/) — Converts any document format to any other.\n",
            "",
        )
        (violation,) = self._run(catalogue=catalogue)
        self.assertEqual(violation["check"], "register")
        self.assertEqual(violation["file"], "SOURCE_CATALOGUE.md")
        self.assertIn("pandoc", violation["detail"])

    def test_an_entry_only_in_the_catalogue_is_a_violation(self):
        catalogue = (
            CATALOGUE_OK + "* [ghost](https://ghost.test) — Not in the register.\n"
        )
        (violation,) = self._run(catalogue=catalogue)
        self.assertIn("ghost", violation["detail"])

    def test_order_divergence_is_a_violation(self):
        """Same entries, wrong sequence — the catalogue mirrors order too."""
        sources = "## L\n\n* [a](https://a.test)\n* [b](https://b.test)\n"
        catalogue = "## L\n\n* [b](https://b.test) — B.\n* [a](https://a.test) — A.\n"
        with TempRepo(
            {"SOURCES.md": sources, "SOURCE_CATALOGUE.md": catalogue}
        ) as repo:
            violations = repo_check.check_register(
                repo.root, ["SOURCES.md"], _register_cfg()
            )
        self.assertTrue(any("order" in v["detail"] for v in violations), violations)

    def test_url_drift_between_the_pair_is_a_violation(self):
        catalogue = CATALOGUE_OK.replace(
            "https://pandoc.org/", "https://pandoc.example/"
        )
        (violation,) = self._run(catalogue=catalogue)
        self.assertIn("URL", violation["detail"])

    def test_two_links_on_one_entry_break_the_one_to_one_rule(self):
        sources = SOURCES_OK.replace(
            "* [pandoc](https://pandoc.org/)",
            "* [pandoc](https://pandoc.org/) and [typst](https://typst.app/)",
        )
        violations = self._run(sources=sources)
        self.assertTrue(
            any("one bracket link" in v["detail"] for v in violations), violations
        )

    def test_a_see_also_line_with_a_link_is_a_second_entry(self):
        sources = SOURCES_OK.replace(
            "*See also:* Something Else — a cross-reference, not an entry (§2).",
            "*See also:* [Something Else](https://else.test) (§2).",
        )
        violations = self._run(sources=sources)
        self.assertTrue(
            any("see also" in v["detail"].lower() for v in violations), violations
        )

    def test_a_duplicated_entry_name_is_a_violation(self):
        sources = SOURCES_OK.replace(
            "* [drawio-mcp](https://example.com/drawio)",
            "* [pandoc](https://example.com/drawio)",
        )
        violations = self._run(sources=sources)
        self.assertTrue(any("more than once" in v["detail"] for v in violations))

    def test_a_separator_in_an_entry_name_is_a_violation(self):
        """`a/b` would silently write outside the destination folder."""
        sources = SOURCES_OK.replace("* [pandoc]", "* [pan/doc]")
        catalogue = CATALOGUE_OK.replace("* [pandoc]", "* [pan/doc]")
        violations = self._run(sources=sources, catalogue=catalogue)
        self.assertTrue(any("separator" in v["detail"] for v in violations), violations)

    def test_an_absent_destination_file_is_not_a_gate_violation(self):
        """The corpus is gitignored; a fresh clone has none and is not broken."""
        self.assertEqual(self._run(), [])


class TestCorpusLedger(unittest.TestCase):
    def test_present_and_missing_are_both_reported(self):
        with _register_repo(
            **{
                "docs/landing-zone/DDD Reference.md": "x\n",
                "workstation/cli/pandoc/reference.md": "x\n",
            }
        ) as repo:
            rows = repo_check.corpus_ledger(repo.root, _register_cfg())
        self.assertEqual(
            [(r["name"], r["present"]) for r in rows],
            [("DDD Reference", True), ("pandoc", True), ("drawio-mcp", False)],
        )

    def test_a_pdf_satisfies_a_landing_zone_entry(self):
        with _register_repo(**{"docs/landing-zone/DDD Reference.pdf": "x\n"}) as repo:
            rows = repo_check.corpus_ledger(repo.root, _register_cfg())
        self.assertTrue(rows[0]["present"])
        self.assertEqual(rows[0]["found"], "docs/landing-zone/DDD Reference.pdf")

    def test_a_missing_row_names_every_candidate_path(self):
        with _register_repo() as repo:
            rows = repo_check.corpus_ledger(repo.root, _register_cfg())
        self.assertEqual(
            rows[0]["candidates"],
            [
                "docs/landing-zone/DDD Reference.md",
                "docs/landing-zone/DDD Reference.pdf",
            ],
        )

    def test_no_register_means_an_empty_ledger(self):
        with TempRepo({"README.md": "hi\n"}) as repo:
            self.assertEqual(repo_check.corpus_ledger(repo.root, _register_cfg()), [])


class TestRunChecks(unittest.TestCase):
    def test_unimplemented_check_raises_rather_than_passing_silently(self):
        """readme_claims belongs to verify-docs; enabling it here must not no-op."""
        cfg = _cfg()
        cfg["checks"]["readme_claims"] = {"enabled": True}
        with TempRepo({"a.md": "hi\n"}) as repo:
            with self.assertRaises(repo_check.CheckError) as ctx:
                repo_check.run_checks(repo.root, ["a.md"], cfg)
            self.assertIn("verify-docs", str(ctx.exception))

    def test_only_enabled_checks_run(self):
        with TempRepo({"a.md": "# no frontmatter\n"}) as repo:
            self.assertEqual(repo_check.run_checks(repo.root, ["a.md"], _cfg()), [])


class TestGlobMatching(unittest.TestCase):
    def test_double_star_spans_directories(self):
        self.assertTrue(
            repo_check._matches("docs/landing-zone/a/b.md", "docs/landing-zone/**")
        )

    def test_single_star_does_not_span_separator(self):
        # Fictional folder for the same reason as TestSchemaFor's: _matches only
        # compares strings, so naming a real tool invites a future grep to read
        # this as a stale path.
        self.assertTrue(
            repo_check._matches(
                "workstation/cli/<tool>/reference.md", "workstation/cli/*/reference.md"
            )
        )
        self.assertFalse(
            repo_check._matches(
                "workstation/cli/a/b/reference.md", "workstation/cli/*/reference.md"
            )
        )

    def test_unrelated_path_is_kept(self):
        self.assertFalse(repo_check._matches("README.md", "docs/landing-zone/**"))


class TestCollectFiles(unittest.TestCase):
    def test_excluded_paths_are_dropped(self):
        def fake_git(cmd, **kwargs):
            out = "README.md\0docs/landing-zone/x.md\0CLAUDE.md\0"
            return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

        self.assertEqual(
            repo_check.collect_files(Path("/repo"), _cfg(), runner=fake_git),
            ["CLAUDE.md", "README.md"],
        )

    def test_paths_containing_spaces_survive(self):
        def fake_git(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd, 0, stdout="docs/Non-functional requirements.md\0", stderr=""
            )

        self.assertEqual(
            repo_check.collect_files(Path("/repo"), _cfg(), runner=fake_git),
            ["docs/Non-functional requirements.md"],
        )

    def test_git_failure_raises(self):
        def failing(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 128, stdout="", stderr="not a repo")

        with self.assertRaises(repo_check.CheckError):
            repo_check.collect_files(Path("/nope"), _cfg(), runner=failing)


class TestFormatReport(unittest.TestCase):
    def test_clean_run(self):
        self.assertIn("passed", repo_check.format_report([]))

    def test_groups_by_check_with_location(self):
        out = repo_check.format_report(
            [
                {
                    "check": "links",
                    "file": "a.md",
                    "line": 3,
                    "detail": "broken",
                    "evidence": "[x](missing.md)",
                }
            ]
        )
        self.assertIn("[links] 1", out)
        self.assertIn("a.md:3", out)


class TestConfigAndExitCodes(unittest.TestCase):
    def test_missing_config_raises(self):
        with self.assertRaises(repo_check.CheckError):
            repo_check.load_config(Path("/nonexistent/checks.toml"))

    def test_invalid_toml_raises(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as fh:
            fh.write("not = = toml")
            bad = Path(fh.name)
        try:
            with self.assertRaises(repo_check.CheckError):
                repo_check.load_config(bad)
        finally:
            bad.unlink()

    def test_shipped_schemas_cover_the_six_document_families(self):
        cfg = repo_check.load_config(repo_check.DEFAULT_CONFIG)
        names = [s["name"] for s in cfg["checks"]["metadata_header"]["schemas"]]
        self.assertEqual(
            sorted(names),
            [
                "cli-install",
                "cli-quick-start",
                "key-document",
                "machine",
                "mcp-setup",
                "skill",
            ],
        )

    def test_cli_install_schema_carries_no_per_machine_field(self):
        """`version_observed` and `status` describe one box, so they moved to
        workstation/machines/<id>.md. A single-valued field cannot answer
        "is it installed" for a repo spanning several machines."""
        cfg = repo_check.load_config(repo_check.DEFAULT_CONFIG)
        (schema,) = [
            s
            for s in cfg["checks"]["metadata_header"]["schemas"]
            if s["name"] == "cli-install"
        ]
        fields = {f["name"] for f in schema["fields"]}
        self.assertEqual(fields, {"tool", "command", "product", "verified"})

    def test_machine_schema_skips_the_folder_index(self):
        """`*-*.md` and not `*.md`: README.md is the index and has no frontmatter."""
        cfg = repo_check.load_config(repo_check.DEFAULT_CONFIG)
        (schema,) = [
            s
            for s in cfg["checks"]["metadata_header"]["schemas"]
            if s["name"] == "machine"
        ]
        self.assertEqual(schema["paths"], ["workstation/machines/*-*.md"])
        rel = "workstation/machines/README.md"
        with TempRepo({rel: "# Machines\n\nNo frontmatter here.\n"}) as repo:
            self.assertEqual(
                repo_check.check_metadata_header(repo.root, [rel], cfg), []
            )

    def test_machine_schema_accepts_never_as_a_verified_date(self):
        """A machine written about but never probed is an honest `never`."""
        cfg = repo_check.load_config(repo_check.DEFAULT_CONFIG)
        rel = "workstation/machines/macos-workstation.md"
        body = (
            "---\nmachine: macos-workstation\nplatform: macOS\n"
            "shell: unrecorded\nrepo: ~/x\nverified: never\n---\n\n# m\n"
        )
        with TempRepo({rel: body}) as repo:
            self.assertEqual(
                repo_check.check_metadata_header(repo.root, [rel], cfg), []
            )

    def test_skill_schema_requires_a_name_matching_its_directory(self):
        """A SKILL.md whose name does not match its folder does not load at all."""
        cfg = repo_check.load_config(repo_check.DEFAULT_CONFIG)
        rel = "workstation/agent/skills/review/SKILL.md"
        with TempRepo(
            {rel: "---\nname: reviewer\ndescription: x\n---\n\n# R\n"}
        ) as repo:
            (v,) = repo_check.check_metadata_header(repo.root, [rel], cfg)
            self.assertIn("directory is 'review'", v["detail"])

    def test_skill_schema_requires_a_description(self):
        cfg = repo_check.load_config(repo_check.DEFAULT_CONFIG)
        rel = "workstation/agent/skills/review/SKILL.md"
        with TempRepo({rel: "---\nname: review\n---\n\n# R\n"}) as repo:
            (v,) = repo_check.check_metadata_header(repo.root, [rel], cfg)
            self.assertIn("missing `description`", v["detail"])

    def test_quick_start_schema_does_not_duplicate_version_or_status(self):
        """Duplicating install.md's facts across the pair manufactures drift."""
        cfg = repo_check.load_config(repo_check.DEFAULT_CONFIG)
        (qs,) = [
            s
            for s in cfg["checks"]["metadata_header"]["schemas"]
            if s["name"] == "cli-quick-start"
        ]
        names = {f["name"] for f in qs["fields"]}
        self.assertNotIn("version_observed", names)
        self.assertNotIn("status", names)

    def test_shipped_config_has_the_five_deterministic_checks(self):
        cfg = repo_check.load_config(repo_check.DEFAULT_CONFIG)
        self.assertEqual(
            sorted(cfg["checks"]),
            ["bare_paths", "links", "metadata_header", "register", "terminology"],
        )

    def test_every_shipped_check_is_implemented(self):
        """A key in checks.toml with no runner behind it fails the gate at exit 2."""
        cfg = repo_check.load_config(repo_check.DEFAULT_CONFIG)
        self.assertEqual([n for n in cfg["checks"] if n not in repo_check.CHECKS], [])

    def test_shipped_config_declares_no_model(self):
        """Nothing here calls a model; a stray [claude] block would mislead."""
        self.assertNotIn("claude", repo_check.load_config(repo_check.DEFAULT_CONFIG))

    def test_broken_config_exits_two_not_one(self):
        self.assertEqual(
            repo_check.main(["--config", "/nonexistent/checks.toml"]),
            repo_check.EXIT_ERROR,
        )

    def test_error_and_violation_codes_are_distinct(self):
        self.assertNotEqual(repo_check.EXIT_ERROR, repo_check.EXIT_VIOLATIONS)
        self.assertNotEqual(repo_check.EXIT_ERROR, repo_check.EXIT_OK)


if __name__ == "__main__":
    unittest.main()
