# Five design rules worth enforcing

Applied when the work is structural rather than mechanical. Proportion matters more than doctrine:

1. **An abstraction earns its place when there are two real implementations.** A test double counts
   only if it replaces something slow, networked or destructive. One implementation does not need an
   interface, and `AbstractThing` with a single subclass is the failure mode, not the goal.
2. **A layer boundary must be checkable by a command, not asserted in prose.** If a README says
   "this layer touches no filesystem", there must be a grep that proves it — otherwise it will drift
   and the false claim is worse than none.
3. **Inputs explicit.** No function reaches for `os.environ`, `__file__`, or the current directory.
   Pass an environment, a root, a fetcher. This is what makes code both testable and installable.
4. **One module owns one external tool.** Then "what changed in the upgrade?" is one file to
   re-read, and one contract test to run.
5. **Interfaces as callables or `Protocol`, never ABCs.** `Fetch = Callable[[str, ...], dict]` is a
   complete interface and a test can satisfy it with a function.

Rule 4's companion is in `decisions.md` under *Contract tests for what you do not own*: pin a third
party's **behaviour** in a test rather than citing its line numbers in a docstring.
