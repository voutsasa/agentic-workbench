---
tool: plantuml-cli
command: plantuml
product: PlantUML
verified: 2026-08-20
author: Achilleas Voutsas
version: 0.3.0
---

# plantuml-cli — install

Binary: `plantuml`. Product: PlantUML. A JAR with a wrapper script — **the package alone will not render**.

| Platform | Command |
|---|---|
| macOS | `brew install plantuml` |
| Windows | `scoop install extras/plantuml` |

Note the bucket: `extras`, not `main`.

Verify with `plantuml -version`; the first line is `PlantUML version 1.YYYY.N`. **The version is year-based, not semver** — `1.2026.6` is the sixth release of 2026, so a "higher" middle number is a newer year and nothing more.

## Workstation configuration

**Java and Graphviz installed alongside — required, not optional.** PlantUML is a JAR and needs a **Java runtime** plus **Graphviz**; the package pulls in neither. Which versions a given machine carries is install status and belongs in that machine's file under [`../../machines/`](../../machines/).

Without Graphviz, every diagram type that needs layout — component, class, state — fails, while sequence diagrams may still render. That partial success makes the failure look intermittent rather than like a missing dependency.

```
brew install openjdk graphviz
```

On Windows the scoop manifest only *suggests* a JDK rather than depending on one, so both are manual and the JDK lives in a bucket you must add first:

```
scoop bucket add java
scoop install java/openjdk main/graphviz
```

Confirm the whole chain in one step:

```
plantuml --check-graphviz
```

It should report a Graphviz version and `Installation seems OK. File generation OK`. Anything less than that full string means the JAR runs but cannot render, which fails later and less obviously than a missing binary.

## Tools that embed PlantUML

Publishing tools that render `plantuml` blocks for you — md2conf, for one — **do not call the `plantuml` wrapper**. They look for `java` plus a `plantuml.jar` file, so a working `plantuml` on `PATH` is invisible to them and rendering fails partway through a run. Point them at the wrapper explicitly:

```sh
# ~/.zshenv
export PLANTUML_CMD='plantuml'
```

`~/.zshenv`, not `~/.zshrc`: zsh reads `.zshrc` only for interactive shells, so scripts, make, cron and CI would not see it.

**Prefer `PLANTUML_CMD` over `PLANTUML_JAR`.** The brew wrapper is not a thin shim — read it and it does three things a bare `java -jar` does not:

```bash
GRAPHVIZ_DOT="/opt/homebrew/opt/graphviz/bin/dot" exec "/opt/homebrew/opt/openjdk/bin/java" \
  -Djava.awt.headless=true -jar .../plantuml.jar "$@"
```

It pins the JDK to Homebrew's own rather than whatever `java` resolves to — which on a machine running a version manager is often a shim for a different release — points Graphviz at an absolute `dot` rather than trusting `PATH`, and forces headless mode. `PLANTUML_JAR=/opt/homebrew/opt/plantuml/libexec/plantuml.jar` gives up all three and re-introduces the `PATH` dependency for both `java` and `dot`. Whether it renders on a given machine then depends on both happening to resolve there — that dependency on ambient `PATH` state is the fragility, not a reason to use it.

Use `/opt/homebrew/opt/plantuml/...` if you ever do need the jar path — the `Cellar/plantuml/1.2026.6/...` path inside the wrapper is version-pinned and breaks on upgrade.

Docs: [Command line](https://plantuml.com/command-line) · full page ingest: [reference.md](reference.md)
