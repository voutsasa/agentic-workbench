"""Unit tests for the pre-push hook itself — stdlib only, no network.

    python3 -m unittest discover -s tests

Four things are covered here: the invocation guard, the ruff and Pyright steps
opted into by their respective marker files, and the unit-test step driven by
``.pre-push-tests``. What the checkers do once invoked is covered by
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
import sys
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
        return subprocess.CompletedProcess(
            proc.args, proc.returncode, out_f.read(), err_f.read()
        )


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
HOOK_ENV_FLAGS = (
    "SKIP_REPO_CHECK",
    "SKIP_VERIFY_CLAIMS",
    "SKIP_PRE_PUSH_TESTS",
    "PRE_PUSH_IN_TESTS",
    "SKIP_RUFF",
    "SKIP_PYRIGHT",
)


#: Stands in for repo_check.py and verify_claims.py: logs the interpreter and
#: arguments it was started with, into the repo it runs in, then passes.
LOGGING_STUB = """import sys
from pathlib import Path

with Path({log!r}).open("a", encoding="utf-8") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
sys.exit(0)
"""


class HookRepoCase(unittest.TestCase):
    """A throwaway git repo, and apart from it a copy of the hook.

    The hook sits in its own skills-shaped tree with a passing stub checker
    beside it and no verifier, the layout of the global skills link. The repo
    has no `workstation/` tree at all — it stands for any repo but the
    workbench, so the hook has to find its checker from its own location.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.root = base / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        scripts = base / "skills" / "review" / "scripts"
        scripts.mkdir(parents=True)
        self.hook = scripts / "pre-push"
        shutil.copyfile(HOOK, self.hook)
        # A stub that passes, so the hook reaches the unit-test step. There is
        # no verifier, so the hook exits straight after that step.
        self.checker = scripts / "repo_check.py"
        self.checker.write_text(
            LOGGING_STUB.format(log="checker-calls.log"), encoding="utf-8"
        )
        self.verifier = base / "skills" / "verify-docs" / "scripts" / "verify_claims.py"

    def add_verifier(self) -> None:
        self.verifier.parent.mkdir(parents=True)
        self.verifier.write_text(
            LOGGING_STUB.format(log="verifier-calls.log"), encoding="utf-8"
        )

    def log(self, name: str) -> list[str]:
        path = self.root / name
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@t"]
            + list(args),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(self, name: str) -> str:
        (self.root / name).write_text("# x\n", encoding="utf-8")
        self.git("add", name)
        self.git("commit", "-q", "-m", name)
        return self.git("rev-parse", "HEAD")

    def write_suite(self, name: str, body: str) -> None:
        suite = self.root / name
        suite.mkdir()
        (suite / "test_sample.py").write_text(body, encoding="utf-8")

    def name_dirs(self, text: str) -> None:
        (self.root / ".pre-push-tests").write_text(text, encoding="utf-8")

    def run_hook(
        self, *, hook: Path | None = None, refs: str = "", **env: str
    ) -> subprocess.CompletedProcess:
        clean = {k: v for k, v in os.environ.items() if k not in HOOK_ENV_FLAGS}
        if BASH is None:
            raise RuntimeError("bash is required to test the pre-push hook")
        # Bytes, not text: text mode on Windows writes "\n" as "\r\n", and git
        # itself feeds the ref list LF-terminated.
        proc = subprocess.run(
            [BASH, "-c", 'exec "$@"', "bash", str(hook or self.hook)]
            + ["origin", "remote"],
            cwd=self.root,
            env={**clean, **env},
            input=refs.encode("utf-8"),
            capture_output=True,
            timeout=TIMEOUT_S,
            check=False,
        )
        return subprocess.CompletedProcess(
            proc.args,
            proc.returncode,
            proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"),
        )


class ScriptResolutionTests(HookRepoCase):
    """The hook finds its checkers beside itself, not in the pushed repo."""

    def test_checker_beside_the_hook_runs_outside_the_workbench(self) -> None:
        self.commit("README.md")
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.log("checker-calls.log")), 1, result.stderr)

    def test_a_repo_with_no_tracked_markdown_skips_the_checker(self) -> None:
        # A code-only repo has nothing for the documentation gate to read; the
        # checker would refuse with "no tracked markdown", blocking every push.
        (self.root / "a.py").write_text("x = 1\n", encoding="utf-8")
        self.git("add", "a.py")
        self.git("commit", "-q", "-m", "code")
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log("checker-calls.log"), [], result.stderr)
        self.assertIn("no tracked markdown", result.stderr)

    def test_symlinked_hook_resolves_to_its_real_location(self) -> None:
        self.commit("README.md")
        link = self.root / ".git" / "hooks" / "pre-push"
        try:
            link.symlink_to(self.hook)
        except OSError as exc:
            self.skipTest(f"cannot create a symlink here: {exc}")
        result = self.run_hook(hook=link)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.log("checker-calls.log")), 1, result.stderr)

    def test_missing_checker_still_runs_the_opted_in_steps(self) -> None:
        self.checker.unlink()
        self.write_suite("suite", FAILING_SUITE)
        self.name_dirs("suite\n")
        result = self.run_hook()
        self.assertIn("checker not found", result.stderr)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tests in suite failed", result.stderr)


def make_venv_python(root: Path) -> None:
    """A `.venv/bin/python` that logs each call, then runs this interpreter."""
    python = root / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    real = Path(sys.executable).as_posix()
    python.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> venv-calls.log\n"
        f'exec "{real}" "$@"\n',
        encoding="utf-8",
        newline="\n",
    )
    python.chmod(0o755)


class InterpreterTests(HookRepoCase):
    """Every Python step, the gates included, runs on the repo's venv."""

    def test_checker_runs_on_the_venv_interpreter(self) -> None:
        make_venv_python(self.root)
        self.commit("README.md")
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log("venv-calls.log")
        self.assertTrue(any("repo_check.py" in c for c in calls), calls)

    def test_verifier_runs_on_the_venv_interpreter(self) -> None:
        make_venv_python(self.root)
        self.add_verifier()
        self.git("symbolic-ref", "HEAD", "refs/heads/x")
        sha = self.commit("a.md")
        result = self.run_hook(refs=f"refs/heads/x {sha} refs/heads/x {ZERO}\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log("venv-calls.log")
        self.assertTrue(any("verify_claims.py" in c for c in calls), calls)

    def test_no_venv_falls_back_to_the_platform_interpreter_and_says_so(
        self,
    ) -> None:
        """`python` on Windows, where `python3` is absent or a Store stub."""
        expected = "python" if os.name == "nt" else "python3"
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"falling back to {expected} on PATH", result.stderr)


ZERO = "0" * 40


class RefListTests(HookRepoCase):
    """Which markdown the claim verifier is given for each pushed ref."""

    def setUp(self) -> None:
        super().setUp()
        self.add_verifier()

    def verified(self) -> list[str]:
        calls = self.log("verifier-calls.log")
        self.assertEqual(len(calls), 1, calls)
        return calls[0].split("--files ", 1)[1].split()

    def test_new_branch_from_a_root_commit_checks_its_files(self) -> None:
        """Regression: `$sha^` does not exist, and the hidden diff error passed."""
        self.git("symbolic-ref", "HEAD", "refs/heads/feature")
        sha = self.commit("a.md")
        result = self.run_hook(
            refs=f"refs/heads/feature {sha} refs/heads/feature {ZERO}\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.verified(), ["a.md"])

    def test_new_branch_diffs_against_the_remote_default_branch(self) -> None:
        """The remote's HEAD, not a hard-coded main, is the merge base."""
        self.git("symbolic-ref", "HEAD", "refs/heads/trunk")
        trunk = self.commit("base.md")
        self.git("update-ref", "refs/remotes/origin/trunk", trunk)
        self.git(
            "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk"
        )
        self.git("checkout", "-q", "-b", "feature")
        self.commit("b.md")
        sha = self.commit("c.md")
        result = self.run_hook(
            refs=f"refs/heads/feature {sha} refs/heads/feature {ZERO}\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(self.verified()), ["b.md", "c.md"])

    def test_a_diff_that_cannot_run_refuses_the_push(self) -> None:
        sha = self.commit("a.md")
        unknown = "1" * 40
        result = self.run_hook(refs=f"refs/heads/x {sha} refs/heads/x {unknown}\n")
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("SKIP_VERIFY_CLAIMS=1", result.stderr)
        self.assertEqual(self.log("verifier-calls.log"), [])


class UnitTestStepTests(HookRepoCase):
    """The step that runs the directories named in ``.pre-push-tests``."""

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


#: Stands in for ruff: the hook runs ``<python> -m ruff``, and a ``ruff``
#: package at the repo root is found first. It logs each call and exits with
#: the code in its RUFF_STUB_EXIT variable.
RUFF_STUB = """import os
import sys
from pathlib import Path

with Path("ruff-calls.log").open("a", encoding="utf-8") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
sys.exit(int(os.environ.get("RUFF_STUB_EXIT", "0")))
"""


class RuffStepTests(HookRepoCase):
    """The ruff step, opted into per repo by a ``.pre-push-ruff`` file."""

    def setUp(self) -> None:
        super().setUp()
        stub = self.root / "ruff"
        stub.mkdir()
        (stub / "__init__.py").write_text("", encoding="utf-8")
        (stub / "__main__.py").write_text(RUFF_STUB, encoding="utf-8")

    def opt_in(self) -> None:
        (self.root / ".pre-push-ruff").write_text("", encoding="utf-8")

    def calls(self) -> list[str]:
        log = self.root / "ruff-calls.log"
        return log.read_text(encoding="utf-8").splitlines() if log.exists() else []

    def test_no_file_runs_no_ruff(self) -> None:
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [])

    def test_opted_in_runs_lint_and_format_check(self) -> None:
        self.opt_in()
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ["check .", "format --check ."])

    def test_ruff_failure_refuses_the_push(self) -> None:
        self.opt_in()
        result = self.run_hook(RUFF_STUB_EXIT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ruff", result.stderr)
        self.assertIn("SKIP_RUFF=1", result.stderr)

    def test_skip_flag_skips_only_ruff(self) -> None:
        self.opt_in()
        result = self.run_hook(SKIP_RUFF="1", RUFF_STUB_EXIT="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SKIP_RUFF=1", result.stderr)
        self.assertEqual(self.calls(), [])


PYRIGHT_STUB = """import os
import sys
from pathlib import Path

with Path("pyright-calls.log").open("a", encoding="utf-8") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
sys.exit(int(os.environ.get("PYRIGHT_STUB_EXIT", "0")))
"""


class PyrightStepTests(HookRepoCase):
    """The Pyright step, opted into per repo by ``.pre-push-pyright``."""

    def setUp(self) -> None:
        super().setUp()
        stub = self.root / "pyright"
        stub.mkdir()
        (stub / "__init__.py").write_text("", encoding="utf-8")
        (stub / "__main__.py").write_text(PYRIGHT_STUB, encoding="utf-8")

    def opt_in(self) -> None:
        (self.root / ".pre-push-pyright").write_text("", encoding="utf-8")

    def calls(self) -> list[str]:
        log = self.root / "pyright-calls.log"
        return log.read_text(encoding="utf-8").splitlines() if log.exists() else []

    def test_no_file_runs_no_pyright(self) -> None:
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [])

    def test_opted_in_runs_the_module(self) -> None:
        self.opt_in()
        result = self.run_hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [""])

    def test_pyright_failure_refuses_the_push(self) -> None:
        self.opt_in()
        result = self.run_hook(PYRIGHT_STUB_EXIT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Pyright", result.stderr)
        self.assertIn("SKIP_PYRIGHT=1", result.stderr)

    def test_skip_flag_skips_only_pyright(self) -> None:
        self.opt_in()
        result = self.run_hook(SKIP_PYRIGHT="1", PYRIGHT_STUB_EXIT="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SKIP_PYRIGHT=1", result.stderr)
        self.assertEqual(self.calls(), [])


SHIM = HOOK.with_name("pre-push.windows")

#: Stands in for the tracked hook: records its arguments and stdin, then exits
#: with the code in HOOK_STUB_EXIT.
HOOK_STUB = """#!/usr/bin/env bash
printf '%s\\n' "$@" > args.log
cat > stdin.log
exit "${HOOK_STUB_EXIT:-0}"
"""


class WindowsShimTests(unittest.TestCase):
    """The shim copied once into .git/hooks on Windows, in place of the hook."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.tracked = self.root / "workstation/agent/skills/review/scripts/pre-push"

    def run_shim(self, stdin: str = "", **env: str) -> subprocess.CompletedProcess:
        if BASH is None:
            raise RuntimeError("bash is required to test the pre-push shim")
        return subprocess.run(
            [BASH, str(SHIM), "origin", "https://example.invalid/repo"],
            cwd=self.root,
            env={**os.environ, **env},
            input=stdin,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            check=False,
        )

    def write_stub(self) -> None:
        self.tracked.parent.mkdir(parents=True)
        self.tracked.write_text(HOOK_STUB, encoding="utf-8")

    def test_shim_is_lf_only(self) -> None:
        """A CRLF shim fails with `bad interpreter` before it runs anything."""
        self.assertNotIn(b"\r\n", SHIM.read_bytes())

    def test_passes_arguments_and_ref_list_through(self) -> None:
        self.write_stub()
        refs = "refs/heads/main abc refs/heads/main def\n"
        result = self.run_shim(stdin=refs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.root / "args.log").read_text(encoding="utf-8").splitlines(),
            ["origin", "https://example.invalid/repo"],
        )
        self.assertEqual((self.root / "stdin.log").read_text(encoding="utf-8"), refs)

    def test_hook_refusal_refuses_the_push(self) -> None:
        self.write_stub()
        result = self.run_shim(HOOK_STUB_EXIT="1")
        self.assertEqual(result.returncode, 1)

    def empty_home(self) -> Path:
        home = self.root.parent / f"{self.root.name}-home"
        home.mkdir()
        self.addCleanup(shutil.rmtree, home, True)
        return home

    def test_missing_hook_refuses_rather_than_passing(self) -> None:
        result = self.run_shim(HOME=self.empty_home().as_posix())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found", result.stderr)
        self.assertIn("--no-verify", result.stderr)

    def test_outside_the_workbench_runs_the_globally_linked_hook(self) -> None:
        """Any other repo has no tracked hook; the skills link has one."""
        home = self.empty_home()
        self.tracked = home / ".claude/skills/review/scripts/pre-push"
        self.write_stub()
        result = self.run_shim(stdin="x\n", HOME=home.as_posix())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.root / "args.log").read_text(encoding="utf-8").splitlines(),
            ["origin", "https://example.invalid/repo"],
        )


if __name__ == "__main__":
    unittest.main()
