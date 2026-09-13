"""Unit tests for the pre-push hook's invocation guard — stdlib only, no network.

    python3 -m unittest discover -s tests

Only the guard is covered here. What the hook does once git *is* driving it is
covered by test_repo_check.py and by the verifier's own suite; this file exists
for the one failure mode neither of those can see.

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

import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "scripts" / "pre-push"
REPO_ROOT = Path(__file__).resolve().parents[5]

#: Long enough for repo_check over the whole repo (~0.07s documented, about a
#: second in practice), short enough that the hang fails the suite rather than
#: stalling it.
TIMEOUT_S = 30


def run_hook(*args: str) -> subprocess.CompletedProcess:
    """Invoke the hook with stdin an open pipe that never receives data.

    Two things this deliberately does not do, because either one hides the bug:

    * ``stdin=DEVNULL`` — EOF arrives immediately and the ref loop ends on its
      own, so the hook returns even with no guard in place.
    * ``communicate()`` — it closes stdin when there is no input to write, which
      is the same EOF by another route. Measured: with the guard removed, a
      ``communicate()``-based helper returned in 0.25s instead of blocking.

    So the pipe is held open for the process's whole life, and stdout and stderr
    go to files rather than pipes — nothing is draining them while we wait.
    """
    with tempfile.TemporaryFile("w+") as out_f, tempfile.TemporaryFile("w+") as err_f:
        proc = subprocess.Popen(
            [str(HOOK), *args],
            cwd=REPO_ROOT,
            stdin=subprocess.PIPE,
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
            if proc.stdin is not None:
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
            [str(HOOK)],
            cwd=REPO_ROOT,
            env={"PATH": "/usr/bin:/bin:/usr/local/bin", "SKIP_REPO_CHECK": "1"},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("SKIP_REPO_CHECK=1", proc.stderr)
        self.assertNotIn("no ref list on stdin", proc.stderr)


if __name__ == "__main__":
    unittest.main()
