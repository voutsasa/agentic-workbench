# Validating a workstation

Does this machine actually do what the workbench says it does? These are the checks that answer it,
with the sample inputs they need. Run them on a new machine after
[`../agent/setup/`](../agent/setup/README.md), and again whenever a tool, a skill or an assistant
changes underneath you.

| Platform | Steps |
|---|---|
| macOS | [`macos.md`](macos.md) |
| Windows | [`windows.md`](windows.md) |

**The sections are lettered the same on both platforms**, so *validation B* means the same check
whichever machine ran it, and a machine note can cite it without repeating what it was.

## Results go in `machines/`, never here

This folder is a **route**: the steps and their expected output, identical on every machine of a
platform. What a given box produced is **state**, and belongs in that machine's file under
[`../machines/`](../machines/README.md) — the same split the rest of `workstation/` is built on, set
out in [`../machines/README.md`](../machines/README.md).

So: no run logs, no "passed on 2026-09-20", no version numbers here beyond a version that is evidence
for a trap.

## What is here

| Path | Holds |
|---|---|
| [`macos.md`](macos.md), [`windows.md`](windows.md) | the lettered sections — commands and what each should print |
| [`fixtures/`](fixtures/README.md) | sample documents the conversion checks convert, with each one's origin |
| [`fixtures/hydrated-pages.md`](fixtures/hydrated-pages.md) | pages whose text is *not* in their raw HTML, for the Playwright route |

**Fixtures are tracked**, unlike the ingested corpus under `docs/landing-zone/`. A validation input
that is re-fetched at run time proves nothing once the source page changes, which is exactly what
happened to the pages this repo first used as examples.
