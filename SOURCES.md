---
role: Source register — source of truth for what belongs in the project
updated: 2026-09-16
verified: never
---

# Agentic Workbench — Source Register

Curated register of the source material this workbench draws on to produce constitutions, skills, and other artefacts for projects adopting Spec-Driven Development.

This file is the **source of truth** for what belongs in the project. Add or remove a source here first; `SOURCE_CATALOGUE.md` (one-line summaries) and `docs/landing-zone/` (ingested content) follow from it.

## How this register is organised

Sources are grouped by the **architecture layer they feed**, not by technology:

| § | Layer | Feeds |
|---|---|---|
| 1 | Business domain | What the business does — domain model, ubiquitous language, org-level principles |
| 2 | Solution architecture | How the solution is shaped — views, decisions, quality attributes |
| 3 | Data architecture | How data is modelled, stored, moved, and governed |
| 4 | Technical architecture | The stack the solution runs on |
| 5 | Implementation architecture | How the specific project work is actually built and governed |

Layers 1–4 are **inputs**. Layer 5 is the **per-project output** the workbench exists to produce.

The two **cross-cutting aspects** at the end sit outside the layer model deliberately — *agent working practice* governs how the *agent* works rather than how the *system* is built, and *workstation tooling* serves this repo only. Neither should leak into a generated artefact as though it were architecture.

### Conventions

- **First-party sources only.** A source's URL must be the canonical home of the thing itself — the project's own repo or docs site, the author's own publication. Never a mirror, rehost, scraped copy, fork, or third-party summary. Where a name has a plausible impostor (a stalled fork, a same-named package by a different author), match the URL's owner against the project before adding the entry. This matters more than it looks: `docs/landing-zone/` is not in git and is refetched from these URLs, so a bad entry is a standing fault rather than a one-off. Install channels carry their own checks in [`skills/ingest-source/references/workstation-tooling.md`](skills/ingest-source/references/workstation-tooling.md) — *Verify the package, never assume it*.
- **One canonical entry per source.** A source appears as a `[bracket link]` exactly once. Where it also informs another layer, that layer carries an italic *see also* cross-reference instead of a second link — this keeps the ingestion invariant one-to-one.
- **Ingestion invariant.** Every `[bracket link]` entry resolves to `docs/landing-zone/<bracket text>.{md,pdf}`, with `:` in a title written as ` - ` in the filename. Workstation tooling entries are the one exception, and they resolve into two trees by subsection — `#### CLI tools` to `workstation/cli/<bracket text>/reference.md` alongside that tool's authored `install.md` and `quick_start.md`, and `#### MCP servers` to `workstation/mcp/<bracket text>/reference.md` alongside that server's authored `setup.md`.
- **Every entry is external.** A source's link target is always an `http(s)` URL, so every entry is subject to the invariant above and to the [`ingest-source`](skills/ingest-source/SKILL.md) skill. The register carries no internal documents.
- **Gaps** are listed per layer as unsourced placeholders — the collection backlog.

---

## 1. Business domain

* [DDD Reference](https://www.domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_2015-03.pdf)

*See also:* Rozanski & Woods Viewpoint Catalogue — Context and Functional viewpoints (§2).

**Gaps — not yet sourced**

- Domain discovery method (event storming or equivalent)
- Business capability modelling
- Requirements/user-story practice (BDD, story mapping)
- Process notation (BPMN or similar)

## 2. Solution architecture

* [Rozanski & Woods Viewpoint Catalogue](https://www.viewpoints-and-perspectives.info/home/viewpoints/)
* [Architecture Decision Records](https://github.com/adr/madr)
* [SOLID Relevance](https://blog.cleancoder.com/uncle-bob/2020/10/18/Solid-Relevance.html)
* [plantuml](https://plantuml.com/component-diagram)

*See also:* DDD Reference — strategic design and bounded contexts (§1).

**Gaps — not yet sourced**

- C4 model (the notation most teams actually draw in)
- Integration patterns (EIP) and API design guidance (REST/OpenAPI)
- Security architecture — OWASP ASVS/Top 10, threat modelling
- Well-architected/quality-attribute framework

## 3. Data architecture

* [dbml](https://dbml.dbdiagram.io/home/)
* [postgres](https://www.postgresql.org/docs/current/index.html)
* [duckdb](https://duckdb.org/docs/current/)
* [SQLAlchemy](https://docs.sqlalchemy.org/en/20/tutorial/index.html#unified-tutorial)
* [SQLModel](https://github.com/fastapi/sqlmodel)
* [pandas](https://pandas.pydata.org/docs/user_guide/index.html)

*See also:* DDD Reference — aggregates, repositories, and persistence boundaries (§1).

**Gaps — not yet sourced**

> This layer is currently storage engines and ORMs only — a stack list rather than an architecture.

- Schema migration (Alembic — conspicuous, given SQLAlchemy is already here)
- Modelling methodology (dimensional/Kimball, Data Vault)
- Data contracts and schema evolution
- Data quality and validation (pandera, Great Expectations)
- Lineage and governance

## 4. Technical architecture

### Experimentation stack

#### Backend and API

* [FastAPI](https://fastapi.tiangolo.com/tutorial/)
* [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/)
* [FastMCP](https://gofastmcp.com/servers/server)
* [yaml](https://pyyaml.org/wiki/PyYAMLDocumentation)
* [pymupdf](https://github.com/pymupdf/pymupdf)

#### Frontend

* [vue](https://vuejs.org/guide/quick-start.html)
* [vite](https://vite.dev/guide/)
* [tailwindcss](https://tailwindcss.com/docs/installation/using-vite)
* [streamlit](https://docs.streamlit.io/)

#### Testing

* [PyTest](https://docs.pytest.org/en/stable/)
#### Quality gates

##### Python

* [uv](https://docs.astral.sh/uv/getting-started/)
* [ruff](https://docs.astral.sh/ruff/)
* [bandit](https://bandit.readthedocs.io/en/latest/)
* [radon](https://radon.readthedocs.io/en/latest/)

##### JavaScript/TypeScript

* [oxlint](https://oxc.rs/docs/guide/usage/linter)
* [oxfmt](https://oxc.rs/docs/guide/usage/formatter)
* [retire.js](https://retirejs.github.io/retire.js/)
* [plato](https://github.com/es-analysis/plato)

##### Cross-platform

* [opengrep](https://github.com/opengrep/opengrep)

---

### Enterprise stack

#### Back end

* [Java](https://dev.java/learn/)
* [Spring Boot](https://docs.spring.io/spring-boot/index.html)

#### Front end

* [Angular](https://angular.dev/overview)
* [TypeScript](https://www.typescriptlang.org/docs/)

#### Build tools

* [Maven](https://maven.apache.org/guides/getting-started/index.html)

#### Testing

##### Java / Spring Boot

* [JUnit](https://docs.junit.org/current/user-guide/)
* [AssertJ](https://assertj.github.io/doc/)
* [Mockito](https://site.mockito.org/)
* [Spring Boot Testing](https://docs.spring.io/spring-boot/reference/testing/index.html)
* [Testcontainers](https://java.testcontainers.org/)

##### Angular / TypeScript

* [Angular Testing](https://angular.dev/guide/testing)
* [Vitest](https://vitest.dev/guide/)

*See also:* playwright for end-to-end browser testing (Cross-cutting aspects → 2. Workstation tooling).

#### Quality gates

##### Java / Spring Boot

* [Checkstyle](https://checkstyle.org/)
* [SpotBugs](https://spotbugs.readthedocs.io/en/latest/introduction.html)
* [JaCoCo](https://www.jacoco.org/jacoco/trunk/doc/)
* [OWASP Dependency-Check](https://owasp.org/projects/dependency-check)

##### Angular / TypeScript

* [angular-eslint](https://github.com/angular-eslint/angular-eslint)
* [typescript-eslint](https://typescript-eslint.io/getting-started/)
* [Prettier](https://prettier.io/docs/)

*See also:* opengrep and retire.js (Experimentation stack → Quality gates).

### LLM and agent stack

* [Pydantic AI](https://pydantic.dev/docs/ai/overview/)
* [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)
* [LiteLLM](https://docs.litellm.ai/docs/proxy/docker_quick_start)
* [DeepEval](https://deepeval.com/docs/introduction)
* [langfuse](https://langfuse.com/docs/observability/sdk/overview)

**Gaps — not yet sourced**

- Containerisation and runtime (Docker, Kubernetes)
- Observability beyond LLM tracing (OpenTelemetry)
- Authentication and authorisation (OIDC/OAuth)
- Configuration and secrets management
- Caching and async work (Redis, task queues)

## 5. Implementation architecture

The per-project output layer: how work is specified, built, verified, and governed in-repo.

### Method

* [Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
 
**Gaps — not yet sourced**

> Every static-analysis tool is here; almost none of the *process* an implementation constitution actually rules on.

- Commit and versioning conventions (Conventional Commits, SemVer)
- Branching and release strategy
- CI pipeline definition
- Pre-commit hook policy
- Test strategy (test pyramid, contract testing, coverage policy)
- Code review policy

---

## Cross-cutting aspects

### 1. Agent working practice

Governs how the agent works, not how the system is built. Feeds the agent working agreement in a constitution and the authoring of skills — never the architecture layers above.

* [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
* [Agent Skills](https://agentskills.io/home)
* [The new rules of context engineering for Claude 5 generation models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)
* [Writing effective tools for agents — with agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
* [Using Claude Code: The unreasonable effectiveness of HTML](https://claude.com/blog/using-claude-code-the-unreasonable-effectiveness-of-html)

#### Background and legacy material

* [Context Engineering for AI Agents: Memory vs. Compaction vs. Tool Clearing](https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools)
* [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

### 2. Workstation tooling

Tools and MCP servers used to ingest and process sources into this repo. Inputs to the workbench itself, never to a downstream artefact.

An entry here means a route has been resolved and written down, **not** that the tool is live on any given machine — the user installs and registers, the agent records. See [`AGENTS.md`](AGENTS.md#the-user-installs-the-agent-records).

#### CLI tools

Each tool has a folder at `workstation/cli/<tool>/` with install commands, a quick start, and its ingested page — see [`workstation/cli/README.md`](workstation/cli/README.md).

* [playwright](https://playwright.dev/docs/intro)
* [pandoc](https://github.com/jgm/pandoc)
* [docling](https://github.com/docling-project/docling)
* [magick](https://github.com/imagemagick/imagemagick)
* [defuddle](https://github.com/kepano/defuddle)
* [tesseract](https://github.com/tesseract-ocr/tesseract)
* [sem-cli](https://github.com/ataraxy-labs/sem)
* [weasyprint](https://github.com/Kozea/WeasyPrint)
* [dbml-cli](https://dbml.dbdiagram.io/cli/#prerequisites)
* [plantuml-cli](https://plantuml.com/command-line)
* [mermaid-cli](https://github.com/mermaid-js/mermaid-cli)
* [d2-cli](https://d2lang.com/tour/install/)
* [typst](https://github.com/typst/typst)

#### MCP servers

Third-party MCP servers configured into this machine's agent clients. Each has a folder at `workstation/mcp/<server>/` holding its setup and its ingested page — see [`workstation/mcp/README.md`](workstation/mcp/README.md).

Servers **authored** in this workbench are project output, not workstation tooling, and do not belong here.

* [drawio-mcp](https://www.drawio.com/docs/manual/generate/drawio-mcp-server/)
