"""Unit tests for `settings_delta.py`.

Run from the repo root::

    python -m unittest discover -s workstation/scripts/tests -t workstation/scripts/tests
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import settings_delta
from settings_delta import delta, env_report

REFERENCE = {
    "model": "opus",
    "permissions": {"defaultMode": "auto", "allow": ["Bash(git status)"]},
    "hooks": {"PostToolUse": [{"matcher": "Edit|Write"}]},
}


class Delta(unittest.TestCase):
    def test_identical_files_are_in_sync(self) -> None:
        self.assertEqual(delta(REFERENCE, json.loads(json.dumps(REFERENCE))), [])

    def test_absent_top_level_key_is_reported_whole(self) -> None:
        live = {k: v for k, v in REFERENCE.items() if k != "hooks"}
        self.assertEqual(delta(REFERENCE, live), [("hooks", REFERENCE["hooks"])])

    def test_object_member_is_reported_alone(self) -> None:
        live = dict(
            REFERENCE,
            permissions={"defaultMode": "default", "allow": ["Bash(git status)"]},
        )
        self.assertEqual(delta(REFERENCE, live), [("permissions.defaultMode", "auto")])

    def test_extra_live_list_items_are_not_drift(self) -> None:
        live = dict(
            REFERENCE,
            permissions={
                "defaultMode": "auto",
                "allow": ["Bash(git status)", "Bash(ls)"],
            },
        )
        self.assertEqual(delta(REFERENCE, live), [])

    def test_list_reports_only_missing_items(self) -> None:
        ref = {"permissions": {"allow": ["a", "b"]}}
        live = {"permissions": {"allow": ["b", "c"]}}
        self.assertEqual(delta(ref, live), [("permissions.allow", ["a"])])

    def test_env_is_never_compared(self) -> None:
        self.assertEqual(delta({"env": {"X": "1"}}, {}), [])

    def test_scalar_where_object_expected_is_reported_whole(self) -> None:
        live = dict(REFERENCE, permissions="oops")
        self.assertEqual(
            delta(REFERENCE, live), [("permissions", REFERENCE["permissions"])]
        )


class EnvReport(unittest.TestCase):
    def test_prints_key_names_not_values(self) -> None:
        live = {
            "model": "opus",
            "env": {"AWS_PROFILE": "secret-profile", "CLAUDE_CODE_USE_BEDROCK": "1"},
        }
        text = "\n".join(env_report(live))
        self.assertIn("['AWS_PROFILE', 'CLAUDE_CODE_USE_BEDROCK']", text)
        self.assertNotIn("secret-profile", text)
        self.assertRegex(text, r"CLAUDE_CODE_USE_BEDROCK +: 1")

    def test_subscription_machine_has_no_env(self) -> None:
        text = "\n".join(env_report({"model": "opus"}))
        self.assertRegex(text, r"env keys +: \[\]")
        self.assertRegex(text, r"CLAUDE_CODE_USE_BEDROCK +: None")

    def test_labels_align(self) -> None:
        lines = env_report({"model": "opus"})[1:]
        self.assertEqual(len({line.index(" : ") for line in lines}), 1)


class Main(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.home = self.root / "home"
        self.repo = self.root / "repo"
        (self.home / ".claude").mkdir(parents=True)
        ref = self.repo / settings_delta.REFERENCE
        ref.parent.mkdir(parents=True)
        ref.write_text(json.dumps(REFERENCE), encoding="utf-8")
        self.live = self.home / ".claude" / "settings.json"

    def run_main(self, *extra: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = settings_delta.main(
                ["--home", str(self.home), "--repo", str(self.repo), *extra]
            )
        return code, out.getvalue(), err.getvalue()

    def test_in_sync_exits_zero(self) -> None:
        self.live.write_text(json.dumps(REFERENCE), encoding="utf-8")
        self.assertEqual(self.run_main()[:2], (0, "in sync\n"))

    def test_delta_exits_one_and_prints_add_lines(self) -> None:
        self.live.write_text(json.dumps({"model": "opus"}), encoding="utf-8")
        code, out, _ = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn('add permissions: {"defaultMode": "auto"', out)
        self.assertIn("add hooks: ", out)

    def test_missing_live_file_exits_two(self) -> None:
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_invalid_json_exits_two(self) -> None:
        self.live.write_text('{"model": "opus",}', encoding="utf-8")
        self.assertEqual(self.run_main("--env")[0], 2)

    def test_env_mode_needs_no_reference(self) -> None:
        self.live.write_text(json.dumps({"model": "opus"}), encoding="utf-8")
        (self.repo / settings_delta.REFERENCE).unlink()
        code, out, _ = self.run_main("--env")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("valid JSON\n"))

    def test_never_writes_either_file(self) -> None:
        self.live.write_text(json.dumps({"model": "opus"}), encoding="utf-8")
        before = self.live.read_bytes()
        self.run_main()
        self.run_main("--env")
        self.assertEqual(self.live.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
