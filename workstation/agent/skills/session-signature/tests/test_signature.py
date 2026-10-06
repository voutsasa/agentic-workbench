import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import signature

ATTRS = {
    "workstation": "H",
    "username": "u",
    "harness": "claude-cli-2.1.291",
    "agent": "agentic-workbench-0.1.0",
    "model": "m",
    "timestamp": "20261006T100816Z",
}


class SignatureTests(unittest.TestCase):
    def test_id_follows_recorded_order(self):
        self.assertEqual(
            signature.ID_FIELDS,
            ("workstation", "username", "harness", "agent", "model", "timestamp"),
        )
        sig = signature.build(ATTRS)["signature"]
        self.assertEqual(
            sig["id"],
            "H_u_claude-cli-2.1.291_agentic-workbench-0.1.0_m_20261006T100816Z",
        )
        self.assertEqual(list(sig)[1:], list(signature.ID_FIELDS))

    def test_skill_table_matches_id_fields(self):
        skill = Path(__file__).resolve().parents[1] / "SKILL.md"
        rows = re.findall(
            r"^\| \d+ \| `(\w+)` \|", skill.read_text("utf-8"), re.MULTILINE
        )
        self.assertEqual(tuple(rows), signature.ID_FIELDS)

    def test_timestamp_is_compact_utc(self):
        now = datetime(2026, 10, 6, 10, 8, 16, tzinfo=UTC)
        self.assertEqual(signature.timestamp(now), "20261006T100816Z")

    def test_agent_version_reads_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "plugin.json"
            manifest.write_text('{"version": "9.9.9"}', encoding="utf-8")
            self.assertEqual(
                signature.agent_version(manifest), "agentic-workbench-9.9.9"
            )

    def test_real_manifest_exists(self):
        self.assertTrue(signature.PLUGIN_MANIFEST.is_file())

    def _probe(self, label, stdout, command=None):
        done = mock.Mock(stdout=stdout)
        with (
            mock.patch.object(signature.shutil, "which", return_value="x") as which,
            mock.patch.object(signature.subprocess, "run", return_value=done),
        ):
            result = signature.harness_version(label, command)
        return result, which.call_args.args[0]

    def _main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), mock.patch("sys.stderr", err):
            rc = signature.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_unlisted_harness_probes_given_command(self):
        result, cmd = self._probe("kiro-cli", "kiro-cli 1.2.3\n", command="kiro-cli")
        self.assertEqual((result, cmd), ("kiro-cli-1.2.3", "kiro-cli"))

    def test_unlisted_harness_without_command_exits_1(self):
        rc, _, err = self._main(["--model", "m", "--harness", "kiro"])
        self.assertEqual(rc, 1)
        self.assertIn("unknown harness 'kiro'", err)

    def test_harness_version_skips_probe(self):
        with mock.patch.object(signature.subprocess, "run") as run:
            rc, out, _ = self._main(
                ["--model", "m", "--harness", "kiro", "--harness-version", "0.5.0"]
            )
        run.assert_not_called()
        self.assertEqual(rc, 0)
        self.assertIn("_kiro-0.5.0_", out)

    def test_harness_label_with_underscore_rejected(self):
        with self.assertRaises(SystemExit):
            self._main(["--model", "m", "--harness", "my_tool"])

    def test_default_prints_id_only(self):
        with mock.patch.object(
            signature, "harness_version", return_value="claude-cli-2.1.291"
        ):
            rc, out, _ = self._main(["--model", "m"])
        self.assertEqual(rc, 0)
        self.assertEqual(len(out.strip().splitlines()), 1)
        self.assertEqual(
            out.strip().split("_")[2:5],
            ["claude-cli-2.1.291", signature.agent_version(), "m"],
        )

    def test_claude_cli_version_parsed(self):
        result, cmd = self._probe("claude-cli", "2.1.291 (Claude Code)\n")
        self.assertEqual((result, cmd), ("claude-cli-2.1.291", "claude"))

    def test_github_copilot_version_parsed(self):
        result, cmd = self._probe("github-copilot", "GitHub Copilot CLI 1.0.89.\n")
        self.assertEqual((result, cmd), ("github-copilot-1.0.89", "copilot"))

    def test_missing_cli_exits_1(self):
        with (
            mock.patch.object(signature.shutil, "which", return_value=None),
            redirect_stdout(io.StringIO()),
            mock.patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            rc = signature.main(["--model", "m"])
        self.assertEqual(rc, 1)
        self.assertIn("`claude` not on PATH", err.getvalue())

    def test_extended_prints_json(self):
        with mock.patch.object(
            signature, "harness_version", return_value="github-copilot-1.0.89"
        ):
            rc, out, _ = self._main(
                ["--model", "m", "--harness", "github-copilot", "--extended"]
            )
        self.assertEqual(rc, 0)
        sig = json.loads(out)["signature"]
        self.assertEqual(sig["id"], "_".join(sig[f] for f in signature.ID_FIELDS))

    def test_model_is_required(self):
        with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()):
            signature.main([])


if __name__ == "__main__":
    unittest.main()
