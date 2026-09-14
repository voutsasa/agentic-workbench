"""Unit tests for the pre-push hook itself — stdlib only, no network.

    python3 -m unittest discover -s tests

Two things are covered here: the invocation guard, and the unit-test step driven
by ``.pre-push-tests``. What the checkers do once invoked is covered by
test_repo_check.py and by the verifier's own suite; this file exists for the
behaviour that lives only in the shell script.

The unit-test step runs against a throwaway git repo holding a stub checker, so
each case controls exactly which directories are named and whether their tests
pass — the real repo's suites would make every outcome depend on its state.

git calls pre-push with two arguments and feeds the ref list on stdin. Run by
hand it gets neither, and the ref loop is a bare ``while read``: with stdin an
open pipe that never carries data — an agent session, a terminal-less runner —
it blocks forever with no output. The first test reproduces exactly that by
holding the pipe open rather than closing it, so a regression fails on the
timeout instead of hanging the suite.

The second test covers the other half. Exiting quietly would be worse than the
hang, because ``repo_check`` has already printed *all enabled checks passed* by
then, so a silent exit 0 reads as a full pass with verify_claims.py never
invoked.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "scripts" / "pre-push"
REPO_ROOT = Path(__file__).resolve().parents[5]
BASH = shutil.which("bash")

#: Long enough for repo_check over the whole repo (~0.07s documented, about a
#: second in practice), short enough that the hang fails the suite rather than
#: stalling it.
TIMEOUT_S = 30


def hook_command(*args: str) -> list[str]:
    """Run the Bash hook through its interpreter on every supported platform."""
    if BASH is None:
        raise RuntimeError("bash is required to test the pre-push hook")
    # `exec` avoids an intermediate Bash retaining the open stdin pipe that
    # deliberately reproduces a hand-run hook invocation.
    return [BASH, "-c", 'exec "$@"', "bash", str(HOOK), *args]


def run_hook(*args: str) -> subprocess.CompletedProcess:
    """Invoke the hook with stdin an open pipe that never receives data.

    Two things this deliberately does not do, because either one hides the bug:

    * ``stdin=DEVNULL`` — EOF arrives immediately and the ref loop ends on its
      own, so the hook returns even with no guard in place.
    * ``communicate()`` — it closes stdin when there is no input to write, which
      is the same EOF by another route. Measured: with the guard removed, a
      ``communicate()``-based helper returned in 0.25s instead of blocking.

    So on POSIX the pipe is held open for the process's whole life, and stdout
    and stderr go to files rather than pipes — nothing is draining them while
    we wait. Git for Windows's MSYS Bash does not preserve a native subprocess
    pipe reliably, so Windows uses EOF; the diagnostic assertions below still
    prove the argument guard there.
    """
    with tempfile.TemporaryFile("w+") as out_f, tempfile.TemporaryFile("w+") as err_f:
        stdin = subprocess.DEVNULL if os.name == "nt" else subprocess.PIPE
        proc = subprocess.Popen(
            hook_command(*args),
            cwd=REPO_ROOT,
            stdin=stdin,
            stdout=out_f,
            stderr=err_f,
            text=True,
        )
        try:
            proc.wait(timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise
        finally:
            if stdin is subprocess.PIPE and proc.stdin is not None:
                proc.stdin.close()
        out_f.seek(0)
        err_f.seek(0)
        return subprocess.CompletedProcess(proc.args, proc.returncode, out_f.read(), err_f.read())


class GuardTests(unittest.TestCase):
    def test_no_arguments_does_not_hang(self) -> None:
        """Without git's two arguments the hook returns rather than blocking."""
        try:
            result = run_hook()
        except subprocess.TimeoutExpired:
            self.fail(
                f"pre-push blocked for {TIMEOUT_S}s with no ref list on stdin — "
                "the argument guard before the `while read` loop is gone"
            )
        self.assertEqual(result.returncode, 0)

    def test_no_arguments_says_the_claim_check_did_not_run(self) -> None:
        """A hand run must not read as a full pass."""
        result = run_hook()
        self.assertIn("no ref list on stdin", result.stderr)
        self.assertIn("verify_claims.py did NOT run", result.stderr)

    def test_one_argument_is_still_treated_as_a_hand_run(self) -> None:
        """git passes two; anything less is not git."""
        result = run_hook("origin")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no ref list on stdin", result.stderr)

    def test_skip_flag_short_circuits_before_anything_else(self) -> None:
        """SKIP_REPO_CHECK=1 exits before repo_check, so it reaches no guard."""
        proc = subprocess.run(
            hook_command(),
            cwd=REPO_ROOT,
            env={"PATH": "/usr/bin:/bin:/usr/local/bin", "SKIP_REPO_CHECK": "1"},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("SKIP_REPO_CHECK=1", proc.stderr)
        self.assertNotIn("no ref list on stdin", proc.stderr)


PASSING_SUITE = """import unittest


class Sample(unittest.TestCase):
    def test_passes(self):
        pass
"""

FAILING_SUITE = """import unittest


class Sample(unittest.TestCase):
    def test_fails(self):
        self.fail("deliberate failure")
"""

#: Variables that change what the hook does; stripped so the developer's own
#: shell, or an outer hook run, cannot decide a test's outcome.
HOOK_ENV_FLAGS = ("SKIP_REPO_CHECK", "SKIP_VERIFY_CLAIMS", "SKIP_PRE_PUSH_TESTS", "PRE_PUSH_IN_TESTS")


class UnitTestStepTests(unittest.TestCase):
    """The step that runs the directories named in ``.pre-push-tests``."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        # A stub that passes, so the hook reaches the unit-test step. There is
        # no verifier, so the hook exits straight after that step.
        checker = self.root / "workstation/agent/skills/review/scripts/repo_check.py"
        checker.parent.mkdir(parents=True)
        checker.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")

    def write_suite(self, name: str, body: str) -> None:
        suite = self.root / name
        suite.mkdir()
        (suite / "test_sample.py").write_text(body, encoding="utf-8")

    def name_dirs(self, text: str) -> None:
        (self.root / ".pre-push-tests").write_text(text, encoding="utf-8")

    def run_hook(self, **env: str) -> subprocess.CompletedProcess:
        clean = {k: v for k, v in os.environ.items() if k not in HOOK_ENV_FLAGS}
        return subprocess.run(
            hook_command("origin", "remote"),
            cwd=self.root,
            env={**clean, **env},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            check=False,
        )

    def test_no_file_runs_no_tests(self) -> None:
        self.write_suite("suite", FAILING_SUITE)
        result = self.run_hook()
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("unit tests in", result.stderr)

    def test_passing_suite_lets_the_push_continue(self) -> None:
        self.write_suite("suite", PASSING_SUITE)
        self.name_dirs("# a comment line\n\n  suite  # trailing comment\n")
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unit tests in suite", result.stderr)

    def test_failing_suite_refuses_the_push(self) -> None:
        self.write_suite("suite", FAILING_SUITE)
        self.name_dirs("suite\n")
        result = self.run_hook()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tests in suite failed", result.stderr)
        self.assertIn("SKIP_PRE_PUSH_TESTS=1", result.stderr)

    def test_every_named_directory_runs(self) -> None:
        """A passing first suite must not hide a failing second one."""
        self.write_suite("first", PASSING_SUITE)
        self.write_suite("second", FAILING_SUITE)
        self.name_dirs("first\nsecond\n")
        result = self.run_hook()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tests in second failed", result.stderr)

    def test_missing_directory_refuses_rather_than_skipping(self) -> None:
        self.name_dirs("nowhere\n")
        result = self.run_hook()
        self.assertEqual(result.returncode, 2)
        self.assertIn("is not a directory", result.stderr)

    def test_skip_flag_skips_only_the_tests(self) -> None:
        self.write_suite("suite", FAILING_SUITE)
        self.name_dirs("suite\n")
        result = self.run_hook(SKIP_PRE_PUSH_TESTS="1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("SKIP_PRE_PUSH_TESTS=1", result.stderr)
        self.assertNotIn("unit tests in", result.stderr)

    def test_hook_started_from_a_suite_does_not_rerun_the_suites(self) -> None:
        self.write_suite("suite", FAILING_SUITE)
        self.name_dirs("suite\n")
        result = self.run_hook(PRE_PUSH_IN_TESTS="1")
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("unit tests in", result.stderr)


if __name__ == "__main__":
    unittest.main()
