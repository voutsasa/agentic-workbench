"""`.python-version` must satisfy `requires-python` in `pyproject.toml`.

uv reads the first to pick the interpreter and enforces the second when it
resolves, so a mismatch shows up as a venv that cannot be created — on the next
clone, not in the commit that caused it. Standard library only.
"""

from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SPEC_RE = re.compile(r"^\s*(~=|==|!=|>=|<=|>|<)\s*([0-9][0-9.]*)(\.\*)?\s*$")


def as_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def satisfies(version: str, spec: str) -> bool:
    """True when ``version`` meets every comma-separated clause of ``spec``.

    Covers the PEP 440 operators a `requires-python` line uses in practice.
    Versions compare padded with zeros, so `3.14` equals `3.14.0`.
    """
    have = as_tuple(version)
    for clause in spec.split(","):
        match = SPEC_RE.match(clause)
        if not match:
            raise ValueError(f"unsupported requires-python clause: {clause!r}")
        op, raw, wildcard = match.groups()
        want = as_tuple(raw)
        width = max(len(have), len(want))
        a = have + (0,) * (width - len(have))
        b = want + (0,) * (width - len(want))
        if wildcard:  # ==3.14.* / !=3.14.*: compare the named prefix only
            same = have[: len(want)] == want
            ok = same if op == "==" else not same
        elif op == "~=":  # ~=3.14 means >=3.14, ==3.*
            ok = a >= b and have[: len(want) - 1] == want[:-1]
        else:
            ok = {
                "==": a == b,
                "!=": a != b,
                ">=": a >= b,
                "<=": a <= b,
                ">": a > b,
                "<": a < b,
            }[op]
        if not ok:
            return False
    return True


class TestSatisfies(unittest.TestCase):
    def test_lower_bound(self) -> None:
        self.assertTrue(satisfies("3.14", ">=3.14"))
        self.assertFalse(satisfies("3.13", ">=3.14"))

    def test_padding_makes_minor_and_patch_equal(self) -> None:
        self.assertTrue(satisfies("3.14.0", "==3.14"))

    def test_every_clause_must_hold(self) -> None:
        self.assertTrue(satisfies("3.13", ">=3.12,<3.14"))
        self.assertFalse(satisfies("3.14", ">=3.12,<3.14"))

    def test_wildcard_and_compatible_release(self) -> None:
        self.assertTrue(satisfies("3.14.2", "==3.14.*"))
        self.assertFalse(satisfies("3.15", "==3.14.*"))
        self.assertTrue(satisfies("3.15", "~=3.14"))
        self.assertFalse(satisfies("4.0", "~=3.14"))

    def test_an_unknown_clause_is_an_error_not_a_pass(self) -> None:
        with self.assertRaises(ValueError):
            satisfies("3.14", "^3.14")


class TestThisRepo(unittest.TestCase):
    def test_python_version_satisfies_requires_python(self) -> None:
        pinned = (REPO / ".python-version").read_text(encoding="utf-8").strip()
        with (REPO / "pyproject.toml").open("rb") as handle:
            spec = tomllib.load(handle)["project"]["requires-python"]
        self.assertTrue(
            satisfies(pinned, spec),
            f".python-version {pinned} does not satisfy requires-python {spec!r}",
        )


if __name__ == "__main__":
    unittest.main()
