"""Tests for link_config.py.

Every test works in a temporary tree, so nothing here can reach a real
``~/.claude``. The link-creation tests exercise the platform's actual mechanism
rather than a stub, because the whole point of the script is that a hardlink and
a plain copy are indistinguishable to anything that only compares content.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import link_config as lc


class TestCopilotHookRegistration(unittest.TestCase):
    def test_uses_copilot_home_environment_variable(self) -> None:
        registration = (
            Path(__file__).resolve().parents[2]
            / "agent"
            / "hooks"
            / "ruff-on-edit.copilot.json"
        )
        hook = json.loads(registration.read_text(encoding="utf-8"))
        command = hook["hooks"]["postToolUse"][0]["bash"]

        self.assertIn(
            '"${COPILOT_HOME:-$HOME/.copilot}/hooks/ruff_on_edit.py"', command
        )


def build_repo(root: Path) -> Path:
    """A minimal repo tree carrying everything plan() expects."""
    agent = root / "workstation" / "agent"
    (agent / "skills").mkdir(parents=True)
    (agent / "AGENT-INSTRUCTIONS.md").write_text("policy\n", encoding="utf-8")
    (agent / "settings.json").write_text("{}\n", encoding="utf-8")
    for skill in lc.SKILLS:
        skill_dir = agent / "skills" / skill
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"# {skill}\n", encoding="utf-8")
    (root / "workstation" / "machines").mkdir(parents=True)
    return root


class TempTree(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.repo = build_repo(self.base / "repo")
        self.home = self.base / "home"
        (self.home / ".claude").mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)

    def machine_file(self, platform: str = "win32", hostname: str = "box") -> Path:
        name = f"{lc.platform_token(platform)}-{hostname}.md"
        path = self.repo / "workstation" / "machines" / name
        path.write_text("state\n", encoding="utf-8")
        return path

    def plan(self, platform: str = "win32", hostname: str = "box") -> list[lc.Link]:
        return lc.plan(self.repo, self.home, platform=platform, hostname=hostname)


class TestPlatformToken(unittest.TestCase):
    def test_maps_the_three_platforms(self) -> None:
        self.assertEqual(lc.platform_token("win32"), "windows")
        self.assertEqual(lc.platform_token("darwin"), "macos")
        self.assertEqual(lc.platform_token("linux"), "linux")

    def test_unknown_platform_falls_back_to_linux(self) -> None:
        self.assertEqual(lc.platform_token("freebsd14"), "linux")

    def test_windows_variants_all_match(self) -> None:
        for plat in ("win32", "windows", "win"):
            self.assertEqual(lc.platform_token(plat), "windows")


class TestShortHostname(unittest.TestCase):
    def test_takes_the_first_label_and_lowercases(self) -> None:
        self.assertEqual(lc.short_hostname("EMA-PF5N4XE7.corp.example"), "ema-pf5n4xe7")

    def test_bare_hostname_survives(self) -> None:
        self.assertEqual(lc.short_hostname("Workstation"), "workstation")


class TestPlan(TempTree):
    def test_covers_the_four_skills_claude_md_and_the_machine_note(self) -> None:
        labels = [link.label for link in self.plan()]
        self.assertEqual(
            labels,
            [f"skills/{s}" for s in lc.SKILLS] + ["CLAUDE.md", "machine.md"],
        )

    def test_skills_come_first_so_junctions_are_never_blocked(self) -> None:
        links = self.plan()
        self.assertTrue(all(link.is_dir for link in links[: len(lc.SKILLS)]))
        self.assertFalse(any(link.is_dir for link in links[len(lc.SKILLS) :]))

    def test_settings_json_is_absent_from_the_plan(self) -> None:
        dests = [link.dest.name for link in self.plan()]
        sources = [link.source.name for link in self.plan()]
        self.assertNotIn("settings.json", dests)
        self.assertNotIn("settings.json", sources)

    def test_machine_note_is_named_from_platform_and_host(self) -> None:
        link = next(
            l for l in self.plan("darwin", "Air.local") if l.label == "machine.md"
        )
        self.assertEqual(link.source.name, "macos-air.md")
        self.assertEqual(link.dest.name, "machine.md")

    def test_every_destination_is_under_dot_claude(self) -> None:
        for link in self.plan():
            self.assertEqual(link.dest.parts[len(self.home.parts)], ".claude")

    def test_a_never_link_destination_raises(self) -> None:
        """The guard is structural: widen it and plan() refuses to emit that link."""
        original = lc.NEVER_LINK
        try:
            lc.NEVER_LINK = frozenset({"CLAUDE.md"})
            with self.assertRaises(AssertionError):
                self.plan()
        finally:
            lc.NEVER_LINK = original


class TestNeverLink(unittest.TestCase):
    def test_settings_json_is_the_guarded_name(self) -> None:
        self.assertIn("settings.json", lc.NEVER_LINK)


class TestInspect(TempTree):
    def test_missing_destination(self) -> None:
        self.machine_file()
        state = lc.inspect(next(l for l in self.plan() if l.label == "CLAUDE.md"))
        self.assertEqual(state.status, lc.MISSING)

    def test_dangling_junction_is_detached_not_missing(self) -> None:
        link = next(l for l in self.plan() if l.label == "skills/review")
        with mock.patch.object(os.path, "isjunction", return_value=True, create=True):
            state = lc.inspect(link)
        self.assertEqual(state.status, lc.DETACHED)
        self.assertEqual(state.detail, "dangling junction")

    def test_no_source_when_the_machine_file_does_not_exist(self) -> None:
        state = lc.inspect(next(l for l in self.plan() if l.label == "machine.md"))
        self.assertEqual(state.status, lc.NO_SOURCE)
        self.assertIn("no source", state.detail)

    def test_detached_when_content_matches(self) -> None:
        link = next(l for l in self.plan() if l.label == "CLAUDE.md")
        link.dest.write_text("policy\n", encoding="utf-8")
        state = lc.inspect(link)
        self.assertEqual(state.status, lc.DETACHED)
        self.assertIn("content still matches", state.detail)

    def test_diverged_when_content_differs(self) -> None:
        link = next(l for l in self.plan() if l.label == "CLAUDE.md")
        link.dest.write_text("an older policy\n", encoding="utf-8")
        state = lc.inspect(link)
        self.assertEqual(state.status, lc.DIVERGED)
        self.assertIn("reconcile", state.detail)

    def test_empty_directory_is_detached_not_occupied(self) -> None:
        link = next(l for l in self.plan() if l.label == "skills/review")
        link.dest.mkdir(parents=True)
        self.assertEqual(lc.inspect(link).status, lc.DETACHED)

    def test_directory_holding_files_is_occupied(self) -> None:
        link = next(l for l in self.plan() if l.label == "skills/review")
        link.dest.mkdir(parents=True)
        (link.dest / "mine.md").write_text("x", encoding="utf-8")
        state = lc.inspect(link)
        self.assertEqual(state.status, lc.OCCUPIED)
        self.assertIn("1 entry", state.detail)

    def test_occupied_pluralises_beyond_one_entry(self) -> None:
        link = next(l for l in self.plan() if l.label == "skills/review")
        link.dest.mkdir(parents=True)
        (link.dest / "a").write_text("x", encoding="utf-8")
        (link.dest / "b").write_text("y", encoding="utf-8")
        self.assertIn("2 entries", lc.inspect(link).detail)

    def test_a_regular_file_where_a_directory_is_expected_is_occupied(self) -> None:
        link = next(l for l in self.plan() if l.label == "skills/review")
        link.dest.parent.mkdir(parents=True, exist_ok=True)
        link.dest.write_text("not a directory", encoding="utf-8")
        state = lc.inspect(link)
        self.assertEqual(state.status, lc.OCCUPIED)
        self.assertIn("file where a directory is expected", state.detail)

    def test_a_junction_to_another_existing_target_is_occupied_not_a_real_directory(
        self,
    ) -> None:
        link = next(l for l in self.plan() if l.label == "skills/review")
        link.dest.mkdir(parents=True)
        (link.dest / "unexpected.md").write_text("x", encoding="utf-8")
        with mock.patch.object(os.path, "isjunction", return_value=True, create=True):
            state = lc.inspect(link)
        self.assertEqual(state.status, lc.OCCUPIED)
        self.assertIn("junction", state.detail.lower())
        self.assertNotIn("real directory holding", state.detail)


class TestSameTarget(TempTree):
    def test_a_plain_copy_is_not_the_same_target(self) -> None:
        a = self.base / "a.md"
        b = self.base / "b.md"
        a.write_text("same", encoding="utf-8")
        b.write_text("same", encoding="utf-8")
        self.assertFalse(lc.same_target(a, b))

    def test_a_real_link_is_the_same_target(self) -> None:
        a = self.base / "a.md"
        a.write_text("x", encoding="utf-8")
        b = self.base / "b.md"
        if os.name == "nt":
            os.link(a, b)
        else:
            os.symlink(a, b)
        self.assertTrue(lc.same_target(a, b))

    def test_a_missing_path_is_not_the_same_target(self) -> None:
        a = self.base / "a.md"
        a.write_text("x", encoding="utf-8")
        self.assertFalse(lc.same_target(a, self.base / "nope.md"))


class TestApply(TempTree):
    def test_links_everything_from_a_clean_home(self) -> None:
        self.machine_file()
        report = lc.apply(lc.inspect_all(self.plan()))
        self.assertTrue(
            report.ok, msg=[(s.link.label, s.status, s.detail) for s in report.states]
        )
        self.assertTrue(all(s.repaired for s in report.states))

    def test_a_second_run_is_a_no_op(self) -> None:
        self.machine_file()
        lc.apply(lc.inspect_all(self.plan()))
        second = lc.inspect_all(self.plan())
        self.assertTrue(second.ok)
        self.assertFalse(any(s.repaired for s in second.states))

    def test_repairs_a_detached_copy_whose_content_matches(self) -> None:
        self.machine_file()
        link = next(l for l in self.plan() if l.label == "CLAUDE.md")
        link.dest.write_text("policy\n", encoding="utf-8")
        report = lc.apply(lc.inspect_all([link]))
        self.assertEqual(report.states[0].status, lc.LINKED)
        self.assertTrue(lc.same_target(link.source, link.dest))

    def test_refuses_a_diverged_copy_without_force(self) -> None:
        link = next(l for l in self.plan() if l.label == "CLAUDE.md")
        link.dest.write_text("older\n", encoding="utf-8")
        report = lc.apply(lc.inspect_all([link]))
        self.assertEqual(report.states[0].status, lc.DIVERGED)
        self.assertEqual(link.dest.read_text(encoding="utf-8"), "older\n")

    def test_force_replaces_a_diverged_copy(self) -> None:
        link = next(l for l in self.plan() if l.label == "CLAUDE.md")
        link.dest.write_text("older\n", encoding="utf-8")
        report = lc.apply(lc.inspect_all([link]), force=True)
        self.assertEqual(report.states[0].status, lc.LINKED)
        self.assertEqual(link.dest.read_text(encoding="utf-8"), "policy\n")

    def test_refuses_an_occupied_directory_without_force(self) -> None:
        link = next(l for l in self.plan() if l.label == "skills/review")
        link.dest.mkdir(parents=True)
        (link.dest / "mine.md").write_text("keep me", encoding="utf-8")
        report = lc.apply(lc.inspect_all([link]))
        self.assertEqual(report.states[0].status, lc.OCCUPIED)
        self.assertEqual((link.dest / "mine.md").read_text(encoding="utf-8"), "keep me")

    def test_force_still_refuses_to_delete_a_non_empty_real_directory(self) -> None:
        """--force safely replaces a junction or a stray file, but never deletes
        user data: a non-empty real directory must be cleared by hand."""
        link = next(l for l in self.plan() if l.label == "skills/review")
        link.dest.mkdir(parents=True)
        (link.dest / "mine.md").write_text("keep me", encoding="utf-8")
        report = lc.apply(lc.inspect_all([link]), force=True)
        self.assertNotEqual(report.states[0].status, lc.LINKED)
        self.assertEqual((link.dest / "mine.md").read_text(encoding="utf-8"), "keep me")
        self.assertIn("by hand", report.states[0].detail)

    def test_no_source_is_never_linked(self) -> None:
        link = next(l for l in self.plan() if l.label == "machine.md")
        report = lc.apply(lc.inspect_all([link]), force=True)
        self.assertEqual(report.states[0].status, lc.NO_SOURCE)
        self.assertFalse(link.dest.exists())

    def test_a_link_failure_is_reported_not_raised(self) -> None:
        self.machine_file()
        link = next(l for l in self.plan() if l.label == "skills/review")

        def boom(*_args, **_kwargs):
            raise OSError("no reparse points here")

        original = lc.make_link
        try:
            lc.make_link = boom
            report = lc.apply(lc.inspect_all([link]))
        finally:
            lc.make_link = original
        self.assertNotEqual(report.states[0].status, lc.LINKED)
        self.assertIn("could not link", report.states[0].detail)

    def test_a_real_directory_link_survives_inspection(self) -> None:
        self.machine_file()
        link = next(l for l in self.plan() if l.label == "skills/verify-docs")
        lc.apply(lc.inspect_all([link]))
        self.assertEqual(lc.inspect(link).status, lc.LINKED)
        self.assertTrue((link.dest / "SKILL.md").exists())


class TestClearDest(TempTree):
    def test_removing_a_directory_link_leaves_the_target_alone(self) -> None:
        self.machine_file()
        link = next(l for l in self.plan() if l.label == "skills/review")
        lc.apply(lc.inspect_all([link]))
        lc.clear_dest(lc.LinkState(link, lc.DETACHED))
        self.assertFalse(link.dest.exists())
        self.assertTrue((link.source / "SKILL.md").exists())

    def test_clearing_an_absent_destination_is_a_no_op(self) -> None:
        link = next(l for l in self.plan() if l.label == "CLAUDE.md")
        lc.clear_dest(lc.LinkState(link, lc.MISSING))  # must not raise

    def test_clearing_a_dangling_junction_removes_the_junction(self) -> None:
        link = next(l for l in self.plan() if l.label == "skills/review")
        with (
            mock.patch.object(os.path, "isjunction", return_value=True, create=True),
            mock.patch("link_config.os.rmdir") as remove,
        ):
            lc.clear_dest(lc.LinkState(link, lc.DETACHED))
        remove.assert_called_once_with(link.dest)


class TestReport(TempTree):
    def test_status_is_the_worst_of_the_set(self) -> None:
        report = lc.Report(
            [
                lc.LinkState(self.plan()[0], lc.LINKED),
                lc.LinkState(self.plan()[1], lc.DIVERGED),
                lc.LinkState(self.plan()[2], lc.MISSING),
            ]
        )
        self.assertEqual(report.status, lc.DIVERGED)

    def test_ok_only_when_everything_is_linked(self) -> None:
        links = self.plan()
        self.assertTrue(lc.Report([lc.LinkState(links[0], lc.LINKED)]).ok)
        self.assertFalse(lc.Report([lc.LinkState(links[0], lc.DETACHED)]).ok)

    def test_an_empty_report_is_not_ok_by_status(self) -> None:
        self.assertEqual(lc.Report([]).status, lc.NO_SOURCE)


class TestRender(TempTree):
    def test_table_has_a_row_per_link_plus_a_header(self) -> None:
        self.machine_file()
        report = lc.inspect_all(self.plan())
        lines = lc.render(report).splitlines()
        self.assertEqual(lines[0].count("|"), 5)
        rows = [ln for ln in lines if ln.startswith("| `")]
        self.assertEqual(len(rows), len(report.states))

    def test_names_settings_json_as_excluded(self) -> None:
        self.machine_file()
        self.assertIn("settings.json", lc.render(lc.inspect_all(self.plan())))

    def test_escapes_pipes_so_the_table_survives(self) -> None:
        link = self.plan()[0]
        report = lc.Report([lc.LinkState(link, lc.DETACHED, "a | b")])
        row = next(ln for ln in lc.render(report).splitlines() if ln.startswith("| `"))
        self.assertEqual(row.count(r"\|"), 1)

    def test_empty_detail_renders_as_a_dash(self) -> None:
        link = self.plan()[0]
        report = lc.Report([lc.LinkState(link, lc.LINKED, "")])
        row = next(ln for ln in lc.render(report).splitlines() if ln.startswith("| `"))
        self.assertIn("—", row)


class TestMain(TempTree):
    """``main()`` takes no platform override, so it derives the machine filename
    from the real host. The fixture has to match that name or the machine note
    reads as ``no_source`` and no run could ever reach ``ok``. Overriding the
    default here keeps the suite valid on Windows and macOS alike."""

    def machine_file(
        self, platform: str | None = None, hostname: str | None = None
    ) -> Path:
        return super().machine_file(
            platform or sys.platform, hostname or lc.short_hostname()
        )

    def test_reports_nonzero_when_nothing_is_linked(self) -> None:
        self.machine_file()
        code = lc.main(["--repo", str(self.repo), "--home", str(self.home)])
        self.assertEqual(code, 1)

    def test_apply_then_check_returns_zero(self) -> None:
        self.machine_file()
        lc.main(["--repo", str(self.repo), "--home", str(self.home), "--apply"])
        code = lc.main(["--repo", str(self.repo), "--home", str(self.home)])
        self.assertEqual(code, 0)

    def test_default_run_writes_nothing(self) -> None:
        self.machine_file()
        lc.main(["--repo", str(self.repo), "--home", str(self.home)])
        self.assertFalse((self.home / ".claude" / "CLAUDE.md").exists())

    def test_json_output_parses_and_lists_every_link(self) -> None:
        self.machine_file()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            lc.main(["--repo", str(self.repo), "--home", str(self.home), "--json"])
        payload = json.loads(buf.getvalue())
        self.assertEqual(len(payload["links"]), len(lc.SKILLS) + 2)
        self.assertFalse(payload["ok"])
        self.assertNotIn("settings.json", [l["dest"] for l in payload["links"]])
        self.assertEqual(payload["agents"], ["claude"])

    def test_json_names_every_requested_agent_once(self) -> None:
        self.machine_file()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            lc.main(
                [
                    "--repo",
                    str(self.repo),
                    "--home",
                    str(self.home),
                    "--json",
                    "--agent",
                    "claude",
                    "--agent",
                    "copilot",
                    "--agent",
                    "copilot",
                ]
            )
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["agents"], ["claude", "copilot"])
        self.assertEqual(len(payload["links"]), 2 * len(lc.SKILLS) + 3)

    def test_copilot_agent_writes_under_dot_copilot_plus_the_machine_note(
        self,
    ) -> None:
        self.machine_file()
        code = lc.main(
            [
                "--repo",
                str(self.repo),
                "--home",
                str(self.home),
                "--agent",
                "copilot",
                "--apply",
            ]
        )
        self.assertEqual(code, 0)
        self.assertTrue(
            (self.home / ".copilot" / "skills" / "review" / "SKILL.md").exists()
        )
        self.assertTrue((self.home / ".copilot" / "copilot-instructions.md").exists())
        self.assertTrue((self.home / ".claude" / "machine.md").exists())
        self.assertFalse((self.home / ".claude" / "CLAUDE.md").exists())
        self.assertFalse((self.home / ".claude" / "skills").exists())

    def test_an_inherited_copilot_home_cannot_redirect_a_scratch_home(self) -> None:
        elsewhere = self.base / "elsewhere"
        with mock.patch.dict(os.environ, {"COPILOT_HOME": str(elsewhere)}):
            lc.main(
                [
                    "--repo",
                    str(self.repo),
                    "--home",
                    str(self.home),
                    "--agent",
                    "copilot",
                    "--apply",
                ]
            )
        self.assertFalse(elsewhere.exists())
        self.assertTrue((self.home / ".copilot" / "skills" / "review").exists())

    def test_copilot_home_flag_wins(self) -> None:
        chosen = self.base / "chosen"
        lc.main(
            [
                "--repo",
                str(self.repo),
                "--home",
                str(self.home),
                "--agent",
                "copilot",
                "--copilot-home",
                str(chosen),
                "--apply",
            ]
        )
        self.assertTrue((chosen / "skills" / "review" / "SKILL.md").exists())
        self.assertFalse((self.home / ".copilot").exists())

    def test_persist_csv_writes_link_report_under_the_repo(self) -> None:
        self.machine_file()
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = lc.main(
                [
                    "--repo",
                    str(self.repo),
                    "--home",
                    str(self.home),
                    "--persist",
                    "--csv",
                ]
            )
        written = next(self.repo.glob("link-config-windows-*-*.csv"))
        self.assertEqual(exit_code, 1)
        self.assertTrue(written.is_file())
        self.assertTrue(
            written.read_text(encoding="utf-8").startswith(
                "Category,Artefact,Kind,Status,Detail\n"
            )
        )

    def test_persist_writes_markdown_by_default(self) -> None:
        self.machine_file()
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = lc.main(
                [
                    "--repo",
                    str(self.repo),
                    "--home",
                    str(self.home),
                    "--persist",
                ]
            )
        written = next(self.repo.glob("link-config-windows-*-*.md"))
        self.assertEqual(exit_code, 1)
        self.assertTrue(
            written.read_text(encoding="utf-8").startswith(
                "| Artefact | Kind | Status | Detail |\n"
            )
        )


class TestCopilotPlan(TempTree):
    def copilot(self, agents: tuple[str, ...] = ("copilot",)) -> list[lc.Link]:
        return lc.plan(
            self.repo,
            self.home,
            platform="win32",
            hostname="box",
            agents=agents,
            copilot_root=self.home / ".copilot",
        )

    def test_links_the_skills_and_global_instructions(self) -> None:
        self.assertEqual(
            [link.label for link in self.copilot()],
            [f"copilot/skills/{s}" for s in lc.SKILLS]
            + ["copilot/copilot-instructions.md", "machine.md"],
        )

    def test_every_destination_but_the_machine_note_is_under_the_copilot_root(
        self,
    ) -> None:
        for link in self.copilot():
            if link.label != "machine.md":
                self.assertTrue(link.dest.is_relative_to(self.home / ".copilot"))

    def test_machine_note_goes_to_the_one_fixed_path(self) -> None:
        # AGENT-INSTRUCTIONS.md names ~/.claude/machine.md for every assistant.
        link = next(l for l in self.copilot() if l.label == "machine.md")
        self.assertEqual(link.dest, self.home / ".claude" / "machine.md")

    def test_global_instructions_use_copilots_native_user_path(self) -> None:
        link = next(
            link
            for link in self.copilot()
            if link.label == "copilot/copilot-instructions.md"
        )
        self.assertEqual(
            link.source,
            self.repo / "workstation" / "agent" / "AGENT-INSTRUCTIONS.md",
        )
        self.assertEqual(link.dest, self.home / ".copilot" / "copilot-instructions.md")
        self.assertFalse(link.is_dir)

    def test_default_root_is_dot_copilot_under_home(self) -> None:
        links = lc.plan(self.repo, self.home, agents=("copilot",))
        self.assertEqual(links[0].dest.parent, self.home / ".copilot" / "skills")

    def test_shares_its_sources_with_claude(self) -> None:
        both = self.copilot(("claude", "copilot"))
        claude = {l.dest.name: l.source for l in both if l.label.startswith("skills/")}
        copilot = {
            l.dest.name: l.source for l in both if l.label.startswith("copilot/skills/")
        }
        self.assertEqual(claude, copilot)

    def test_both_agents_keep_every_directory_ahead_of_the_files(self) -> None:
        links = self.copilot(("claude", "copilot"))
        dirs = 2 * len(lc.SKILLS)
        self.assertTrue(all(link.is_dir for link in links[:dirs]))
        self.assertEqual(
            [link.label for link in links[dirs:]],
            ["copilot/copilot-instructions.md", "CLAUDE.md", "machine.md"],
        )

    def test_applies_cleanly_once_the_machine_note_exists(self) -> None:
        self.machine_file()
        report = lc.apply(lc.inspect_all(self.copilot()))
        self.assertTrue(report.ok, lc.render(report))

    def test_an_unknown_agent_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.copilot(("cursor",))


class TestProjectPlan(TempTree):
    def setUp(self) -> None:
        super().setUp()
        for name in ("beta", "alpha"):
            (self.repo / "skills" / name).mkdir(parents=True)
            (self.repo / "skills" / name / "SKILL.md").write_text(
                f"# {name}\n", encoding="utf-8"
            )
        (self.repo / "skills" / "not-a-skill").mkdir()
        (self.repo / "skills" / "README.md").write_text("index\n", encoding="utf-8")

    def project(self) -> list[lc.Link]:
        return lc.plan(self.repo, self.home, agents=(), project=True)

    def test_repo_skills_are_the_folders_holding_a_skill_md(self) -> None:
        self.assertEqual(lc.repo_skills(self.repo), ("alpha", "beta"))

    def test_no_skills_folder_means_no_skills(self) -> None:
        self.assertEqual(lc.repo_skills(self.base / "elsewhere"), ())

    def test_links_each_repo_skill_into_the_repos_own_dot_claude(self) -> None:
        links = self.project()
        self.assertEqual(
            [link.label for link in links],
            ["project/skills/alpha", "project/skills/beta"],
        )
        for link in links:
            self.assertEqual(link.dest.parent, self.repo / ".claude" / "skills")
            self.assertTrue(link.is_dir)

    def test_project_alone_reaches_ok_and_leaves_home_alone(self) -> None:
        report = lc.apply(lc.inspect_all(self.project()))
        self.assertTrue(report.ok, lc.render(report))
        self.assertFalse((self.home / ".claude" / "skills").exists())
        self.assertTrue(
            (self.repo / ".claude" / "skills" / "alpha" / "SKILL.md").exists()
        )

    @unittest.skipIf(os.name == "nt", "creating a symlink on Windows needs elevation")
    def test_a_hand_made_relative_link_counts_as_linked(self) -> None:
        """skills/README.md used to give `ln -s ../../skills/<name>`; those must not be redone."""
        link = self.project()[0]
        link.dest.parent.mkdir(parents=True)
        os.symlink("../../skills/alpha", link.dest)
        self.assertEqual(lc.inspect(link).status, lc.LINKED)

    def test_main_with_project_alone_links_only_the_repo_skills(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = lc.main(
                [
                    "--repo",
                    str(self.repo),
                    "--home",
                    str(self.home),
                    "--project",
                    "--apply",
                    "--json",
                ]
            )
        payload = json.loads(buf.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual((payload["agents"], payload["project"]), ([], True))
        self.assertFalse((self.home / ".claude" / "CLAUDE.md").exists())
        self.assertFalse((self.repo / "CLAUDE.md").exists())


class TestClaudeMd(TempTree):
    """The per-clone CLAUDE.md: generated, never tracked, never linked."""

    def setUp(self) -> None:
        super().setUp()
        (self.repo / "AGENTS.md").write_text("# repo rules\n", encoding="utf-8")

    def link(self) -> lc.Link:
        links = lc.plan(self.repo, self.home, agents=(), claude_md=True)
        self.assertEqual([link.label for link in links], ["project/CLAUDE.md"])
        return links[0]

    def test_absent_reads_missing_and_apply_writes_the_import(self) -> None:
        self.assertEqual(lc.inspect(self.link()).status, lc.MISSING)
        report = lc.apply(lc.inspect_all([self.link()]))
        self.assertTrue(report.ok, lc.render(report))
        self.assertEqual((self.repo / "CLAUDE.md").read_bytes(), b"@AGENTS.md\n")
        self.assertEqual(lc.inspect(self.link()).status, lc.LINKED)

    def test_a_file_with_other_content_is_diverged_and_kept(self) -> None:
        (self.repo / "CLAUDE.md").write_text("my own notes\n", encoding="utf-8")
        report = lc.apply(lc.inspect_all([self.link()]))
        self.assertEqual(report.status, lc.DIVERGED)
        self.assertEqual(
            (self.repo / "CLAUDE.md").read_text(encoding="utf-8"), "my own notes\n"
        )

    def test_force_replaces_diverged_content(self) -> None:
        (self.repo / "CLAUDE.md").write_text("my own notes\n", encoding="utf-8")
        report = lc.apply(lc.inspect_all([self.link()]), force=True)
        self.assertTrue(report.ok, lc.render(report))
        self.assertEqual((self.repo / "CLAUDE.md").read_bytes(), b"@AGENTS.md\n")

    def test_no_agents_md_is_no_source(self) -> None:
        (self.repo / "AGENTS.md").unlink()
        self.assertEqual(lc.inspect(self.link()).status, lc.NO_SOURCE)

    def test_main_with_claude_md_alone_leaves_home_alone(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = lc.main(
                [
                    "--repo",
                    str(self.repo),
                    "--home",
                    str(self.home),
                    "--claude-md",
                    "--apply",
                    "--json",
                ]
            )
        payload = json.loads(buf.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual((payload["agents"], payload["claude_md"]), ([], True))
        self.assertTrue((self.repo / "CLAUDE.md").exists())
        self.assertEqual(list((self.home / ".claude").iterdir()), [])


class TestHooks(TempTree):
    """Post-edit hooks: opt-in, linked per agent, registration JSON only for Copilot."""

    def setUp(self) -> None:
        super().setUp()
        hooks = self.repo / "workstation" / "agent" / "hooks"
        hooks.mkdir()
        (hooks / "ruff_on_edit.py").write_text("# hook\n", encoding="utf-8")
        (hooks / "ruff-on-edit.copilot.json").write_text("{}\n", encoding="utf-8")

    def hook_links(self, agents: tuple[str, ...], hooks: bool = True) -> list[lc.Link]:
        links = lc.plan(
            self.repo,
            self.home,
            platform="win32",
            hostname="box",
            agents=agents,
            copilot_root=self.home / ".copilot",
            hooks=hooks,
        )
        return [link for link in links if "hooks/" in link.label]

    def test_off_by_default(self) -> None:
        self.assertEqual(self.hook_links(("claude", "copilot"), hooks=False), [])

    def test_claude_gets_the_script_only(self) -> None:
        [link] = self.hook_links(("claude",))
        self.assertEqual(link.dest, self.home / ".claude" / "hooks" / "ruff_on_edit.py")

    def test_copilot_gets_the_script_and_its_registration(self) -> None:
        dests = {link.dest for link in self.hook_links(("copilot",))}
        root = self.home / ".copilot" / "hooks"
        self.assertEqual(dests, {root / "ruff_on_edit.py", root / "ruff-on-edit.json"})

    def test_files_come_after_every_directory(self) -> None:
        links = lc.plan(
            self.repo,
            self.home,
            platform="win32",
            hostname="box",
            agents=("claude", "copilot"),
            copilot_root=self.home / ".copilot",
            hooks=True,
        )
        first_file = next(i for i, link in enumerate(links) if not link.is_dir)
        self.assertFalse(any(link.is_dir for link in links[first_file:]))

    def test_apply_links_them(self) -> None:
        report = lc.apply(lc.inspect_all(self.hook_links(("claude", "copilot"))))
        self.assertTrue(report.ok, lc.render(report))
        self.assertTrue(
            (self.home / ".copilot" / "hooks" / "ruff-on-edit.json").exists()
        )


class TestCopilotHome(unittest.TestCase):
    def test_copilot_home_wins_for_the_real_home(self) -> None:
        self.assertEqual(
            lc.copilot_home(
                Path("/h"), {"COPILOT_HOME": "/c"}, default_home=Path("/h")
            ),
            Path("/c"),
        )

    def test_copilot_home_is_ignored_for_any_other_home(self) -> None:
        self.assertEqual(
            lc.copilot_home(
                Path("/scratch"), {"COPILOT_HOME": "/c"}, default_home=Path("/h")
            ),
            Path("/scratch/.copilot"),
        )

    def test_unset_falls_back_to_dot_copilot(self) -> None:
        self.assertEqual(
            lc.copilot_home(Path("/h"), {}, default_home=Path("/h")),
            Path("/h/.copilot"),
        )


class TestMachineFile(TempTree):
    """Resolution order, so a machine file need not be named after a hostname."""

    def resolve(
        self,
        platform: str = "darwin",
        hostname: str = "box",
        machine: str | None = None,
    ) -> Path:
        return lc.machine_file(self.repo, platform, hostname, machine)

    def test_explicit_machine_wins_over_everything(self) -> None:
        self.machine_file("darwin", "box")
        self.assertEqual(self.resolve(machine="macos-chosen").name, "macos-chosen.md")

    def test_explicit_machine_accepts_a_name_that_already_ends_in_md(self) -> None:
        self.assertEqual(
            self.resolve(machine="macos-chosen.md").name, "macos-chosen.md"
        )

    def test_the_conventional_name_is_used_when_it_exists(self) -> None:
        self.machine_file("darwin", "box")
        self.assertEqual(self.resolve().name, "macos-box.md")

    def test_the_only_file_for_this_platform_is_used_when_the_host_does_not_match(
        self,
    ) -> None:
        self.machine_file("darwin", "workstation")
        self.assertEqual(
            self.resolve(hostname="unmatched").name, "macos-workstation.md"
        )

    def test_another_platforms_file_is_never_borrowed(self) -> None:
        self.machine_file("win32", "some-pc")
        self.assertEqual(self.resolve(hostname="unmatched").name, "macos-unmatched.md")

    def test_two_candidates_and_no_host_match_is_not_guessed_at(self) -> None:
        self.machine_file("darwin", "one")
        self.machine_file("darwin", "two")
        resolved = self.resolve(hostname="unmatched")
        self.assertEqual(resolved.name, "macos-unmatched.md")
        self.assertFalse(resolved.exists())


@unittest.skipIf(os.name == "nt", "creating a symlink on Windows needs elevation")
class TestDanglingSymlink(TempTree):
    """A symlink whose target has been renamed away.

    This repo's config moved from ``workstation-agent/`` to
    ``workstation/agent/``, so it is the state a macOS box carrying links from
    that era is actually in. ``Path.exists()`` follows the link and reports
    ``False``, but the entry is there and blocks ``os.symlink``.
    """

    def dangle(self, label: str) -> lc.Link:
        self.machine_file()
        link = next(l for l in self.plan() if l.label == label)
        link.dest.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(self.repo / "gone" / link.dest.name, link.dest)
        return link

    def test_a_dangling_file_link_is_detached_not_missing(self) -> None:
        link = self.dangle("CLAUDE.md")
        state = lc.inspect(link)
        self.assertEqual(state.status, lc.DETACHED)
        self.assertIn("dangling symlink", state.detail)

    def test_the_detail_names_the_stale_target(self) -> None:
        state = lc.inspect(self.dangle("CLAUDE.md"))
        self.assertIn("gone", state.detail)

    def test_a_dangling_directory_link_is_detached_too(self) -> None:
        self.assertEqual(lc.inspect(self.dangle("skills/review")).status, lc.DETACHED)

    def test_clear_dest_removes_it(self) -> None:
        link = self.dangle("CLAUDE.md")
        lc.clear_dest(lc.LinkState(link, lc.DETACHED))
        self.assertFalse(link.dest.is_symlink())

    def test_apply_repairs_it_rather_than_raising_file_exists(self) -> None:
        link = self.dangle("CLAUDE.md")
        state = lc.apply(lc.inspect_all([link])).states[0]
        self.assertEqual(state.status, lc.LINKED, state.detail)
        self.assertTrue(lc.same_target(link.source, link.dest))

    def test_apply_repairs_a_dangling_directory_link(self) -> None:
        link = self.dangle("skills/review")
        state = lc.apply(lc.inspect_all([link])).states[0]
        self.assertEqual(state.status, lc.LINKED, state.detail)
        self.assertTrue((link.dest / "SKILL.md").exists())

    def test_a_whole_dangling_home_reaches_ok(self) -> None:
        self.dangle("CLAUDE.md")
        self.dangle("skills/review")
        report = lc.apply(lc.inspect_all(self.plan()))
        self.assertTrue(report.ok, lc.render(report))


class TestMcp(TempTree):
    """The catalog is merged into ``<repo>/.mcp.json``, never linked."""

    def catalog(self, servers: dict) -> Path:
        path = lc.mcp_catalog_path(self.repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"mcpServers": servers}, indent=2), encoding="utf-8")
        return path

    def live(self, servers: dict) -> Path:
        path = lc.project_mcp_path(self.repo)
        path.write_text(json.dumps({"mcpServers": servers}, indent=2), encoding="utf-8")
        return path

    def test_no_catalog_is_an_empty_status_not_an_error(self) -> None:
        self.assertEqual(lc.mcp_status(self.repo), [])

    def test_missing_from_the_live_file(self) -> None:
        self.catalog({"drawio-mcp": {"type": "stdio", "command": "npx"}})
        (states,) = lc.mcp_status(self.repo)
        self.assertEqual(states.status, lc.MISSING)

    def test_matching_value_is_linked(self) -> None:
        entry = {"type": "stdio", "command": "npx"}
        self.catalog({"drawio-mcp": entry})
        self.live({"drawio-mcp": entry})
        (state,) = lc.mcp_status(self.repo)
        self.assertEqual(state.status, lc.LINKED)

    def test_different_value_is_diverged(self) -> None:
        self.catalog({"drawio-mcp": {"type": "stdio", "command": "npx"}})
        self.live({"drawio-mcp": {"type": "stdio", "command": "node"}})
        (state,) = lc.mcp_status(self.repo)
        self.assertEqual(state.status, lc.DIVERGED)

    def test_a_live_only_server_is_not_in_the_report(self) -> None:
        self.catalog({"drawio-mcp": {"type": "stdio", "command": "npx"}})
        self.live({"personal-tool": {"type": "stdio", "command": "whatever"}})
        names = [s.name for s in lc.mcp_status(self.repo)]
        self.assertEqual(names, ["drawio-mcp"])

    def test_apply_adds_missing_entries_and_preserves_live_only_ones(self) -> None:
        self.catalog({"drawio-mcp": {"type": "stdio", "command": "npx"}})
        self.live({"personal-tool": {"type": "stdio", "command": "whatever"}})
        lc.apply_mcp(self.repo)
        servers = lc.load_mcp_servers(lc.project_mcp_path(self.repo))
        self.assertEqual(
            servers,
            {
                "personal-tool": {"type": "stdio", "command": "whatever"},
                "drawio-mcp": {"type": "stdio", "command": "npx"},
            },
        )

    def test_apply_skips_a_diverged_entry(self) -> None:
        self.catalog({"drawio-mcp": {"type": "stdio", "command": "npx"}})
        self.live({"drawio-mcp": {"type": "stdio", "command": "node"}})
        lc.apply_mcp(self.repo)
        servers = lc.load_mcp_servers(lc.project_mcp_path(self.repo))
        self.assertEqual(servers["drawio-mcp"]["command"], "node")

    def test_apply_creates_the_file_when_absent(self) -> None:
        self.catalog({"drawio-mcp": {"type": "stdio", "command": "npx"}})
        self.assertFalse(lc.project_mcp_path(self.repo).is_file())
        lc.apply_mcp(self.repo)
        self.assertTrue(lc.project_mcp_path(self.repo).is_file())

    def test_apply_writes_nothing_when_already_all_linked(self) -> None:
        entry = {"type": "stdio", "command": "npx"}
        self.catalog({"drawio-mcp": entry})
        path = self.live({"drawio-mcp": entry})
        before = path.stat().st_mtime_ns
        lc.apply_mcp(self.repo)
        self.assertEqual(path.stat().st_mtime_ns, before)

    def test_main_mcp_flag_reports_and_applies(self) -> None:
        self.machine_file(sys.platform, lc.short_hostname())
        self.catalog({"drawio-mcp": {"type": "stdio", "command": "npx"}})
        code = lc.main(["--repo", str(self.repo), "--home", str(self.home), "--mcp"])
        self.assertEqual(code, 1)
        self.assertFalse(lc.project_mcp_path(self.repo).is_file())
        code = lc.main(
            ["--repo", str(self.repo), "--home", str(self.home), "--mcp", "--apply"]
        )
        self.assertEqual(code, 0)
        self.assertTrue(lc.project_mcp_path(self.repo).is_file())

    def test_main_mcp_json_output(self) -> None:
        self.catalog({"drawio-mcp": {"type": "stdio", "command": "npx"}})
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            lc.main(["--repo", str(self.repo), "--mcp", "--json"])
        payload = json.loads(buf.getvalue())
        self.assertEqual(
            payload["mcp_servers"],
            [{"name": "drawio-mcp", "status": "missing", "detail": "not in .mcp.json"}],
        )
        self.assertFalse(payload["ok"])

    def test_without_mcp_flag_the_project_file_is_untouched(self) -> None:
        self.machine_file(sys.platform, lc.short_hostname())
        self.catalog({"drawio-mcp": {"type": "stdio", "command": "npx"}})
        lc.main(
            ["--repo", str(self.repo), "--home", str(self.home), "--project", "--apply"]
        )
        self.assertFalse(lc.project_mcp_path(self.repo).is_file())


if __name__ == "__main__":
    unittest.main()
