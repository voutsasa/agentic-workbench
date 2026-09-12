# Five ways these tools report success while being wrong

Every one of these was hit on a real project. They share a shape: the command exits 0, prints
something plausible, and the gate you thought you installed is not running.

## 1. pyright resolves against the wrong interpreter

**Symptom.** Every third-party import is an error — `Import "requests" could not be resolved`,
`Import "pytest" could not be resolved` — while the code runs fine.

**Cause.** pyright does not find the project venv on its own.

```toml
[tool.pyright]
venvPath = "."
venv = ".venv"
```

**Why it matters beyond noise.** A wall of false positives trains everyone to ignore pyright output,
including the true positives. On the project this skill came from, adding those two lines took it
from "errors everywhere, all session" to `0 errors` — and then the two real errors it did find were
worth having.

## 2. radon silently skips files it cannot parse

**Symptom.** The average complexity looks better than it should, and a file you know is complex is
missing from the report. Buried in the output: `ERROR: multiple exception types must be parenthesized`.

**Cause.** `uvx radon` runs on whatever Python uv picks, which may be older than the project's
target. ruff formats to the project's `requires-python` — at 3.14 that means PEP 758's
`except A, B:` without parentheses, which older interpreters reject.

```make
complexity:
	uvx --python 3.14 radon cc src -a -nb     # match the project's own version
```

**The general rule.** Any tool that parses the source must run on at least the version the code
targets. radon exits 0 having skipped the file, so nothing tells you.

## 3. pdoc cannot import the project under uvx

**Symptom.** `RuntimeError: Error importing <package>` from a `uvx pdoc` run.

**Cause.** pdoc imports the modules it documents, so it needs the project's dependencies — which a
`uvx` sandbox does not have.

**Fix.** pdoc is a dev dependency, not a `uvx` tool. This is the exception to keeping tools out of
the lock file: anything that imports your code belongs in the environment your code lives in.

## 4. `git diff` cannot see an untracked file

**Symptom.** A documentation-drift gate passes for a file that was never committed — so a brand-new
command ships with no reference entry.

**Fix.** Stage intent first:

```make
docs-current: docs
	@git add --intent-to-add docs/
	@git diff --exit-code docs/
```

**Test it.** Break a generated file on purpose and confirm the gate fails. A gate nobody has seen
fail is a gate nobody knows works.

## 5. A gate that always fails is not a gate

**Symptom.** `make check` has been red for weeks and everyone runs the steps individually.

**Cause.** A threshold set to an ideal rather than to the code, or a check pointed at files that
cannot pass — vendored templates, generated output, third-party prose.

**Fix.** Exempt them explicitly and write the reason next to the exemption:

```python
# Documents whose links point at a structure that lives in another repository, published knowingly
# with --no-force-valid-url. Checking them would mean this gate always fails.
EXEMPT = ("architecture-decision-records",)
```

An exemption with a reason is a decision. An exemption without one is a hole.
