"""Unit tests for the deterministic documentation-truth gate.

Standard library only (unittest), no network, no model:
    python3 -m unittest discover -s tests -v

Two regression classes have their own sections, because both have shipped bugs
before and both fail silently — a wrong answer here looks exactly like a right
one until someone follows the documentation and it does not work:

  * TestBaseDirectoryRegression — which directory a relative path resolves from.
  * TestSimilarLookingSubjects  — binding a version or a flag to the right tool
    when two tools in the same document look alike.
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# E402: sys.path has to be extended before these imports, so they cannot move up.
from dataclasses import asdict

from extract_claims import Claim
from verify_claims import (
    FLAG_ALLOW_FILE_NAME,
    REFUTED,
    UNVERIFIABLE,
    VERIFIED,
    ManifestIndex,
    Result,
    Verifier,
    advertised_subcommands,
    candidate_paths,
    clip,
    collect_claims,
    command_on_line,
    exemption_notice,
    format_report,
    frontmatter_version_claims,
    help_subject,
    main,
    parse_frontmatter,
    read_allow_file,
    read_flag_allow_file,
    root_is_known,
    source_line,
    tls_advice,
    transport_failure,
)


class TempRepo:
    """A throwaway directory tree written from a {relative path: contents} map."""

    def __init__(self, files: dict[str, str]) -> None:
        self.root = Path(tempfile.mkdtemp())
        for rel, text in files.items():
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

    def __enter__(self) -> Path:
        return self.root

    def __exit__(self, *exc: object) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


class OnPath:
    """A stub executable on PATH for the duration of the block.

    A regression test must not need the real tool installed. Two of these
    previously passed only on a workstation with pandoc present and failed on a
    bare runner — which is precisely where CI runs them, and precisely the kind
    of environment-dependent green that hides a broken rule.
    """

    def __init__(self, name: str, output: str = "") -> None:
        self.dir = Path(tempfile.mkdtemp())
        script = self.dir / name
        script.write_text(f"#!/bin/sh\ncat <<'STUB_EOF'\n{output}\nSTUB_EOF\n")
        script.chmod(0o755)
        self._previous = os.environ.get("PATH", "")

    def __enter__(self) -> Path:
        os.environ["PATH"] = f"{self.dir}{os.pathsep}{self._previous}"
        return self.dir

    def __exit__(self, *exc: object) -> None:
        os.environ["PATH"] = self._previous
        shutil.rmtree(self.dir, ignore_errors=True)


def claim(
    kind: str, text: str, file: str = "doc.md", line: int = 1, command: str = ""
) -> Claim:
    return Claim(
        id="C0001",
        file=file,
        line=line,
        kind=kind,
        claim=text,
        verification_method="test",
        verification_command=command,
    )


# --------------------------------------------------------------------------
# The base-directory rule
# --------------------------------------------------------------------------


class TestBaseDirectoryRegression(unittest.TestCase):
    """A relative path has two plausible bases and picking wrong passes silently.

    `./NOTES.md` inside `workstation/cli/pandoc/quick_start.md` means the file
    beside that document. A resolver that tries the repo root as well will find
    an unrelated NOTES.md there and report a dead link as healthy.
    """

    def test_dot_slash_resolves_against_the_document_directory(self):
        bases = candidate_paths(
            Path("/repo"), "workstation/cli/pandoc/quick_start.md", "./NOTES.md"
        )
        self.assertEqual(
            [("document", Path("/repo/workstation/cli/pandoc/NOTES.md"))], bases
        )

    def test_dot_slash_is_given_no_repo_root_fallback(self):
        bases = candidate_paths(Path("/repo"), "a/b/doc.md", "./NOTES.md")
        self.assertEqual(1, len(bases), "an anchored path must have exactly one base")
        self.assertNotIn(Path("/repo/NOTES.md"), [candidate for _, candidate in bases])

    def test_dot_dot_climbs_from_the_document_not_the_root(self):
        bases = candidate_paths(Path("/repo"), "a/b/doc.md", "../sibling.md")
        self.assertEqual([("document", Path("/repo/a/sibling.md"))], bases)

    def test_a_root_level_namesake_does_not_rescue_a_broken_relative_link(self):
        """The regression itself, end to end, on a real filesystem."""
        with TempRepo(
            {
                "NOTES.md": "a decoy at the repo root\n",
                "deep/doc.md": "see [notes](./NOTES.md)\n",
            }
        ) as root:
            verifier = Verifier(root)
            result = verifier.verify_path(
                claim("path", "./NOTES.md", file="deep/doc.md")
            )
            self.assertEqual(
                REFUTED, result[2], f"root-level decoy masked the break: {result}"
            )

    def test_the_same_link_passes_when_the_file_is_actually_beside_the_document(self):
        with TempRepo(
            {
                "deep/NOTES.md": "the real one\n",
                "deep/doc.md": "see [notes](./NOTES.md)\n",
            }
        ) as root:
            verifier = Verifier(root)
            verdict = verifier.verify_path(
                claim("path", "./NOTES.md", file="deep/doc.md")
            )
            self.assertEqual(VERIFIED, verdict[2])
            self.assertIn("document", verdict[1])

    def test_unanchored_path_tries_the_repo_root_first(self):
        bases = candidate_paths(Path("/repo"), "a/b/doc.md", "docs/guidance/README.md")
        self.assertEqual("repo root", bases[0][0])
        self.assertEqual(Path("/repo/docs/guidance/README.md"), bases[0][1])

    def test_unanchored_path_falls_back_to_the_document_directory(self):
        bases = candidate_paths(Path("/repo"), "a/b/doc.md", "sub/thing.md")
        self.assertEqual(["repo root", "document"], [base for base, _ in bases])

    def test_evidence_names_the_base_that_resolved(self):
        with TempRepo({"x/y.md": "y\n", "doc.md": "see `x/y.md`\n"}) as root:
            _verifier, evidence, verdict = Verifier(root).verify_path(
                claim("path", "x/y.md")
            )
            self.assertEqual(VERIFIED, verdict)
            self.assertIn("repo root", evidence)

    def test_percent_escapes_are_decoded_before_resolving(self):
        bases = candidate_paths(
            Path("/repo"), "doc.md", "docs/Non-functional%20requirements.md"
        )
        self.assertEqual(Path("/repo/docs/Non-functional requirements.md"), bases[0][1])

    def test_anchor_and_query_are_not_part_of_the_path(self):
        bases = candidate_paths(Path("/repo"), "doc.md", "README.md#section")
        self.assertEqual(Path("/repo/README.md"), bases[0][1])

    def test_home_relative_path_is_not_resolved_against_the_repo(self):
        bases = candidate_paths(Path("/repo"), "doc.md", "~/.claude/settings.json")
        self.assertEqual(["home"], [base for base, _ in bases])


# --------------------------------------------------------------------------
# Telling similar-looking tools apart
# --------------------------------------------------------------------------


class TestSimilarLookingSubjects(unittest.TestCase):
    """Two tools in one repo look alike; the verdict must still name the right one.

    Version numbers collide (three tools here sit on 10.1.1), binaries do not
    match their folder (`mermaid-cli` ships `mmdc`), and a page about one tool
    mentions another often enough to steal the attribution.
    """

    MERMAID = "---\ntool: mermaid-cli\ncommand: mmdc\nversion_observed: 11.16.0\n---\n\n# mermaid\n"
    PLANTUML = (
        "---\ntool: plantuml-cli\ncommand: plantuml\nversion_observed: 1.2026.6\n---\n\n"
        "# plantuml\n\nInstall with `scoop install plantuml`; scoop is the usual route,\n"
        "and scoop keeps it current.\n"
    )
    DBML = "---\ntool: dbml-cli\ncommand: dbml2sql, sql2dbml, db2dbml\nversion_observed: 10.1.1\n---\n"

    def test_version_binds_to_the_declared_command_not_the_folder_name(self):
        with TempRepo({"workstation/cli/mermaid-cli/install.md": self.MERMAID}) as root:
            claims = frontmatter_version_claims(
                root, ["workstation/cli/mermaid-cli/install.md"]
            )
            self.assertEqual(
                ["mmdc reports version 11.16.0"], [c.claim for c in claims]
            )
            self.assertNotIn("mermaid reports", " ".join(c.claim for c in claims))

    def test_version_is_not_stolen_by_the_installer_the_page_talks_about(self):
        """plantuml-cli's page mentions `scoop` three times; the version is PlantUML's."""
        with TempRepo(
            {"workstation/cli/plantuml-cli/install.md": self.PLANTUML}
        ) as root:
            claims = frontmatter_version_claims(
                root, ["workstation/cli/plantuml-cli/install.md"]
            )
            self.assertEqual(
                ["plantuml reports version 1.2026.6"], [c.claim for c in claims]
            )

    def test_a_multi_binary_tool_yields_one_claim_per_binary(self):
        with TempRepo({"workstation/cli/dbml-cli/install.md": self.DBML}) as root:
            claims = frontmatter_version_claims(
                root, ["workstation/cli/dbml-cli/install.md"]
            )
            self.assertEqual(
                [
                    "db2dbml reports version 10.1.1",
                    "dbml2sql reports version 10.1.1",
                    "sql2dbml reports version 10.1.1",
                ],
                sorted(c.claim for c in claims),
            )

    def test_two_tools_sharing_a_version_number_stay_separate(self):
        other = "---\ntool: other\ncommand: othertool\nversion_observed: 10.1.1\n---\n"
        with TempRepo(
            {
                "workstation/cli/dbml-cli/install.md": self.DBML,
                "workstation/cli/other/install.md": other,
            }
        ) as root:
            claims = frontmatter_version_claims(
                root,
                [
                    "workstation/cli/dbml-cli/install.md",
                    "workstation/cli/other/install.md",
                ],
            )
            binaries = {c.claim.split()[0] for c in claims}
            self.assertIn("othertool", binaries)
            self.assertEqual(
                4, len(claims), "one claim per binary, not one per version string"
            )

    def test_a_flag_named_in_prose_can_be_confirmed_but_never_refuted(self):
        """pdf-deliverables.md compares pandoc and WeasyPrint.

        `--pdf-variant` is WeasyPrint's. The extractor attributes it to pandoc,
        the document's dominant binary. Refuting that would blame pandoc for a
        flag it never claimed, so an inferred subject may only be confirmed.
        """
        page = "Verified: the identifier appears only when `--pdf-variant` is passed.\n"
        with (
            TempRepo({"docs/guidance/pdf-deliverables.md": page}) as root,
            OnPath("pandoc", "--pdf-engine\n--pdf-engine-opt\n"),
        ):
            _name, evidence, verdict = Verifier(root).verify_cli_flag(
                claim(
                    "cli_flag",
                    "pandoc supports --pdf-variant",
                    file="docs/guidance/pdf-deliverables.md",
                    line=1,
                )
            )
            self.assertEqual(UNVERIFIABLE, verdict)
            self.assertIn("inferred from prose", evidence)

    def test_a_flag_in_a_real_invocation_is_refutable(self):
        page = "```sh\npandoc --pdf-variant in.md\n```\n"
        with TempRepo({"doc.md": page}) as root, OnPath("pandoc", "--pdf-engine\n"):
            _name, _evidence, verdict = Verifier(root).verify_cli_flag(
                claim("cli_flag", "pandoc supports --pdf-variant", line=2)
            )
            self.assertEqual(
                REFUTED, verdict, "an invocation on the line makes the subject certain"
            )


# --------------------------------------------------------------------------
# Resolving what a flag belongs to
# --------------------------------------------------------------------------


class TestHelpSubject(unittest.TestCase):
    def test_a_subcommand_carries_the_flag(self):
        argv, label = help_subject(
            Path("/repo"), "doc.md", ["git", "diff", "--stat"], "--stat"
        )
        self.assertEqual(["git", "diff"], argv)
        self.assertEqual("git diff", label)

    def test_a_bare_binary_keeps_its_own_flag(self):
        argv, _ = help_subject(
            Path("/repo"), "doc.md", ["pandoc", "--wrap=none"], "--wrap"
        )
        self.assertEqual(["pandoc"], argv)

    def test_a_path_argument_is_not_mistaken_for_a_subcommand(self):
        argv, _ = help_subject(
            Path("/repo"), "doc.md", ["magick", "in.png", "--resize"], "--resize"
        )
        self.assertEqual(["magick"], argv)

    def test_an_interpreter_defers_to_its_script(self):
        with TempRepo(
            {"scripts/extract_claims.py": "#!/usr/bin/env python3\n"}
        ) as root:
            argv, label = help_subject(
                root,
                "doc.md",
                ["python3", "scripts/extract_claims.py", "--out"],
                "--out",
            )
            self.assertEqual("python3", argv[0])
            self.assertTrue(argv[1].endswith("extract_claims.py"))
            self.assertEqual("python3 extract_claims.py", label)

    def test_an_interpreter_with_no_script_on_disk_is_declined(self):
        with TempRepo({}) as root:
            subject = help_subject(
                root, "doc.md", ["python3", "missing.py", "--out"], "--out"
            )
            self.assertEqual("no-script", subject)

    def test_declining_a_script_is_not_reported_as_an_install_risk(self):
        """`python3 x.py --flag` and `npx tool --flag` fail for different reasons."""
        with TempRepo({"doc.md": "```sh\npython3 missing.py --out x\n```\n"}) as root:
            _n, evidence, verdict = Verifier(root).verify_cli_flag(
                claim("cli_flag", "python3 supports --out", line=2)
            )
            self.assertEqual(UNVERIFIABLE, verdict)
            self.assertIn("script this repo does not hold", evidence)

    def test_npx_is_never_run_because_it_would_install(self):
        self.assertIsNone(
            help_subject(Path("/repo"), "doc.md", ["npx", "mmdc", "-i"], "-i")
        )

    def test_command_is_recovered_from_a_fenced_line(self):
        self.assertEqual(
            ["git", "diff", "--stat"], command_on_line("    git diff --stat", "--stat")
        )

    def test_command_is_recovered_from_inline_code(self):
        self.assertEqual(
            ["ruff", "check", "--fix"],
            command_on_line("Run `ruff check --fix` before pushing.", "--fix"),
        )

    def test_a_prose_mention_yields_no_command(self):
        self.assertIsNone(
            command_on_line("The `--fix` option is destructive.", "--fix")
        )

    def test_a_markdown_table_row_is_not_an_invocation(self):
        """A report table contains flags in its text and begins with a pipe."""
        row = "| C0007 | pandoc supports --wrap | file.md:34 | VERIFIED | ok |"
        self.assertIsNone(command_on_line(row, "--wrap"))

    def test_a_placeholder_binary_is_declined(self):
        with TempRepo({"doc.md": "```sh\n<bin> --version\n```\n"}) as root:
            _n, evidence, verdict = Verifier(root).verify_cli_flag(
                claim("cli_flag", "<bin> supports --version", line=2)
            )
            self.assertEqual(UNVERIFIABLE, verdict)
            self.assertIn("placeholder", evidence)

    def test_two_repos_with_a_same_named_file_do_not_share_a_cache(self):
        """source_line caches per file; keyed by name alone the second repo reads the first."""
        with TempRepo({"doc.md": "first tree\n"}) as first:
            self.assertIn("first", source_line(first, "doc.md", 1))
            with TempRepo({"doc.md": "second tree\n"}) as second:
                self.assertIn("second", source_line(second, "doc.md", 1))

    def test_a_shell_prompt_marker_is_stripped(self):
        self.assertEqual(
            ["pandoc", "--wrap"], command_on_line("$ pandoc --wrap", "--wrap")
        )


class TestAdvertisedSubcommands(unittest.TestCase):
    RICH = (
        " Usage: docling [OPTIONS] COMMAND\n"
        "╭─ Options ─────╮\n│ --help   Show this message.  │\n╰────╯\n"
        "╭─ Commands ────╮\n│ convert                      │\n"
        "│ convert-remote  Convert via a remote service │\n╰────╯\n"
    )
    PLAIN = (
        "Usage: defuddle [options] [command]\n\nOptions:\n  -V, --version   version\n\n"
        "Commands:\n  parse [options] [source]  Parse HTML\n  help [command]  display help\n"
    )

    def test_rich_boxed_commands_are_found(self):
        self.assertEqual(
            ["convert", "convert-remote"], advertised_subcommands(self.RICH)
        )

    def test_plain_commands_are_found(self):
        self.assertEqual(["parse"], advertised_subcommands(self.PLAIN))

    def test_help_is_never_offered_as_a_subcommand(self):
        self.assertNotIn("help", advertised_subcommands(self.PLAIN))

    def test_a_tool_without_a_commands_section_offers_none(self):
        self.assertEqual(
            [], advertised_subcommands("Usage: pandoc [OPTIONS]\n  --wrap=auto\n")
        )

    def test_the_sweep_is_bounded(self):
        many = "Commands:\n" + "".join(f"  cmd{n}  does a thing\n" for n in range(20))
        self.assertLessEqual(len(advertised_subcommands(many)), 6)


class TestManPageOverstrike(unittest.TestCase):
    """`git diff --help` pipes a man page whose bold is `c\\bc` per character."""

    MAN = "".join(f"{c}\b{c}" for c in "--staged") + " is a synonym of --cached.\n"

    def test_a_bold_flag_in_a_man_page_is_found(self):
        done = mock.Mock(stdout=self.MAN, stderr="")
        with (
            mock.patch("verify_claims.shutil.which", return_value="/usr/bin/git"),
            mock.patch("verify_claims.subprocess.run", return_value=done),
        ):
            hit = Verifier(Path(".")).find_flag(["git", "diff"], "--staged")
        self.assertIsNotNone(hit)
        self.assertIn("--staged is a synonym", hit[1])


class TestBracketNegationInHelp(unittest.TestCase):
    """git prints an optional negation inline: `--[no-]porcelain[=<version>]`.

    A substring search for the flag as documented misses that line, so the gate
    refuted `git status --porcelain` — a flag its own help screen carries.
    """

    HELP: ClassVar[str] = (
        "usage: git status [<options>]\n"
        "    -s, --short           show status concisely\n"
        "    --[no-]porcelain[=<version>]\n"
        "                          machine-readable output\n"
    )

    def _find(self, flag: str, help_text: str | None = None):
        done = mock.Mock(stdout=help_text if help_text is not None else self.HELP)
        done.stderr = ""
        with (
            mock.patch("verify_claims.shutil.which", return_value="/usr/bin/git"),
            mock.patch("verify_claims.subprocess.run", return_value=done),
        ):
            return Verifier(Path(".")).find_flag(["git", "status"], flag)

    def test_a_flag_printed_in_bracket_form_is_found(self):
        hit = self._find("--porcelain")
        self.assertIsNotNone(hit)
        self.assertIn("[no-]porcelain", hit[1])

    def test_the_negated_spelling_matches_the_same_line(self):
        self.assertIsNotNone(self._find("--no-porcelain"))

    def test_a_plainly_printed_flag_is_unaffected(self):
        hit = self._find("--short")
        self.assertIsNotNone(hit)
        self.assertIn("--short", hit[1])

    def test_a_flag_absent_in_every_form_still_misses(self):
        self.assertIsNone(self._find("--invented"))

    def test_the_bracket_form_does_not_match_a_neighbouring_flag(self):
        self.assertIsNone(self._find("--porcelainish"))


class TestFlagExemptions(unittest.TestCase):
    """`.verify-flags-allow` — the synonym case help cannot settle.

    `git diff -h` documents `--cached` and never mentions `--staged`, which
    works and exits 0. No help parsing finds it, so the repo exempts the pair
    explicitly rather than the checker guessing or the class losing its teeth.
    """

    HELP: ClassVar[str] = "    --cached              compare against the index\n"
    PAGE: ClassVar[str] = "```sh\ngit diff --staged --stat\n```\n"

    def _verdict(self, exemptions):
        done = mock.Mock(stdout=self.HELP)
        done.stderr = ""
        with (
            TempRepo({"doc.md": self.PAGE}) as root,
            mock.patch("verify_claims.shutil.which", return_value="/usr/bin/git"),
            mock.patch("verify_claims.subprocess.run", return_value=done),
        ):
            return Verifier(root, flag_exemptions=exemptions).verify_cli_flag(
                claim("cli_flag", "git supports --staged", line=2)
            )

    def test_an_unlisted_flag_is_still_refuted(self):
        _name, _evidence, verdict = self._verdict(frozenset())
        self.assertEqual(REFUTED, verdict)

    def test_an_exempt_pair_is_unverifiable_and_says_why(self):
        _name, evidence, verdict = self._verdict(frozenset({("git diff", "--staged")}))
        self.assertEqual(UNVERIFIABLE, verdict)
        self.assertIn(FLAG_ALLOW_FILE_NAME, evidence)

    def test_the_exemption_is_bound_to_the_whole_command(self):
        _name, _evidence, verdict = self._verdict(frozenset({("git log", "--staged")}))
        self.assertEqual(
            REFUTED, verdict, "another subcommand's exemption must not travel"
        )

    def test_the_file_yields_command_flag_pairs(self):
        text = (
            "# documented only under its --cached synonym\n"
            "git diff --staged\n"
            "\n"
            "docling convert --to  # subcommand flag\n"
        )
        with TempRepo({FLAG_ALLOW_FILE_NAME: text}) as root:
            self.assertEqual(
                {("git diff", "--staged"), ("docling convert", "--to")},
                read_flag_allow_file(root),
            )

    def test_no_file_means_no_exemptions(self):
        with TempRepo({"doc.md": "x\n"}) as root:
            self.assertEqual(frozenset(), read_flag_allow_file(root))

    def test_a_line_without_a_flag_is_ignored(self):
        with TempRepo({FLAG_ALLOW_FILE_NAME: "git diff\n"}) as root:
            self.assertEqual(frozenset(), read_flag_allow_file(root))


class TestExemptionNotice(unittest.TestCase):
    """An exemption nobody sees is one nobody revisits.

    The pre-push hook echoes the path globs it read; the flag file is read by
    this script, so this script is what says it is in force. Printed by the
    object that made the decision, so the notice cannot disagree with it.
    """

    def test_no_exemptions_says_nothing(self):
        self.assertEqual("", exemption_notice(frozenset()))

    def test_the_notice_names_the_file_the_count_and_the_pair(self):
        notice = exemption_notice(frozenset({("git diff", "--staged")}))
        self.assertIn(FLAG_ALLOW_FILE_NAME, notice)
        self.assertIn("1 flag exemption", notice)
        self.assertIn("git diff --staged", notice)

    def test_pairs_are_sorted_so_the_line_is_reproducible(self):
        pairs = frozenset({("git diff", "--staged"), ("docling convert", "--to")})
        body = exemption_notice(pairs).splitlines()[1:]
        self.assertEqual(
            ["docling convert --to", "git diff --staged"], [ln.strip() for ln in body]
        )

    def test_main_prints_the_notice_on_stderr(self):
        files = {
            FLAG_ALLOW_FILE_NAME: "git diff --staged\n",
            "doc.md": "```sh\ngit diff --staged --stat\n```\n",
        }
        with TempRepo(files) as root:
            err = io.StringIO()
            with (
                contextlib.redirect_stderr(err),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                main(["--repo", str(root), "--files", "doc.md", "--quiet"])
            self.assertEqual("", err.getvalue(), "--quiet prints counts only")

            err = io.StringIO()
            with (
                contextlib.redirect_stderr(err),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                main(["--repo", str(root), "--files", "doc.md"])
            self.assertIn(FLAG_ALLOW_FILE_NAME, err.getvalue())
            self.assertIn("git diff --staged", err.getvalue())


# --------------------------------------------------------------------------
# Manifests, frontmatter, paths, reporting
# --------------------------------------------------------------------------


class TestManifestIndex(unittest.TestCase):
    def test_pyproject_name_and_version_are_indexed(self):
        with TempRepo(
            {"pyproject.toml": '[project]\nname = "sdd-workbench"\nversion = "0.1.0"\n'}
        ) as root:
            self.assertEqual(
                ("0.1.0", "pyproject.toml"), ManifestIndex(root).lookup("sdd-workbench")
            )

    def test_requires_python_is_indexed_under_python(self):
        with TempRepo(
            {"pyproject.toml": '[project]\nname = "x"\nrequires-python = ">=3.14"\n'}
        ) as root:
            found = ManifestIndex(root).lookup("python")
            self.assertIsNotNone(found)
            self.assertEqual("3.14", found[0])

    def test_package_json_version_is_indexed(self):
        with TempRepo(
            {"package.json": json.dumps({"name": "site", "version": "2.3.4"})}
        ) as root:
            self.assertEqual(
                ("2.3.4", "package.json"), ManifestIndex(root).lookup("site")
            )

    def test_lookup_is_case_insensitive(self):
        with TempRepo(
            {"package.json": json.dumps({"name": "Site", "version": "1.0.0"})}
        ) as root:
            self.assertIsNotNone(ManifestIndex(root).lookup("site"))

    def test_a_malformed_manifest_does_not_raise(self):
        with TempRepo({"pyproject.toml": "this is not toml ["}) as root:
            self.assertIsNone(ManifestIndex(root).lookup("anything"))

    def test_a_manifest_disagreement_is_refuted_against_the_manifest(self):
        with TempRepo(
            {
                "package.json": json.dumps({"name": "site", "version": "2.3.4"}),
                "doc.md": "site 9.9.9\n",
            }
        ) as root:
            name, evidence, verdict = Verifier(root).verify_version(
                claim("version", "site reports version 9.9.9")
            )
            self.assertEqual(REFUTED, verdict)
            self.assertEqual("manifest_diff", name)
            self.assertIn("2.3.4", evidence)

    def test_a_manifest_agreement_is_verified_without_running_anything(self):
        with TempRepo(
            {
                "package.json": json.dumps({"name": "site", "version": "2.3.4"}),
                "doc.md": "site 2.3.4\n",
            }
        ) as root:
            _name, _evidence, verdict = Verifier(root).verify_version(
                claim("version", "site reports version 2.3.4")
            )
            self.assertEqual(VERIFIED, verdict)


class TestParseFrontmatter(unittest.TestCase):
    def test_fields_are_parsed_and_quotes_stripped(self):
        self.assertEqual(
            {"tool": "pandoc", "command": "pandoc"},
            parse_frontmatter("---\ntool: 'pandoc'\ncommand: pandoc\n---\n\nbody\n"),
        )

    def test_a_document_without_frontmatter_yields_nothing(self):
        self.assertEqual({}, parse_frontmatter("# Title\n\ncommand: not-frontmatter\n"))

    def test_a_value_containing_a_colon_survives(self):
        self.assertEqual(
            {"url": "https://x.test/a"},
            parse_frontmatter("---\nurl: https://x.test/a\n---\n"),
        )

    def test_a_page_without_a_version_produces_no_claim(self):
        with TempRepo(
            {"workstation/cli/x/install.md": "---\ntool: x\ncommand: x\n---\n"}
        ) as root:
            self.assertEqual(
                [], frontmatter_version_claims(root, ["workstation/cli/x/install.md"])
            )

    def test_only_install_and_setup_pages_are_scanned(self):
        page = "---\ntool: x\ncommand: x\nversion_observed: 1.0\n---\n"
        with TempRepo({"workstation/cli/x/quick_start.md": page}) as root:
            self.assertEqual(
                [],
                frontmatter_version_claims(root, ["workstation/cli/x/quick_start.md"]),
            )


class TestPathVerdicts(unittest.TestCase):
    def test_a_placeholder_is_not_checkable(self):
        with TempRepo({"doc.md": "x\n"}) as root:
            self.assertEqual(
                UNVERIFIABLE,
                Verifier(root).verify_path(claim("path", "<tool>/reference.md"))[2],
            )

    def test_a_bare_word_from_link_syntax_prose_is_not_a_path(self):
        """`[text](target)` in a line explaining links must not become a claim."""
        with TempRepo({"doc.md": "links only ever see `[text](target)`\n"}) as root:
            self.assertEqual(
                UNVERIFIABLE, Verifier(root).verify_path(claim("path", "target"))[2]
            )

    def test_a_slash_command_is_not_an_absolute_path(self):
        with TempRepo({"doc.md": "reinstall with `/plugin`\n"}) as root:
            self.assertEqual(
                UNVERIFIABLE, Verifier(root).verify_path(claim("path", "/plugin"))[2]
            )

    def test_an_absent_home_path_is_machine_state_not_a_doc_defect(self):
        with TempRepo({"doc.md": "x\n"}) as root:
            _n, evidence, verdict = Verifier(root).verify_path(
                claim("path", "~/.claude/definitely-absent-9e7f.json")
            )
            self.assertEqual(UNVERIFIABLE, verdict)
            self.assertIn("machine state", evidence)

    def test_posix_venv_path_with_a_windows_alternative_is_not_refuted(self):
        page = "Use `.venv/bin/python`, or `.venv\\Scripts\\python.exe` on Windows.\n"
        with (
            TempRepo({"doc.md": page}) as root,
            mock.patch("verify_claims.platform.system", return_value="Windows"),
        ):
            _name, evidence, verdict = Verifier(root).verify_path(
                claim("path", ".venv/bin/python", line=1)
            )
            self.assertEqual(UNVERIFIABLE, verdict)
            self.assertIn("explicit Windows alternative", evidence)

    def test_a_path_for_a_foreign_machine_is_not_a_doc_defect(self):
        page = "---\nplatform: macOS 26\n---\n"
        with TempRepo({"workstation/machines/macos-host.md": page}) as root:
            with mock.patch("verify_claims.platform.system", return_value="Windows"):
                _name, evidence, verdict = Verifier(root).verify_path(
                    claim(
                        "path",
                        "/opt/homebrew/bin/tool",
                        file="workstation/machines/macos-host.md",
                    )
                )
            self.assertEqual(UNVERIFIABLE, verdict)
            self.assertIn("recorded for Darwin", evidence)

    def test_a_path_for_the_recorded_machine_remains_checkable(self):
        page = "---\nplatform: macOS 26\n---\n"
        with (
            TempRepo({"workstation/machines/macos-host.md": page}) as root,
            mock.patch("verify_claims.platform.system", return_value="Darwin"),
        ):
            self.assertEqual(
                REFUTED,
                Verifier(root).verify_path(
                    claim(
                        "path",
                        "/opt/homebrew/bin/tool",
                        file="workstation/machines/macos-host.md",
                    )
                )[2],
            )

    def test_a_relative_path_in_a_shell_block_has_no_knowable_cwd(self):
        page = "Install it:\n\n```sh\nln -sf ../../scripts/pre-push .git/hooks/pre-push\n```\n"
        with TempRepo({"a/b/README.md": page}) as root:
            _n, evidence, verdict = Verifier(root).verify_path(
                claim("path", "../../scripts/pre-push", file="a/b/README.md", line=4)
            )
            self.assertEqual(UNVERIFIABLE, verdict)
            self.assertIn("working directory unknown", evidence)

    def test_the_same_path_outside_a_shell_block_is_still_checked(self):
        with TempRepo({"a/b/README.md": "see ../../nope.md\n"}) as root:
            self.assertEqual(
                REFUTED,
                Verifier(root).verify_path(
                    claim("path", "../../nope.md", file="a/b/README.md", line=1)
                )[2],
            )

    def test_an_allow_glob_exempts_a_generated_path(self):
        with TempRepo({"doc.md": "writes .github/workflows/check.yml\n"}) as root:
            verifier = Verifier(root, allow_globs=(".github/**",))
            self.assertEqual(
                UNVERIFIABLE,
                verifier.verify_path(claim("path", ".github/workflows/check.yml"))[2],
            )

    def test_an_allow_glob_matches_a_path_resolved_beside_the_document(self):
        with TempRepo({"workstation/cli/x/install.md": "x\n"}) as root:
            verifier = Verifier(root, allow_globs=("workstation/cli/*/reference.md",))
            self.assertEqual(
                UNVERIFIABLE,
                verifier.verify_path(
                    claim(
                        "path",
                        "reference.md",
                        file="workstation/cli/x/install.md",
                    )
                )[2],
            )

    def test_a_posix_path_is_not_refuted_on_windows(self):
        with TempRepo({"doc.md": "x\n"}) as root:
            with mock.patch("verify_claims.platform.system", return_value="Windows"):
                _name, evidence, verdict = Verifier(root).verify_path(
                    claim("path", "/dev/null")
                )
            self.assertEqual(UNVERIFIABLE, verdict)
            self.assertIn("POSIX path", evidence)

    def test_a_symlink_counts_as_existing_even_when_dangling(self):
        with (
            TempRepo({"doc.md": "x\n"}) as root,
            mock.patch.object(Path, "exists", return_value=False),
            mock.patch.object(Path, "is_symlink", return_value=True),
        ):
            self.assertEqual(
                VERIFIED, Verifier(root).verify_path(claim("path", "link.md"))[2]
            )


class TestUnknownRoot(unittest.TestCase):
    """A path whose root segment is at neither base cannot be judged either way.

    `workstation/mcp/README.md` links to `../cli/README.md` — a correct target —
    but labels it `cli/README.md`, relative to `workstation/`. Refuting the label
    blames the document for an implicit base it never claimed; inventing the base
    would pass a broken path in any repo where `cli/` means something else.
    """

    def test_a_root_at_neither_base_is_unknown(self):
        with TempRepo({"workstation/mcp/README.md": "see `cli/README.md`\n"}) as root:
            self.assertFalse(
                root_is_known(root, "workstation/mcp/README.md", "cli/README.md")
            )

    def test_a_root_at_the_repo_root_is_known(self):
        with TempRepo({"docs/x.md": "x\n", "a.md": "see `docs/x.md`\n"}) as root:
            self.assertTrue(root_is_known(root, "a.md", "docs/x.md"))

    def test_a_root_beside_the_document_is_known(self):
        with TempRepo({"a/sub/x.md": "x\n", "a/doc.md": "see `sub/x.md`\n"}) as root:
            self.assertTrue(root_is_known(root, "a/doc.md", "sub/x.md"))

    def test_the_label_beside_a_correct_target_is_not_refuted(self):
        with TempRepo(
            {
                "workstation/cli/README.md": "the real one\n",
                "workstation/mcp/README.md": "The sibling of [`cli/README.md`](../cli/README.md).\n",
            }
        ) as root:
            _n, evidence, verdict = Verifier(root).verify_path(
                claim("path", "cli/README.md", file="workstation/mcp/README.md")
            )
            self.assertEqual(UNVERIFIABLE, verdict)
            self.assertIn("root is unknown", evidence)

    def test_a_broken_path_under_a_known_root_is_still_refuted(self):
        """The rule must not become a blanket amnesty for missing files."""
        with TempRepo({"docs/real.md": "x\n", "a.md": "see `docs/gone.md`\n"}) as root:
            self.assertEqual(
                REFUTED,
                Verifier(root).verify_path(claim("path", "docs/gone.md", file="a.md"))[
                    2
                ],
            )

    def test_an_anchored_path_is_unaffected_by_the_rule(self):
        with TempRepo({"a/doc.md": "see [x](./gone.md)\n"}) as root:
            self.assertEqual(
                REFUTED,
                Verifier(root).verify_path(claim("path", "./gone.md", file="a/doc.md"))[
                    2
                ],
            )

    def test_a_deleted_root_directory_stops_being_checkable(self):
        """Deleting `.github/` turns its claims from REFUTED into UNVERIFIABLE."""
        with TempRepo(
            {
                ".github/workflows/other.yml": "x\n",
                "s.md": "writes `.github/workflows/c.yml`\n",
            }
        ) as root:
            self.assertEqual(
                REFUTED,
                Verifier(root).verify_path(
                    claim("path", ".github/workflows/c.yml", file="s.md")
                )[2],
            )
            shutil.rmtree(root / ".github")
            self.assertEqual(
                UNVERIFIABLE,
                Verifier(root).verify_path(
                    claim("path", ".github/workflows/c.yml", file="s.md")
                )[2],
            )


class TestAllowFile(unittest.TestCase):
    def test_globs_are_read_one_per_line(self):
        with TempRepo({".verify-claims-allow": ".github/**\n.claude/**\n"}) as root:
            self.assertEqual([".github/**", ".claude/**"], read_allow_file(root))

    def test_comments_and_blank_lines_are_ignored(self):
        body = "# why\n\n.github/**   # trailing note\n\n"
        with TempRepo({".verify-claims-allow": body}) as root:
            self.assertEqual([".github/**"], read_allow_file(root))

    def test_a_repo_without_the_file_inherits_nothing(self):
        with TempRepo({"a.md": "x\n"}) as root:
            self.assertEqual([], read_allow_file(root))

    def test_an_exempt_path_does_not_fail_the_gate(self):
        with TempRepo(
            {
                ".verify-claims-allow": ".github/**\n",
                ".github/workflows/other.yml": "x\n",
                "s.md": "writes `.github/workflows/c.yml`\n",
            }
        ) as root:
            verifier = Verifier(root, allow_globs=tuple(read_allow_file(root)))
            _n, evidence, verdict = verifier.verify_path(
                claim("path", ".github/workflows/c.yml", file="s.md")
            )
            self.assertEqual(UNVERIFIABLE, verdict)
            self.assertIn("--allow", evidence)

    def test_a_path_outside_the_globs_is_still_refuted(self):
        with TempRepo(
            {
                ".verify-claims-allow": ".github/**\n",
                "docs/real.md": "x\n",
                "s.md": "see `docs/gone.md`\n",
            }
        ) as root:
            verifier = Verifier(root, allow_globs=tuple(read_allow_file(root)))
            self.assertEqual(
                REFUTED,
                verifier.verify_path(claim("path", "docs/gone.md", file="s.md"))[2],
            )


class TestReportFrom(unittest.TestCase):
    """A saved run must render identically without re-verifying anything."""

    def test_a_saved_run_round_trips_through_json(self):
        rows = [
            Result(
                "C1", "a.md", 3, "path", "x/y.md", "filesystem", "no such path", REFUTED
            ),
            Result(
                "C2",
                "b.md",
                9,
                "url",
                "https://x.test",
                "http_head",
                "HTTP 200",
                VERIFIED,
            ),
        ]
        restored = [
            Result(**row) for row in json.loads(json.dumps([asdict(r) for r in rows]))
        ]
        self.assertEqual(rows, restored)
        self.assertEqual(format_report(rows), format_report(restored))

    def test_the_rendered_report_still_leads_with_refuted(self):
        rows = [Result("C1", "a.md", 1, "path", "x", "filesystem", "gone", REFUTED)]
        restored = [
            Result(**row) for row in json.loads(json.dumps([asdict(r) for r in rows]))
        ]
        self.assertIn("## Refuted", format_report(restored))


class TestTransportFailure(unittest.TestCase):
    """One broken CA bundle must not read as 179 unverifiable claims."""

    @staticmethod
    def urls(n: int, evidence: str) -> list[Result]:
        return [
            Result(
                f"C{i}",
                "a.md",
                i,
                "url",
                f"https://x{i}.test",
                "http_head",
                evidence,
                UNVERIFIABLE,
            )
            for i in range(n)
        ]

    def test_a_uniform_tls_failure_is_a_broken_tier(self):
        rows = self.urls(
            20, "unreachable: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]>"
        )
        self.assertIn("transport", transport_failure(rows))

    def test_varied_failures_are_the_web_not_the_tier(self):
        rows = self.urls(10, "unreachable: timed out") + self.urls(
            10, "unreachable: name resolution"
        )
        for i, row in enumerate(rows):
            row.id = f"C{i}"
        self.assertIsNone(transport_failure(rows))

    def test_a_healthy_run_reports_nothing(self):
        rows = [
            Result(
                "C1",
                "a.md",
                1,
                "url",
                "https://x.test",
                "http_head",
                "HTTP 200",
                VERIFIED,
            )
        ] * 20
        self.assertIsNone(transport_failure(rows))

    def test_too_few_urls_to_conclude_anything(self):
        self.assertIsNone(
            transport_failure(self.urls(3, "unreachable: <urlopen error>"))
        )

    def test_offline_skips_are_not_transport_failures(self):
        rows = self.urls(20, "skipped — network tier, run with --online")
        self.assertIsNone(transport_failure(rows))


class TestInstallPackageParsing(unittest.TestCase):
    """The package name must survive the manager's own flags and subcommands.

    The first real --online run refuted all 19 brew and npm claims with evidence
    reading "Homebrew has no package --json=v2 sem". The registry was right; the
    parser was handing it the flag.
    """

    @staticmethod
    def parsed(lookup: str) -> str:
        """Reproduce the extraction verify_install performs, without the network."""
        from verify_claims import REGISTRY_API

        for prefix in REGISTRY_API:
            if lookup.startswith(prefix):
                rest = [
                    tok
                    for tok in lookup[len(prefix) :].split()
                    if not tok.startswith("-")
                ]
                pkg = rest[0] if rest else ""
                return "" if pkg in ("version", "versions") else pkg
        return ""

    def test_brew_flags_are_not_the_package(self):
        self.assertEqual("sem", self.parsed("brew info --json=v2 sem"))

    def test_npm_trailing_subcommand_is_not_the_package(self):
        self.assertEqual("defuddle", self.parsed("npm view defuddle version"))

    def test_a_scoped_npm_package_survives(self):
        self.assertEqual(
            "@mermaid-js/mermaid-cli",
            self.parsed("npm view @mermaid-js/mermaid-cli version"),
        )

    def test_pypi_lookup(self):
        self.assertEqual("docling", self.parsed("pip index versions docling"))

    def test_a_lookup_with_no_package_yields_nothing(self):
        self.assertEqual("", self.parsed("npm view version"))


class TestTlsAdvice(unittest.TestCase):
    """The advice must describe this machine, not a guess about how Python got here."""

    def test_it_names_the_interpreter_actually_running(self):
        self.assertIn(sys.executable, "\n".join(tls_advice()))

    def test_it_reports_ssl_cert_file_when_set(self):
        previous = os.environ.get("SSL_CERT_FILE")
        os.environ["SSL_CERT_FILE"] = "/tmp/some-bundle-9e7f.pem"
        try:
            self.assertIn("/tmp/some-bundle-9e7f.pem", "\n".join(tls_advice()))
        finally:
            if previous is None:
                del os.environ["SSL_CERT_FILE"]
            else:
                os.environ["SSL_CERT_FILE"] = previous

    def test_it_says_so_when_ssl_cert_file_is_unset(self):
        previous = os.environ.pop("SSL_CERT_FILE", None)
        try:
            self.assertIn("SSL_CERT_FILE is not set", "\n".join(tls_advice()))
        finally:
            if previous is not None:
                os.environ["SSL_CERT_FILE"] = previous

    def test_it_never_guesses_at_the_installation_method(self):
        """Naming python.org or Homebrew is what sent the last diagnosis wrong."""
        text = " ".join(tls_advice()).lower()
        self.assertNotIn("install certificates.command", text)

    def test_it_degrades_cleanly_without_certifi(self):
        """certifi is optional: its absence is reported, never raised."""
        with mock.patch.dict(sys.modules, {"certifi": None}):
            self.assertIn(
                "certifi is not importable from this interpreter.", tls_advice()
            )

    def test_it_points_at_zshenv_rather_than_zshrc(self):
        text = " ".join(tls_advice())
        if "export SSL_CERT_FILE" in text:
            self.assertIn(".zshenv", text)


class TestTiersAndDispatch(unittest.TestCase):
    def test_a_url_is_skipped_offline(self):
        with TempRepo({"doc.md": "x\n"}) as root:
            result = Verifier(root, online=False).verify(
                claim("url", "https://example.test/a")
            )
            self.assertEqual(UNVERIFIABLE, result.verdict)
            self.assertIn("--online", result.evidence)

    def test_an_install_claim_is_skipped_offline(self):
        with TempRepo({"doc.md": "x\n"}) as root:
            result = Verifier(root, online=False).verify(
                claim(
                    "install",
                    "brew install pandoc",
                    command="brew info --json=v2 pandoc",
                )
            )
            self.assertEqual(UNVERIFIABLE, result.verdict)

    def test_a_git_claim_is_never_guessed_at(self):
        with TempRepo({"doc.md": "x\n"}) as root:
            result = Verifier(root).verify(claim("git", "merged into main"))
            self.assertEqual(UNVERIFIABLE, result.verdict)
            self.assertEqual("git_state", result.verifier)

    def test_a_missing_binary_is_unverifiable_not_refuted(self):
        with TempRepo({"doc.md": "```sh\nnosuchtool-9e7f --flag\n```\n"}) as root:
            result = Verifier(root).verify(
                claim("cli_flag", "nosuchtool-9e7f supports --flag", line=2)
            )
            self.assertEqual(UNVERIFIABLE, result.verdict)
            self.assertIn("not on PATH", result.evidence)

    def test_a_missing_binary_invocation_is_unverifiable(self):
        with TempRepo({"doc.md": "x\n"}) as root:
            result = Verifier(root).verify(
                claim("cli_invocation", "nosuchtool-9e7f convert")
            )
            self.assertEqual(UNVERIFIABLE, result.verdict)


class TestReportAndCollection(unittest.TestCase):
    ROWS: ClassVar[list[Result]] = [
        Result(
            "C1", "a.md", 3, "path", "x/y.md", "filesystem", "no such path", REFUTED
        ),
        Result(
            "C2",
            "b.md",
            9,
            "cli_flag",
            "pandoc supports --wrap",
            "help_text",
            "--wrap=auto",
            VERIFIED,
        ),
        Result(
            "C3",
            "c.md",
            1,
            "url",
            "https://x.test",
            "http_head",
            "skipped",
            UNVERIFIABLE,
        ),
    ]

    def test_the_counts_line_reports_all_three_verdicts(self):
        report = format_report(self.ROWS)
        self.assertIn("1 verified · 1 refuted · 1 unverifiable", report)

    def test_refuted_rows_lead_the_report(self):
        report = format_report(self.ROWS)
        self.assertLess(report.index("## Refuted"), report.index("## Unverifiable"))

    def test_every_requested_column_is_present(self):
        report = format_report(self.ROWS)
        self.assertIn(
            "| id | claim | location | verifier | evidence | verdict |", report
        )

    def test_a_pipe_in_evidence_cannot_break_the_table(self):
        """An unescaped pipe would silently split one row into extra columns."""
        rows = [Result("C1", "a.md", 1, "path", "a|b", "filesystem", "x | y", REFUTED)]
        row = next(
            ln for ln in format_report(rows).splitlines() if ln.startswith("| C1 ")
        )
        header = next(
            ln for ln in format_report(rows).splitlines() if ln.startswith("| id |")
        )
        self.assertEqual(
            header.count("|"),
            row.count("|") - row.count("\\|"),
            "a pipe in the data changed the column count",
        )

    def test_a_clean_run_says_so(self):
        clean = [self.ROWS[1]]
        self.assertIn("No claim was refuted.", format_report(clean))

    def test_files_to_fix_names_the_offending_file(self):
        self.assertIn("a.md", format_report(self.ROWS))

    def test_clip_keeps_evidence_to_one_line(self):
        self.assertNotIn("\n", clip("a\nb\nc"))
        self.assertLessEqual(len(clip("x" * 400)), 110)

    def test_collect_replaces_extractor_versions_with_frontmatter_ones(self):
        page = "---\ntool: mermaid-cli\ncommand: mmdc\nversion_observed: 11.16.0\n---\n\n`mermaid 11.16.0`\n"
        with TempRepo({"workstation/cli/mermaid-cli/install.md": page}) as root:
            claims = collect_claims(root, ["workstation/cli/mermaid-cli/install.md"])
            versions = [c.claim for c in claims if c.kind == "version"]
            self.assertEqual(["mmdc reports version 11.16.0"], versions)

    def test_ids_are_assigned_in_file_order_and_are_unique(self):
        with TempRepo(
            {
                "a.md": "see `docs/x.md`\n",
                "b.md": "see `docs/y.md`\n",
            }
        ) as root:
            claims = collect_claims(root, ["a.md", "b.md"])
            self.assertEqual(len(claims), len({c.id for c in claims}))
            self.assertEqual(sorted(c.id for c in claims), [c.id for c in claims])


if __name__ == "__main__":
    unittest.main()
