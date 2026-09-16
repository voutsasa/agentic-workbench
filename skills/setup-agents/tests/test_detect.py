"""Unit tests for detect.py — stdlib only, no real probes, no real home.

python3 -m unittest discover -s skills/setup-agents/tests
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# E402: sys.path has to be extended before this import, so it cannot move to the top.
import detect
import link_config


def completed(stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], 0, stdout, stderr)


def build_repo(root: Path) -> Path:
    agent = root / "workstation" / "agent"
    for skill in link_config.SKILLS:
        (agent / "skills" / skill).mkdir(parents=True)
        (agent / "skills" / skill / "SKILL.md").write_text(
            f"# {skill}\n", encoding="utf-8"
        )
    (agent / "AGENT-INSTRUCTIONS.md").write_text("policy\n", encoding="utf-8")
    (agent / "settings.json").write_text(
        json.dumps({"model": "opus", "fastMode": False}), encoding="utf-8"
    )
    (root / "workstation" / "machines").mkdir(parents=True)
    return root


class TempTree(unittest.TestCase):
    def setUp(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.repo = build_repo(self.base / "repo")
        self.home = self.base / "home"
        (self.home / ".claude").mkdir(parents=True)

    def live_settings(self, data: dict | str) -> None:
        text = data if isinstance(data, str) else json.dumps(data)
        (self.home / ".claude" / "settings.json").write_text(text, encoding="utf-8")


class TestProbe(unittest.TestCase):
    spec = detect.Spec("copilot", "GitHub Copilot CLI", "copilot", True)

    def test_absent_command_is_not_run(self) -> None:
        run = mock.Mock()
        found = detect.probe(self.spec, which=lambda _: None, run=run)
        self.assertIsNone(found.path)
        self.assertEqual(found.detail, "not on PATH")
        run.assert_not_called()

    def test_reads_the_first_dotted_number(self) -> None:
        found = detect.probe(
            self.spec,
            which=lambda _: "/bin/copilot",
            run=lambda *a, **k: completed("GitHub Copilot CLI 1.0.63.\n"),
        )
        self.assertEqual(found.version, "1.0.63")

    def test_version_on_stderr_counts(self) -> None:
        found = detect.probe(
            self.spec,
            which=lambda _: "/bin/x",
            run=lambda *a, **k: completed("", "x 2.1\n"),
        )
        self.assertEqual(found.version, "2.1")

    def test_a_probe_that_cannot_launch_is_reported_not_raised(self) -> None:
        def boom(*_a, **_k):
            raise OSError("quarantined")

        found = detect.probe(self.spec, which=lambda _: "/bin/x", run=boom)
        self.assertEqual(found.path, "/bin/x")
        self.assertIn("OSError", found.detail)

    def test_a_timeout_is_reported_not_raised(self) -> None:
        def slow(*_a, **_k):
            raise subprocess.TimeoutExpired("x", 15)

        found = detect.probe(self.spec, which=lambda _: "/bin/x", run=slow)
        self.assertIn("TimeoutExpired", found.detail)

    def test_output_without_a_version(self) -> None:
        found = detect.probe(
            self.spec,
            which=lambda _: "/bin/x",
            run=lambda *a, **k: completed("usage: x\n"),
        )
        self.assertIsNone(found.version)
        self.assertIn("no version", found.detail)


class TestClaudeProvider(TempTree):
    def test_no_settings_and_no_env_is_subscription_or_unset(self) -> None:
        result = detect.claude_provider(self.home, {})
        self.assertEqual(result["provider"], "subscription-or-unset")
        self.assertEqual(result["settings_state"], "absent")

    def test_bedrock_in_the_settings_env_block(self) -> None:
        self.live_settings(
            {"env": {"CLAUDE_CODE_USE_BEDROCK": "1", "AWS_PROFILE": "p"}}
        )
        result = detect.claude_provider(self.home, {})
        self.assertEqual(result["provider"], "bedrock")
        self.assertEqual(
            result["set_vars"], {"CLAUDE_CODE_USE_BEDROCK": "settings.json env"}
        )

    def test_bedrock_in_the_process_environment(self) -> None:
        result = detect.claude_provider(self.home, {"CLAUDE_CODE_USE_BEDROCK": "true"})
        self.assertEqual(result["provider"], "bedrock")
        self.assertEqual(
            result["set_vars"]["CLAUDE_CODE_USE_BEDROCK"], "process environment"
        )

    def test_a_switch_set_to_zero_is_off(self) -> None:
        self.live_settings({"env": {"CLAUDE_CODE_USE_BEDROCK": "0"}})
        self.assertEqual(
            detect.claude_provider(self.home, {})["provider"], "subscription-or-unset"
        )

    def test_bedrock_outranks_an_api_key(self) -> None:
        result = detect.claude_provider(
            self.home, {"ANTHROPIC_API_KEY": "sk-x", "CLAUDE_CODE_USE_BEDROCK": "1"}
        )
        self.assertEqual(result["provider"], "bedrock")

    def test_an_api_key_value_never_reaches_the_output(self) -> None:
        result = detect.claude_provider(
            self.home, {"ANTHROPIC_API_KEY": "sk-secret-123"}
        )
        self.assertEqual(result["provider"], "api-key")
        self.assertNotIn("sk-secret-123", json.dumps(result))

    def test_unreadable_settings_are_reported(self) -> None:
        self.live_settings("{not json")
        result = detect.claude_provider(self.home, {})
        self.assertTrue(result["settings_state"].startswith("unreadable"))


class TestSettingsDrift(TempTree):
    def test_lists_only_the_keys_that_differ(self) -> None:
        self.live_settings({"model": "opus", "fastMode": True, "env": {"X": "1"}})
        self.assertEqual(
            detect.settings_drift(self.home, self.repo)["differs"], ["fastMode"]
        )

    def test_a_key_missing_live_differs(self) -> None:
        self.live_settings({"model": "opus"})
        self.assertEqual(
            detect.settings_drift(self.home, self.repo)["differs"], ["fastMode"]
        )

    def test_env_is_never_compared(self) -> None:
        ref = self.repo / "workstation" / "agent" / "settings.json"
        ref.write_text(json.dumps({"env": {"A": "1"}}), encoding="utf-8")
        self.live_settings({})
        self.assertEqual(detect.settings_drift(self.home, self.repo)["differs"], [])

    def test_absent_live_file_is_named(self) -> None:
        self.assertEqual(detect.settings_drift(self.home, self.repo)["live"], "absent")


class TestVSCode(TempTree):
    def test_macos_user_settings_path(self) -> None:
        path = detect.vscode_user_settings("darwin", Path("/Users/u"), {})
        self.assertEqual(
            path, Path("/Users/u/Library/Application Support/Code/User/settings.json")
        )

    def test_windows_uses_appdata(self) -> None:
        path = detect.vscode_user_settings("win32", Path("/h"), {"APPDATA": "/appdata"})
        self.assertEqual(path, Path("/appdata/Code/User/settings.json"))

    def test_windows_without_appdata_and_linux_have_no_route(self) -> None:
        self.assertIsNone(detect.vscode_user_settings("win32", Path("/h"), {}))
        self.assertIsNone(detect.vscode_user_settings("linux", Path("/h"), {}))

    def write(self, text: str) -> Path:
        path = self.base / "settings.json"
        path.write_text(text, encoding="utf-8")
        return path

    def test_reads_true_and_false(self) -> None:
        self.assertTrue(
            detect.jsonc_flag(
                self.write('{ "chat.useClaudeMdFile": true, }'), "chat.useClaudeMdFile"
            )
        )
        self.assertFalse(
            detect.jsonc_flag(
                self.write('{"chat.useClaudeMdFile":false}'), "chat.useClaudeMdFile"
            )
        )

    def test_a_commented_out_line_is_not_a_setting(self) -> None:
        path = self.write('{\n  // "chat.useClaudeMdFile": true,\n  "a": 1\n}')
        self.assertIsNone(detect.jsonc_flag(path, "chat.useClaudeMdFile"))

    def test_a_longer_key_with_the_same_prefix_does_not_match(self) -> None:
        path = self.write('{"chat.useClaudeMdFileX": true}')
        self.assertIsNone(detect.jsonc_flag(path, "chat.useClaudeMdFile"))

    def test_missing_file_and_no_path_are_unset(self) -> None:
        self.assertIsNone(detect.jsonc_flag(self.base / "nope.json", "k"))
        self.assertIsNone(detect.jsonc_flag(None, "k"))


class TestCollect(TempTree):
    def facts(self, on_path: dict[str, str]) -> dict:
        return detect.collect(
            self.repo,
            self.home,
            environ={},
            platform="darwin",
            hostname="box",
            which=on_path.get,
            run=lambda *a, **k: completed("tool 1.2.3\n"),
        )

    def test_splits_configurable_from_report_only(self) -> None:
        facts = self.facts({"claude": "/bin/claude", "gemini": "/bin/gemini"})
        found = {a["id"]: a["configurable"] for a in facts["assistants"] if a["path"]}
        self.assertEqual(found, {"claude": True, "gemini": False})

    def test_every_known_assistant_is_listed_found_or_not(self) -> None:
        facts = self.facts({})
        self.assertEqual(
            [a["id"] for a in facts["assistants"]], [s.id for s in detect.ASSISTANTS]
        )

    def test_link_counts_for_both_agents_from_a_clean_home(self) -> None:
        facts = self.facts({})
        self.assertEqual(facts["claude"]["links"]["linked"], 0)
        self.assertEqual(facts["claude"]["links"]["total"], len(link_config.SKILLS) + 2)
        self.assertEqual(facts["copilot"]["links"]["total"], len(link_config.SKILLS))

    def test_reports_the_machine_note_as_absent_by_its_conventional_name(self) -> None:
        machine = self.facts({})["machine"]
        self.assertEqual(machine["machine_note"], "workstation/machines/macos-box.md")
        self.assertFalse(machine["machine_note_exists"])

    def test_counts_this_repos_own_skills_for_the_project_links(self) -> None:
        (self.repo / "skills" / "mine").mkdir(parents=True)
        (self.repo / "skills" / "mine" / "SKILL.md").write_text(
            "# mine\n", encoding="utf-8"
        )
        links = self.facts({})["project"]["links"]
        self.assertEqual((links["linked"], links["total"]), (0, 1))

    def test_writes_nothing(self) -> None:
        before = sorted(p for p in self.base.rglob("*"))
        self.facts({"claude": "/bin/claude", "copilot": "/bin/copilot"})
        self.assertEqual(sorted(p for p in self.base.rglob("*")), before)


class TestRender(TempTree):
    def rendered(self, on_path: dict[str, str]) -> str:
        facts = detect.collect(
            self.repo,
            self.home,
            environ={},
            platform="darwin",
            hostname="box",
            which=on_path.get,
            run=lambda *a, **k: completed("x 1.0.0"),
        )
        return detect.render(facts, self.home)

    def test_marks_report_only_assistants(self) -> None:
        self.assertIn("report only", self.rendered({"gemini": "/bin/gemini"}))

    def test_names_what_is_not_on_path(self) -> None:
        self.assertIn("Not on PATH:", self.rendered({}))
        self.assertIn("`codex`", self.rendered({}))

    def test_flags_an_absent_machine_note(self) -> None:
        self.assertIn("**absent**", self.rendered({}))


class TestMain(TempTree):
    def test_json_parses_and_writes_nothing(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(detect.shutil, "which", return_value=None),
            contextlib.redirect_stdout(buf),
        ):
            code = detect.main(
                ["--repo", str(self.repo), "--home", str(self.home), "--json"]
            )
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(
            set(payload),
            {"machine", "assistants", "claude", "copilot", "project", "vscode"},
        )
        self.assertFalse((self.home / ".claude" / "CLAUDE.md").exists())


if __name__ == "__main__":
    unittest.main()
