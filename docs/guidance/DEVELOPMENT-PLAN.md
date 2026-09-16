---
role: Phased capability curriculum, doubling as a prioritised ingestion backlog
updated: 2026-09-16
verified: never
---

# Development Plan — Agentic Engineering & SDD Capability

**Provenance:** corpus-derived. Every ✓ reading row cites an entry in [`SOURCES.md`](../../SOURCES.md); every ➕ row names a source not yet registered. Adapted from the sibling `sdd-workbench` repo's plan, with its paths remapped to this workbench.

A phased curriculum for building capability across four tracks, with reading and tutorials mapped to each step. Every phase produces a **concrete artefact**, not just completed reading.

**Tracks:** **(A)** Agentic AI coding · **(B)** Skills · **(C)** MCP server development · **(D)** Spec-Driven Development

---

## What this plan is, and who it is for

You have cloned the Agentic Workbench. This plan is the route from that clone to a **real project of your own**, built Spec-Driven, with the skills and MCP servers that support it.

It is a **curriculum, not a progress tracker**. Nothing here records how far any particular person has got — the markers describe the *material*, not your history with it.

**You will be working in two repositories, and the distinction matters:**

| | The workbench (this clone) | Your project |
|---|---|---|
| **Holds** | Reading corpus, source register, guidance notes, skills, MCP servers, artefact templates | The system you are actually building — constitution, specs, plans, code, tests |
| **Grows** | Reusable machinery that serves every project you start | One product |
| **Lifespan** | Permanent; you keep coming back to it | Per-project |

Each deliverable below is tagged **ⓦ workbench** or **ⓟ project** so you always know where the output lands. Getting this backwards is the most common way to make a mess: project-specific detail hard-coded into workbench templates, or reusable machinery stranded inside one product repo.

**One consequence worth stating plainly.** The workbench is not a library you read once. Track (D) teaches you to write specifications; tracks (A), (B) and (C) teach you to build the tooling that makes an agent execute them reliably. The plan interleaves them on purpose — you write a constitution, discover it does not constrain anything, and build a hook or a test that does.

---

## Next steps

**If you have just cloned this repo, do these in order.**

1. **Complete Day 0 below** — install the workstation tooling, create your project repository, and build your local corpus. Budget half a day. The repo you cloned contains *no* ingested reading; see Day 0 for why.
2. **Choose the project you will build.** It must be real — something you would write anyway. The plan's value comes from a constitution meeting actual code, and a throwaway will not push back on you.
3. **Work the 10-day kickstart**, starting at Day 1. Do not start at Phase 1. Roughly two hours a day, nine resources, and every day produces something.
4. **Then enter the full plan at Phase 1**, which re-covers the same ground at depth and carries on into months 2–15.

**If you are returning mid-way**, find your current phase in the full plan, re-run the Day 0 corpus check (sources drift, and `docs/landing-zone/` is rebuilt rather than versioned), and carry on.

---

## Day 0 — before any reading

### 1. Install the workstation toolchain

The ingestion routes depend on it. [`workstation/README.md`](../../workstation/README.md) maps the tree; [`workstation/cli/README.md`](../../workstation/cli/README.md) gives the `command → folder` index, and each tool's `install.md` carries the route.

**Install these yourself — do not delegate it to an agent.** Installing changes your machine, and a tool that shifts version mid-task breaks the work in progress. The agent's job is to resolve the route and record it.

### 2. Create your project repository

Empty is fine. It needs to exist before Day 1, because the kickstart's outputs land in it.

### 3. Build your corpus — the clone does not ship one

`docs/landing-zone/` is **excluded from git**, so a fresh clone has an empty corpus and *every* entry will look un-ingested. That is by design, not a fault: the register is the source of truth and the content is refetched from it.

Rebuild it by running [`SOURCES.md`](../../SOURCES.md)'s entries through the [`ingest-source`](../../skills/ingest-source/SKILL.md) skill, which delegates each conversion to [`fetch-to-markdown`](../../workstation/agent/skills/fetch-to-markdown/SKILL.md). This is a deliberate, potentially long operation. You do not need all of it on Day 0 — ingest the ✓ items for the phase you are about to start, and pull the rest as you reach it.

> **The ingestion skills already exist here.** Week 3 therefore studies `ingest-source` and `fetch-to-markdown` as worked examples rather than authoring them from scratch. Run your first few ingestions one at a time and read what the skill did — that is what teaches you what a skill has to encode.

### 4. Note what you are *not* getting

This workbench ships **no organisational material** — no enterprise architecture principles, NFR standards or view catalogue of an organisation's own. **Supply your own.** If you have none, Month 6 still works from the public sources alone — you will just be building the organisational layer from scratch rather than reconciling against it.

---

## How to read the tables

**Source status:** ✓ the source is **already registered** in [`SOURCES.md`](../../SOURCES.md) — ingestion is mechanical, just run it through the `ingest-source` skill · ➕ the source is **not in the register** — add the entry to `SOURCES.md` and [`SOURCE_CATALOGUE.md`](../../SOURCE_CATALOGUE.md) first, then ingest.

Neither marker says anything about whether the file is on your disk right now. On a fresh clone, nothing is. Use `✓`/`➕` to know **how much work an item costs you**: a ✓ is one ingestion run, a ➕ is a register decision followed by an ingestion run.

No reading in this plan is workstation tooling, so nothing here resolves to `workstation/cli/` or `workstation/mcp/` — including track (C), where the subject is *building* an MCP server rather than consuming one.

**Importance:** scored against *this plan's objectives*, not general quality — a five-star reference book can still be three stars here.

| Score | Meaning |
|---|---|
| ★★★★★ | Essential. Skip it and the phase's deliverable suffers. |
| ★★★★☆ | Strongly recommended. Read in full. |
| ★★★☆☆ | Useful reference. Skim, then dip in when you hit the problem it solves. |
| ★★☆☆☆ | Optional. Worth it only if the format suits you or you have slack. |

**Conventions this plan adopts.** Skill code lives under each skill's `scripts/`, documented, with unit tests. Functionality needed by several skills gets refactored into a local MCP server rather than copied — that is what Month 4 is for.

---

# Start here — a 10-day kickstart

If you are new to this material, do **not** start at Phase 1. Complete **Day 0** above, then work through the ten days below: nine resources, roughly two hours a day. Everything here is ★★★★★ in the full plan, and every day produces something.

Day 0 is a prerequisite, not a suggestion — Day 1's reading is a ✓ item, so it has to be ingested before you can read it locally.

The order is deliberate — understand the method before touching the tooling.

## Week 1 — Method and working practice

| Day | Material | Time | Output |
|---|---|---|---|
| **1** | [Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) | 1h | Pick your level — spec-first, spec-anchored, or spec-as-source. Write down which, and why. |
| **2–3** | [github/spec-kit](https://github.com/github/spec-kit) + [docs](https://github.github.com/spec-kit/) | 4h | Run it end-to-end on one small **real** feature. A spec/plan/tasks triple you wrote yourself. |
| **4** | [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) | 1.5h | List three tasks you do weekly; label each *workflow* or *agent*. Most are workflows. |
| **5** | [Claude Code best practices](https://code.claude.com/docs/en/best-practices) | 2h | A `CLAUDE.md` for one repo you actually work in. |

**By the end of week 1** you can write a spec an agent can execute against, and set up a repo so an agent works well in it. That is most of the practical value.

## Week 2 — Skills, then a taste of MCP

| Day | Material | Time | Output |
|---|---|---|---|
| **6** | [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — *the* document in this track — plus [Claude Code — Skills](https://code.claude.com/docs/en/skills) for where they actually live | 2h | Notes on progressive disclosure and description-writing. |
| **7–8** | [anthropics/skills](https://github.com/anthropics/skills) — read `pdf` or `docx` as a production example, then write your own | 4h | **One working skill** ⓦ solving a real repetitive task of yours. |
| **9** | [MCP — Architecture](https://modelcontextprotocol.io/docs/learn/architecture), then [Build an MCP server](https://modelcontextprotocol.io/docs/develop/build-server) | 3h | A running toy server. Orientation only — see below. |
| **10** | *No new reading.* Consolidate. | 2h | A one-page draft constitution for one project. |

## What the kickstart deliberately leaves out

**MCP is orientation, not mastery.** Day 9 exists so you understand resources vs. tools vs. prompts and have seen a server run. Building real MCP infrastructure belongs after you have several skills and can see what they duplicate — guessing at the shared surface earlier wastes the effort. The full plan puts it at month 4 for that reason.

**No context-engineering reading.** Valuable, but it is optimisation. Get something working before tuning what goes into its context.

**One SDD tool, not three.** spec-kit only. Comparing tools in week one teaches taxonomy instead of practice; day 1's article gives you enough comparison to choose.

**The thing to watch for.** The assumption under all of this is that a written spec or constitution actually changes what the agent does. Sometimes it does not — the prose reads well and gets ignored. When you hit that on day 10, the answer is not more prose; it is moving the rule into something deterministic (a hook, a permission, a test). Noticing this early is worth more than finishing the reading.

**If you only have one week:** days 1–5, then day 6 and a half-day skill. The method and working practice are the parts that compound. Skills and MCP keep.

---

# The full plan

## Phase 1 — Weeks 1–4 · Foundations and a first constitution

**Objective:** go from reading about SDD to having a constitution that actually constrains a real project, plus a working skill and MCP server.

### Week 1 — Ground the method (D)

| | Importance | Reading / tutorial |
|---|---|---|
| ✓ | ★★★★★ | [Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) — start here; it frames the other three |
| ➕ | ★★★★★ | [github/spec-kit](https://github.com/github/spec-kit) + [Spec Kit docs](https://github.github.com/spec-kit/) — **tutorial:** run it end-to-end |
| ➕ | ★★★★☆ | [Exploring Generative AI](https://martinfowler.com/articles/exploring-gen-ai.html) — the series index; read the spec-first / spec-anchored / spec-as-source distinction |
| ➕ | ★★★★☆ | [Kiro — Specs](https://kiro.dev/docs/specs/) — the requirements/design/tasks triple, plus steering and hooks |
| ➕ | ★★★☆☆ | [Spec-driven development with AI — GitHub Blog](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/) — announcement-level; largely covered by the spec-kit docs |

**Do:** install spec-kit, run it on one throwaway feature — *not* the real project yet. Note what a spec/plan/tasks triple actually contains in practice.
**Deliverable:** ⓦ `templates/constitution.md` v0.1 in the workbench, instantiated as ⓟ `constitution.md` in your project repo. Plus a decision note on which level you're targeting — spec-first, spec-anchored, or spec-as-source. This choice drives everything downstream; don't leave it implicit.

### Week 2 — Agent working practice (A)

| | Importance | Reading / tutorial |
|---|---|---|
| ➕ | ★★★★★ | [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) — workflows vs. agents; the foundational piece |
| ➕ | ★★★★★ | [Claude Code best practices](https://code.claude.com/docs/en/best-practices) — most directly actionable item this week |
| ✓ | ★★★★☆ | [The new rules of context engineering for Claude 5 generation models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models) — current guidance; supersedes much of the two below |
| ✓ | ★★★☆☆ | [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — filed as background in the register |
| ✓ | ★★★☆☆ | [Context Engineering for AI Agents: Memory vs. Compaction vs. Tool Clearing](https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools) — filed as background in the register |

**Do:** write a `CLAUDE.md` for your project repo against the best-practices guidance, as a live exercise. Read this workbench's own `CLAUDE.md` first as a worked example of the form.
**Deliverable:** ⓟ a `CLAUDE.md` your project actually uses, and ⓦ constitution v0.2 with an **agent working agreement** section — what agents may change unasked, context discipline, when to stop and ask.

### Week 3 — First skills (B)

| | Importance | Reading / tutorial |
|---|---|---|
| ➕ | ★★★★★ | [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — **the single most important document in this track** |
| ➕ | ★★★★★ | [anthropics/skills](https://github.com/anthropics/skills) — **tutorial:** read `docx`/`pdf`/`pptx` as production reference implementations |
| ➕ | ★★★★☆ | [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) — progressive disclosure, the core mechanic |
| ➕ | ★★★★★ | [Claude Code — Skills](https://code.claude.com/docs/en/skills) — where skills actually live in the tool you use; the platform docs cover the API surface, not this |
| ➕ | ★★★★☆ | [Claude Skills Cookbook](https://github.com/anthropics/claude-cookbooks/tree/main/skills) — **tutorial:** runnable notebooks; the guided path, without the course overhead |
| ✓ | ★★★☆☆ | [Agent Skills](https://agentskills.io/home) — the portable open standard; thinner than Anthropic's own docs |
| ➕ | ★★☆☆☆ | *Optional.* [Agent Skills overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) — the orientation piece. Largely subsumed by the two docs above; read it only if you want the concepts before the practice. |
| ➕ | ★★☆☆☆ | *Optional.* [Agent Skills with Anthropic — DeepLearning.AI](https://www.deeplearning.ai/courses/agent-skills-with-anthropic) — **course.** Same ground as the Cookbook at much greater time cost; take it only if a guided video format is what makes material stick for you. |

**Do:** read `ingest-source` and `fetch-to-markdown` against the authoring docs above — note where they follow the guidance and where they diverge. Then author `check-corpus` (enforcing the `SOURCES.md` ingestion invariant). You checked that invariant by eye on Day 0, so you know what it must encode. Per the conventions above: code under the skill's `scripts/`, documented, with unit tests.
**Deliverable:** ⓦ a written critique of the two existing skills, and `check-corpus` working with passing tests — the invariant becomes executable rather than prose.

### Week 4 — First MCP server (C)

| | Importance | Reading / tutorial |
|---|---|---|
| ➕ | ★★★★★ | [MCP — Architecture](https://modelcontextprotocol.io/docs/learn/architecture) — resources vs. tools vs. prompts; get this distinction wrong and the server's shape is wrong |
| ➕ | ★★★★★ | [Build an MCP server](https://modelcontextprotocol.io/docs/develop/build-server) — **the canonical tutorial** |
| ✓ | ★★★★★ | [FastMCP](https://gofastmcp.com/servers/server) — the ergonomic layer you will actually build on |
| ➕ | ★★★☆☆ | [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) — reference for when FastMCP abstracts something you need to reach under |

**Do:** build a minimal server exposing search and read over `docs/landing-zone/`.
**Deliverable:** ⓦ a running local MCP server, plus a written note on **where the skill/MCP boundary sits** — you will need that rule in month 4.

---

## Phase 2 — Months 2–3 · Distil and prove

**Objective:** turn the raw corpus into a distilled knowledge layer, then prove the whole chain on one real project.

### Month 2 — Build the knowledge layer

| | Importance | Reading / tutorial |
|---|---|---|
| ✓ | ★★★★☆ | [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — the raw → wiki → schema pattern you're implementing |
| ✓ | — | Your own corpus, as built on Day 0 — this month is mostly *distillation*, not new intake |
| ➕ | — | Close the **§2 gaps** — C4 model, integration patterns (EIP) and API design, security architecture (OWASP ASVS/Top 10, threat modelling), well-architected/quality-attribute framework. The `architecture-and-views` and `nfr-checklist` notes have nothing to cite without them. |

**Do:** write `docs/guidance/` files to the bar in [`docs/guidance/README.md`](README.md) — dense tables, "reach for it when" / "watch out", each citing its backing corpus files.
**Deliverable:** ⓦ `docs/guidance/` populated (sdd-workflow, context-engineering, skill-authoring, architecture-and-views, nfr-checklist); **§2 closed** in the register and ingested.

### Month 3 — Run one project end-to-end

| | Importance | Reading / tutorial |
|---|---|---|
| ➕ | ★★★★★ | [Spec-Driven Development — best practices so far (Allegro)](https://blog.allegro.tech/2026/06/spec-driven-development-best-practices.html) — field report, not vendor material; the only item here written by people who've already made the mistakes |
| ➕ | ★★★★☆ | [Humans and Agents in Software Engineering Loops](https://martinfowler.com/articles/exploring-gen-ai/humans-and-agents.html) — where the human review points belong |
| ➕ | ★★★★☆ | [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) |
| ➕ | — | Close the **§5 gaps** — commit and versioning conventions (Conventional Commits, SemVer), branching and release strategy, CI pipeline definition, pre-commit hook policy, test strategy, code review policy. §5 is the layer a constitution actually rules on, and this is the month it meets real code. |
| ➕ | — | Close one **§1 gap** — requirements/user-story practice (BDD, story mapping). You are writing specs this month; the rest of §1 waits for month 6. |

**Do:** take **the project you chose at step 2 of Next steps** through constitution → spec → plan → tasks → implementation. Record every point where the constitution failed to constrain something it should have. This is the month the plan exists for.
**Deliverable:** ⓟ working software in your project repo, built Spec-Driven end to end; ⓦ an `examples/` worked example distilled from it, **constitution v1.0** hardened by contact with reality rather than by more reading, and **§5 closed**.

---

## Phase 3 — Months 4–5 · Shared infrastructure and evaluation

**Objective:** consolidate the tooling, then find out whether any of the prose you have written actually governs anything.

### Month 4 — Refactor shared skill logic into MCP (B→C)

| | Importance | Reading / tutorial |
|---|---|---|
| ➕ | ★★★★★ | [Code execution with MCP: building more efficient agents](https://www.anthropic.com/engineering/code-execution-with-mcp) — why tool-per-call stops scaling; this month's whole rationale |
| ✓ | ★★★★★ | [Writing effective tools for agents — with agents](https://www.anthropic.com/engineering/writing-tools-for-agents) — the tool-design discipline the shared server needs |
| ➕ | ★★★☆☆ | [MCP specification](https://modelcontextprotocol.io/specification) — reference, not a read-through |

**Do:** this is the plan's shared-functionality convention made real — what several skills need in common gets refactored into a local MCP server. By month 4 you will have enough skills for the duplication to be visible rather than hypothetical.
**Deliverable:** ⓦ one shared MCP server replacing duplicated per-skill scripts.

### Month 5 — Evaluation and observability

| | Importance | Reading / tutorial |
|---|---|---|
| ✓ | ★★★★☆ | [DeepEval](https://deepeval.com/docs/introduction) — the harness itself |
| ➕ | ★★★★☆ | [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) — needed to drive generation programmatically enough to evaluate it |
| ✓ | ★★★☆☆ | [langfuse](https://langfuse.com/docs/observability/sdk/overview) — valuable, but tracing can follow once the eval loop exists |
| ➕ | ★★★☆☆ | Close one **§4 gap** — observability beyond LLM tracing (OpenTelemetry). langfuse traces the model calls; OTel traces everything around them. |

**Do:** build an eval harness that scores generated artefacts, then use it to answer **the question this whole plan rests on**.

> **The question.** By now you have written a constitution — clauses like *"use `pathlib` over `os`"* or *"ask before overwriting a file"*. Does an agent that reads those clauses actually behave differently, or does the document read like governance without functioning as governance?
>
> **How to test it.** Generate code that deliberately violates a clause, with the constitution loaded, and see whether the agent catches it, refuses, or sails past. One clause at a time. Score the hit rate.

**Your options, if the answer is bad.** Every rule can live at one of these levels, weakest and most flexible first:

| | Mechanism | Deterministic? | Best for |
|---|---|---|---|
| 1 | Prose in always-on context — constitution, `CLAUDE.md` | ✗ | Judgement, priorities, *why* |
| 2 | **Skill** — prose that loads only when relevant | ✗ | Procedures for a specific situation |
| 3 | **Subagent review pass** | ✗ | Catching what self-adherence missed |
| 4 | **Spec or test written first** | ~ | Behaviour you can assert |
| 5 | **Linter, type checker, schema** | ✓ | Structural rules |
| 6 | **Hook** — `PreToolUse` / `PostToolUse` | ✓ | "Never do X", "always run Y after an edit" |
| 7 | **Permission rule** in `settings.json` | ✓ | Hard denials |
| 8 | **CI gate** | ✓ | Anything checkable on the artefact |

**The rule to take away: if a clause can be checked by a program, it does not belong in prose.** Levels 1–3 are probabilistic — the model may comply. Levels 5–8 are enforced by the harness, and the model cannot talk its way past them. Prose earns its place only where mechanisation is impossible.

**The three outcomes.** *Most violations caught* → keep the prose, gate the residue. *Some caught* → hybrid; push every mechanisable clause down the ladder. *Few caught* → shrink the prose hard, let the gates govern, and demote the constitution to a document explaining why they exist. Expect the middle one.

**Deliverable:** ⓦ eval suite over artefact generation; traced agent runs; §4's observability gap closed; and **a written verdict on which clauses survived** — with each failed clause reassigned to a level between 5 and 8, or deleted.

---

## Phase 4 — Months 6–8 · The layered artefact set

**Objective:** turn four layers of collected method into templates a project can be generated from, and make explicit how they compose.

This was one month in earlier drafts and could not fit: twelve register entries and five templates. Two layers a month, with the intake attached to the layer that consumes it.

> **Ingest at reference depth across this whole phase.** You are building templates that *cite* Kimball and Kubernetes, not becoming an expert in either. Depth arrives when a project needs it.

### Month 6 — Business domain and solution (§1, §2)

| | Importance | Reading / tutorial |
|---|---|---|
| ✓ | ★★★★★ | [DDD Reference](https://www.domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_2015-03.pdf) — the vocabulary the business-domain template is built from |
| ✓ | ★★★★★ | [Rozanski & Woods Viewpoint Catalogue](https://www.viewpoints-and-perspectives.info/home/viewpoints/) + your organisation's views — reconcile the two into one view set before templating |
| ➕ | ★★★★☆ | Your organisation's own non-functional requirements and enterprise architecture principles — this workbench ships none; see Day 0 step 4 |
| ➕ | ★★★★☆ | Close the remaining **§1 gaps** — domain discovery (event storming or equivalent), business capability modelling, process notation (BPMN or similar). Three entries. They read as abstract until one real project is behind you, which is why they wait until now. |
| ➕ | ★★★★☆ | The **§2 gaps** — C4, EIP/API design, OWASP ASVS, quality-attribute framework — collected back in **month 2**. Nothing new to gather; the solution template is built from them. |

**Do:** build the business-domain and solution-architecture templates. Reconcile the public view catalogue against your organisation's before you template either — doing it after means templating a view set you then have to unpick.
**Deliverable:** ⓦ two templates — business domain, solution architecture; **§1 closed**.

### Month 7 — Data (§3)

| | Importance | Reading / tutorial |
|---|---|---|
| ➕ | ★★★★☆ | Close the **§3 gaps** — schema migration (Alembic), modelling methodology (Kimball, Data Vault), data contracts and schema evolution, data quality and validation, lineage and governance. Five entries; the whole layer. |
| ✓ | ★★★☆☆ | Your existing §3 register entries — postgres, duckdb, SQLAlchemy, SQLModel, pandas — re-read as *what the layer currently is* before you decide what it should be |

**Do:** build the data-architecture template. The register warns that this layer is "storage engines and ORMs only — a stack list rather than an architecture"; this is the month that stops being true. A single layer gets a whole month because it starts from the least material.
**Deliverable:** ⓦ the data-architecture template; **§3 closed**.

### Month 8 — Technical, implementation, and composition (§4, §5)

| | Importance | Reading / tutorial |
|---|---|---|
| ➕ | ★★★☆☆ | Close the remaining **§4 gaps** — containerisation and runtime, authentication and authorisation (OIDC/OAuth), configuration and secrets management, caching and async work. Four entries. |
| ➕ | ★★★★☆ | The **§5 gaps** — commit conventions, branching, CI, hooks, test strategy, review policy — collected back in **month 3**. Nothing new to gather; the implementation template is built from them. |

**Do:** build the technical and implementation templates, then the part that is easy to skip and hardest to retrofit — **write down how the four input layers compose into the per-project implementation architecture**. Which template feeds which section, what a conflict between two layers means, and who resolves it.
**Deliverable:** ⓦ the five-layer artefact set complete, plus the composition rules. **Every gap in the register is now closed** — 24 of 24.

## Phase 5 — Months 9–15 · Operate and scale

**Objective:** the workbench serves multiple projects and is governed, measured, and secure.

### Months 9–11 — Programmatic generation and reuse (A)

| | Importance | Reading / tutorial |
|---|---|---|
| ➕ | ★★★★★ | Agent SDK overview — read at month 5; Python and TypeScript, and central by this phase |
| ➕ | ★★★★★ | [Claude Code hooks reference](https://code.claude.com/docs/en/hooks) — deterministic enforcement where a prompt won't do; the fallback if month 5 shows constitutions don't constrain |
| ➕ | ★★★★☆ | [Building agents with the Claude Agent SDK](https://claude.com/blog/building-agents-with-the-claude-agent-sdk) — the worked narrative around the reference docs |
| ➕ | ★★★★☆ | [Create plugins](https://code.claude.com/docs/en/plugins) — packaging skills, agents, hooks, and MCP servers for reuse across projects; the mechanism this phase's bootstrap deliverable needs |

**Do:** package the workbench so a new project bootstraps from it in one command. Move artefact generation from interactive sessions to Agent SDK harnesses where it's repeatable.
**Deliverable:** ⓦ bootstrap skill/command; SDK-driven generation for the mechanical parts. From here a new project starts from the workbench in one command rather than by hand.

### Months 12–15 — Govern, secure, measure

| | Importance | Reading / tutorial |
|---|---|---|
| ➕ | ★★★★★ | [MCP Authorization specification](https://modelcontextprotocol.io/specification/draft/basic/authorization) — OAuth 2.1; essential the moment a server stops being stdio-only, irrelevant until then |
| ➕ | ★★★★☆ | OWASP ASVS — for the MCP tool surface, once ingested |
| ✓ | ★★★☆☆ | Revisit context-engineering material against a year of real traces |

**Do:** security-review the MCP surface. Measure artefact quality over the year — which constitution clauses actually got cited or enforced, and which were decoration. Cut the decoration.
**Deliverable:** ⓦ **constitution v2** driven by evidence; documented MCP security posture; publishable skills.

---

## Sequencing notes

### The gap schedule

`SOURCES.md` lists **24 unsourced gaps** across the five layers — the collection backlog. They are not closed in one pass. Each closes in the month that first needs it, so you are never reading about Kubernetes to satisfy a checklist.

| Layer | Gaps | Closes in | Because |
|---|---|---|---|
| **§2** Solution architecture | 4 | Month 2 | `architecture-and-views` and `nfr-checklist` are written that month and have nothing to cite without them. |
| **§5** Implementation architecture | 6 | Month 3 | This is the layer a constitution rules on. Month 3 is where the constitution first meets real code. |
| **§1** Business domain | 1 of 4 | Month 3 | Requirements/user-story practice, because you are writing specs. |
| **§4** Technical architecture | 1 of 5 | Month 5 | OpenTelemetry, in the observability month. |
| **§1** Business domain | 3 of 4 | Month 6 | Domain discovery, capability modelling and process notation feed the business-domain template — and read as abstract until one project is behind you. |
| **§3** Data architecture | 5 | Month 7 | The data template is built that month; until then the layer is storage engines and ORMs only. |
| **§4** Technical architecture | 4 of 5 | Month 8 | The technical template is built that month. |

By the end of Month 8 the register carries no open gaps. Phase 4 absorbs twelve of the twenty-four across three months — three, then five, then four — which is why it was given its own phase rather than crammed into one month. Intake there is reference-depth rather than read-through.

**A gap you cannot source is still a result.** If your organisation has no view catalogue or no branching policy, record that in the register as an open gap rather than substituting someone else's and calling the layer covered. An artefact built on a borrowed standard nobody follows is worse than one that names the hole.

**Why the artefact set gets three months.** Phase 4 builds five templates from four layers of collected method. An earlier draft did it in one month, which meant twelve register entries and five templates side by side — the reliable way to produce templates that cite sources nobody read. The data layer gets a whole month to itself because it starts from the least material: the register describes it as a stack list rather than an architecture.

**Why SDD comes before Skills and MCP.** Weeks 1–2 are deliberately method-first. Skills and MCP servers are delivery mechanisms — building them before you know what artefacts you need produces well-engineered tooling for the wrong target.

**Why the MCP refactor waits until month 4.** This plan's convention is that shared skill functionality becomes a local MCP server. That judgement needs several real skills to be visible; doing it at month 1 means guessing at the shared surface.

**The riskiest assumption in this plan** is that a written constitution changes agent behaviour. Month 5's eval work is what tests it. If it turns out constitutions mostly don't constrain, the answer is to shift enforcement into hooks and permissions — deterministic checks — and shrink the prose. Better to discover that at month 5 than month 15.

---

## What this plan depends on

The plan is not self-contained. It assumes a **substrate** — a register of sources, a way to ingest them, organisational material to architect against, and a documented toolchain. This workbench is one worked instance of that substrate; it is meant to be read as an **example**, not as the only valid shape.

If you are following the plan inside this clone, everything below is already wired up and you only need Day 0. If you are **lifting `DEVELOPMENT-PLAN.md` into a workbench of your own**, this section is the list of what has to exist around it before it means anything.

### The seven dependencies

`✅ ships` = present in a fresh `git clone` · `♻️ rebuild` = deliberately excluded from git, reconstructed locally · `🔷 yours` = this repo's copy is an example only; supply your own.

| # | Dependency | This repo's instance | In a clone | What it costs you to replace |
|---|---|---|---|---|
| 1 | **Source register** — the list of what the corpus contains, grouped by architecture layer | `SOURCES.md` (75 linked entries: 55 across the five layers, 7 agent working practice, 13 workstation tooling) + `SOURCE_CATALOGUE.md` one-line summaries | ✅ ships | 🔷 The **layer model and conventions transfer; the entries do not.** A Python/Vue register serves a Python/Vue shop. Keep §1–§5 and the ingestion invariant, replace the links. |
| 2 | **Ingestion route** — how a URL becomes a local file | The `ingest-source` skill (register mechanics) delegating to the global `fetch-to-markdown` skill (classify, route, quality-check, post-process) | ✅ ships | `fetch-to-markdown` transfers unchanged — it names no register. `ingest-source` names `SOURCES.md` and `docs/landing-zone/`, and its `skills/ingest-source/references/workstation-tooling.md` branch is workstation-specific. |
| 3 | **The corpus** — the reading itself | `docs/landing-zone/` — **0 tracked** | ♻️ rebuild | Free but slow. Rebuilt from dependency 1 via dependency 2. This is Day 0 step 3. |
| 4 | **Organisational material** — your enterprise's own architecture standards, the thing you reconcile public method against | **None** | 🔷 yours | **The one dependency you cannot borrow.** Month 6 reconciles a public view catalogue against it; with no equivalent of your own, that month becomes "build from scratch" rather than "reconcile". |
| 5 | **Toolchain guidance** — how the machine that runs the ingestion is set up | `workstation/cli/` (13 tools, authored `install.md` + `quick_start.md`) and `workstation/mcp/` (1 server, authored `setup.md`); each folder's `reference.md` is ♻️ | ✅ ships (authored files) | 🔷 Machine-specific by definition. The **two-file contract** — short authored guidance beside an ingested reference — is what transfers. |
| 6 | **Agent configuration and skills** | `workstation/agent/` — 42 tracked files: `AGENT-INSTRUCTIONS.md` (linked as `~/.claude/CLAUDE.md`) and the `fetch-to-markdown`, `fix-findings`, `pdf-deliverable`, `python-quality`, `review` and `verify-docs` skills, linked into `~/.claude/` by the `setup-agents` skill, plus a `settings.json` that is merged by hand rather than linked | ✅ ships | 🔷 Yours will differ. Two traps: the symlinks are **absolute paths**, so moving or renaming the repo silently strips every session of its global instructions; and a settings file cannot be linked if the live one carries anything you must not lose — here, a compliance-mandated provider block. |
| 7 | **Guidance notes** — short agent-facing notes applied mid-task | `docs/guidance/` — a `README.md` charter and this plan | ✅ ships | Month 2's deliverable *is* growing this folder. What you need up front is only the charter — the bar a note must clear and the provenance it must declare. |

### What is deliberately absent

`templates/` and `examples/` are named in Weeks 1–4 and Month 3, and **neither directory exists**. That is correct: they are the plan's **outputs**, not its inputs. Week 1 creates `templates/constitution.md`; Month 3 creates the `examples/` worked example. A clone that already contained them would be handing you the answer to the exercise.

The same applies to the five `docs/guidance/` notes named in Month 2 — `sdd-workflow`, `context-engineering`, `skill-authoring`, `architecture-and-views`, `nfr-checklist`. Absent by design. You write them; that is the month.

**This section documents the substrate rather than scaffolding it.** No empty `templates/` stub, no placeholder notes — an empty directory teaches nothing and rots faster than prose.

### If you are copying just the plan

The shortest honest path to a workbench of your own, in dependency order:

1. **Copy verbatim** — `DEVELOPMENT-PLAN.md` and the `fetch-to-markdown` skill. Both are method, not content. Adapt `ingest-source` to your register's paths.
2. **Copy the skeleton, replace the contents** — `SOURCES.md`. Keep the layer model, the register conventions, and the ingestion invariant; delete every entry and re-register your own stack. Mirror it in `SOURCE_CATALOGUE.md`.
3. **Supply from your own organisation** — your enterprise architecture principles, NFR standards and view catalogue. If you genuinely have none, say so in the register as a §1/§2 gap rather than pretending the layer is covered.
4. **Write for your machine** — the `workstation/` tree. Adopt the two-file contract and the rule that **the user installs and the agent records**; the tool list itself is yours.
5. **Copy the charter, not the notes** — `docs/guidance/README.md`.
6. **Then run Day 0**, which builds the corpus and turns the register into something you can actually read.

Steps 1 and 2 take an afternoon. Step 3 is the one that decides whether the plan produces architecture or just well-formatted reading.
