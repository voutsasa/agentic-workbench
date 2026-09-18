"""Unit tests for the ruff post-edit hook. Standard library only:

python -m unittest discover -s workstation/agent/hooks/tests -t workstation/agent/hooks/tests
"""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ruff_on_edit as hook


class TestEditedPath(unittest.TestCase):
    def test_claude_payload(self):
        payload = {"tool_input": {"file_path": "/repo/a.py"}}
        self.assertEqual(hook.edited_path(payload), Path("/repo/a.py"))

    def test_copilot_payload_as_object(self):
        payload = {"toolArgs": {"path": "/repo/a.py"}, "cwd": "/repo"}
        self.assertEqual(hook.edited_path(payload), Path("/repo/a.py"))

    def test_copilot_payload_as_json_string(self):
        payload = {"toolArgs": json.dumps({"path": "a.py"}), "cwd": "/repo"}
        self.assertEqual(hook.edited_path(payload), Path("/repo/a.py"))

    def test_relative_path_resolves_against_cwd(self):
        payload = {"tool_input": {"file_path": "pkg/a.py"}, "cwd": "/repo"}
        self.assertEqual(hook.edited_path(payload), Path("/repo/pkg/a.py"))

    def test_no_path_is_none(self):
        self.assertIsNone(hook.edited_path({"tool_input": {"command": "ls"}}))
        self.assertIsNone(hook.edited_path({"toolArgs": "not json"}))
        self.assertIsNone(hook.edited_path({}))


class TestMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bin = self.root / ".venv" / "bin"
        self.bin.mkdir(parents=True)
        self.python = self.bin / "python"
        (self.bin / ("ruff.exe" if hook.os.name == "nt" else "ruff")).touch()
        self.file = self.root / "a.py"
        self.file.write_text("x=1\n")
        self.runner = mock.Mock(return_value=mock.Mock(returncode=0))

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, payload) -> int:
        stdin = io.StringIO(json.dumps(payload))
        return hook.main(stdin, str(self.python), self.runner)

    def test_fixes_then_formats_a_python_file(self):
        # Fix first: a removed import leaves a blank line only format cleans up.
        status = self.call({"tool_input": {"file_path": str(self.file)}})
        self.assertEqual(status, 0)
        commands = [c.args[0][1:] for c in self.runner.call_args_list]
        self.assertEqual(
            commands, [["check", "--fix", str(self.file)], ["format", str(self.file)]]
        )

    def test_uses_the_ruff_beside_the_interpreter(self):
        self.call({"tool_input": {"file_path": str(self.file)}})
        self.assertEqual(Path(self.runner.call_args.args[0][0]).parent, self.bin)

    def test_skips_a_non_python_file(self):
        md = self.root / "a.md"
        md.touch()
        self.assertEqual(self.call({"tool_input": {"file_path": str(md)}}), 0)
        self.runner.assert_not_called()

    def test_skips_when_no_ruff_is_installed(self):
        for ruff in self.bin.glob("ruff*"):
            ruff.unlink()
        self.assertEqual(self.call({"tool_input": {"file_path": str(self.file)}}), 0)
        self.runner.assert_not_called()

    def test_skips_a_deleted_file(self):
        self.file.unlink()
        self.call({"tool_input": {"file_path": str(self.file)}})
        self.runner.assert_not_called()

    def test_reports_an_unfixable_violation(self):
        self.runner.side_effect = [mock.Mock(returncode=1), mock.Mock(returncode=0)]
        self.assertEqual(self.call({"tool_input": {"file_path": str(self.file)}}), 1)

    def test_malformed_stdin_is_ignored(self):
        self.assertEqual(hook.main(io.StringIO("{"), str(self.python), self.runner), 0)
        self.runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
