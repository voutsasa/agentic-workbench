---
role: One-sentence capability summary per source, mirroring SOURCES.md
updated: 2026-09-28
verified: never
---

# Source Catalogue

What each source in the workbench gives you: one line per entry, in the same order as the register. [`SOURCES.md`](SOURCES.md) decides what belongs here — this file says what it's for. The two stay entry-for-entry identical, so a source added there needs a line added here.

See [`README.md`](README.md) for the project as a whole and the role of every other file in it.

## The layer model

Sources are grouped by the architecture layer they feed, not by technology. **Layers 1–4 are inputs; layer 5 is the per-project output** the workbench exists to produce. The cross-cutting aspects sit outside the layer model deliberately — agent working practice governs how the *agent* works rather than how the *system* is built, and workstation tooling serves this repo only.

See [`SOURCES.md`](SOURCES.md) for the full layer definitions, register conventions, and the collection backlog of gaps not yet sourced.

---

## 1. Business domain

* [DDD Reference](https://www.domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_2015-03.pdf) — Eric Evans' condensed reference of Domain-Driven Design patterns, building blocks, and strategic-design vocabulary.

*See also:* Rozanski & Woods Viewpoint Catalogue — Context and Functional viewpoints (§2).

## 2. Solution architecture

* [Rozanski & Woods Viewpoint Catalogue](https://www.viewpoints-and-perspectives.info/home/viewpoints/) — Canonical catalogue of six viewpoints for describing software architecture from multiple stakeholder angles.
* [Architecture Decision Records](https://github.com/adr/madr) — MADR template system for documenting architectural decisions in structured, version-controlled Markdown.
* [SOLID Relevance](https://blog.cleancoder.com/uncle-bob/2020/10/18/Solid-Relevance.html) — Uncle Bob revisits whether SOLID principles still hold value in modern software design.
* [plantuml](https://plantuml.com/component-diagram) — Generates UML and other diagrams from a simple text-based description language.

*See also:* DDD Reference — strategic design and bounded contexts (§1).

## 3. Data architecture

* [dbml](https://dbml.dbdiagram.io/home/) — Database Markup Language for defining and visualizing schemas as code.
* [postgres](https://www.postgresql.org/docs/current/index.html) — Full-featured, open-source relational database management system.
* [duckdb](https://duckdb.org/docs/current/) — Embedded, in-process analytical (OLAP) SQL database for fast local data analysis.
* [SQLAlchemy](https://docs.sqlalchemy.org/en/20/tutorial/index.html#unified-tutorial) — Python SQL toolkit and Object-Relational Mapper for database access.
* [SQLModel](https://github.com/fastapi/sqlmodel) — Combines SQLAlchemy and Pydantic to define database models with type-safe validation.
* [pandas](https://pandas.pydata.org/docs/user_guide/index.html) — Data manipulation and analysis library built around DataFrame structures.

*See also:* DDD Reference — aggregates, repositories, and persistence boundaries (§1).

## 4. Technical architecture

### Experimentation stack

#### Backend and API

* [FastAPI](https://fastapi.tiangolo.com/tutorial/) — High-performance Python web framework for building APIs with automatic docs and validation.
* [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/) — Data validation and settings management using Python type annotations.
* [FastMCP](https://gofastmcp.com/servers/server) — Python framework for building and deploying Model Context Protocol (MCP) servers.
* [yaml](https://pyyaml.org/wiki/PyYAMLDocumentation) — PyYAML library for parsing and emitting YAML in Python.
* [pymupdf](https://github.com/pymupdf/pymupdf) — Python library for fast PDF parsing, rendering, and text/image extraction.

#### Frontend

* [vue](https://vuejs.org/guide/quick-start.html) — Progressive JavaScript framework for building reactive user interfaces.
* [vite](https://vite.dev/guide/) — Fast frontend build tool and dev server with instant hot module replacement.
* [tailwindcss](https://tailwindcss.com/docs/installation/using-vite) — Utility-first CSS framework for building custom designs directly in markup.
* [streamlit](https://docs.streamlit.io/) — Turns Python scripts into interactive web apps and data dashboards with minimal code.

#### Testing

* [PyTest](https://docs.pytest.org/en/stable/) — Feature-rich Python testing framework with fixtures and plugin ecosystem.

#### Quality gates

##### Python

* [uv](https://docs.astral.sh/uv/getting-started/) — Fast, all-in-one Python package and project manager replacing pip and virtualenv.
* [ruff](https://docs.astral.sh/ruff/) — Extremely fast Python linter and code formatter.
* [bandit](https://bandit.readthedocs.io/en/latest/) — Static analysis tool for finding common security issues in Python code.
* [radon](https://radon.readthedocs.io/en/latest/) — Computes Python code metrics like cyclomatic complexity and maintainability index.

##### JavaScript/TypeScript

* [oxlint](https://oxc.rs/docs/guide/usage/linter) — Rust-based, extremely fast linter for JavaScript and TypeScript.
* [oxfmt](https://oxc.rs/docs/guide/usage/formatter) — Rust-based, extremely fast code formatter for JavaScript and TypeScript.
* [retire.js](https://retirejs.github.io/retire.js/) — Scans JavaScript dependencies for known security vulnerabilities.
* [plato](https://github.com/es-analysis/plato) — Generates visual JavaScript source code complexity and quality reports.

##### Cross-platform

* [opengrep](https://github.com/opengrep/opengrep) — Ultra-fast semantic grep for finding vulnerability patterns across 30+ languages.

---

### Enterprise stack

#### Back end

* [Java](https://dev.java/learn/) — Oracle's official Java learning portal, from setting up the JDK to writing and running first applications.
* [Spring Boot](https://docs.spring.io/spring-boot/index.html) — Creates stand-alone, production-grade Spring-based Java applications with opinionated defaults and minimal configuration.

#### Front end

* [Angular](https://angular.dev/overview) — Google's web development framework for building modern apps, documented with overviews and in-browser tutorials.
* [TypeScript](https://www.typescriptlang.org/docs/) — Microsoft's official TypeScript documentation: introductions by background, everyday guides, and how it models JavaScript modules.

#### Build tools

* [Maven](https://maven.apache.org/guides/getting-started/index.html) — Apache Maven's getting-started cookbook: set up, compile, test, package JARs, manage dependencies, and deploy Java projects.

#### Testing

##### Java / Spring Boot

* [JUnit](https://docs.junit.org/current/user-guide/) — The JUnit User Guide: reference documentation for writing tests, extensions, and test engines in Java.
* [AssertJ](https://assertj.github.io/doc/) — Fluent testing assertions for Java and the JVM, bundled in Spring Boot's test starter.
* [Mockito](https://site.mockito.org/) — Mocking framework for Java unit tests, bundled in Spring Boot's test starter.
* [Spring Boot Testing](https://docs.spring.io/spring-boot/reference/testing/index.html) — Spring Boot's utilities and annotations for testing applications, from test-scope dependencies to integration test support.
* [Testcontainers](https://java.testcontainers.org/) — Java library giving JUnit tests lightweight, throwaway instances of common databases, Selenium browsers, and more.

##### Angular / TypeScript

* [Angular Testing](https://angular.dev/guide/testing) — Angular's official testing guide, covering the Vitest-based default setup for new Angular CLI projects.
* [Vitest](https://vitest.dev/guide/) — Next-generation testing framework powered by Vite; the default unit-test runner for new Angular projects.

*See also:* playwright for end-to-end browser testing (Cross-cutting aspects → 2. Workstation tooling).

#### Quality gates

##### Java / Spring Boot

* [Checkstyle](https://checkstyle.org/) — Checks Java source against configurable rules for naming, imports, formatting, Javadoc, and class design.
* [SpotBugs](https://spotbugs.readthedocs.io/en/latest/introduction.html) — Finds likely errors in Java programs by detecting known bug patterns.
* [JaCoCo](https://www.jacoco.org/jacoco/trunk/doc/) — Java code coverage library with coverage counters and ready-to-use tools for measuring test coverage.
* [OWASP Dependency-Check](https://owasp.org/projects/dependency-check) — Software composition analysis tool checking project dependencies for known, publicly disclosed vulnerabilities.

##### Angular / TypeScript

* [angular-eslint](https://github.com/angular-eslint/angular-eslint) — Monorepo of tooling that enables ESLint to lint Angular projects.
* [typescript-eslint](https://typescript-eslint.io/getting-started/) — Enables ESLint to lint TypeScript, including rules that use type information.
* [Prettier](https://prettier.io/docs/) — Opinionated code formatter supporting TypeScript, Angular, HTML, CSS, JSON, and more.

*See also:* opengrep and retire.js (Experimentation stack → Quality gates).

### LLM and agent stack

* [Pydantic AI](https://pydantic.dev/docs/ai/overview/) — Model-agnostic Python agent framework for building type-safe, production-grade generative AI applications.
* [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) — LangChain's framework for building stateful, graph-based multi-step agent workflows.
* [LiteLLM](https://docs.litellm.ai/docs/proxy/docker_quick_start) — Unified proxy/SDK for calling 100+ LLM provider APIs through a single OpenAI-compatible interface.
* [DeepEval](https://deepeval.com/docs/introduction) — Open-source unit-testing framework for evaluating and benchmarking LLM application outputs.
* [langfuse](https://langfuse.com/docs/observability/sdk/overview) — Observability and tracing platform for debugging and monitoring LLM applications.
* [MCP architecture overview](https://modelcontextprotocol.io/docs/learn/architecture) — How MCP clients, servers and transports fit together, and what resources, tools and prompts each are.
* [Build an MCP server](https://modelcontextprotocol.io/docs/develop/build-server) — The canonical tutorial for building an MCP server, from tool definitions to transport.
* [MCP specification](https://modelcontextprotocol.io/specification) — The protocol specification: versions, base protocol, and the client and server feature surface.
* [MCP authorization specification](https://modelcontextprotocol.io/specification/draft/basic/authorization) — OAuth 2.1 authorization for MCP servers beyond stdio: flows, tokens and metadata discovery.

## 5. Implementation architecture

### Method

* [Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) — Martin Fowler compares three spec-driven development tools and their approaches.

---

## Cross-cutting aspects

### 1. Agent working practice

* [DPACT - A Framework for Identity, Accountability, and Task-Scoped Authority in Autonomous AI Agent Systems](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7307799) — Framework for establishing agent identity, accountability, and task-scoped authority in autonomous AI systems.
* [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — Karpathy's pattern for LLM-maintained knowledge bases layering raw sources, an evolving wiki, and a governing schema.
* [Agent Skills](https://agentskills.io/home) — Open standard for packaging reusable, on-demand agent capabilities as portable `SKILL.md` folders.
* [The new rules of context engineering for Claude 5 generation models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models) — Anthropic on why newer models need fewer explicit constraints, cutting Claude Code's system prompt over 80%.
* [Writing effective tools for agents — with agents](https://www.anthropic.com/engineering/writing-tools-for-agents) — Anthropic's guide to designing agent-friendly tool interfaces, refined using agents themselves.
* [Using Claude Code: The unreasonable effectiveness of HTML](https://claude.com/blog/using-claude-code-the-unreasonable-effectiveness-of-html) — Claude blog post on HTML as a surprisingly versatile agent output and interaction format.
* [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) — Anthropic's SDK for building custom agents programmatically on Claude Code's harness, in Python and TypeScript.
* [Claude Code hooks reference](https://code.claude.com/docs/en/hooks) — Lifecycle hook events, matchers and input/output schema for enforcing rules deterministically rather than by prompt.
* [AGENTS.md](https://agents.md/) — Open standard for the agent instruction file, with its format and the tools that read it.
* [Using hooks with GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks) — Copilot CLI's hook events, configuration and payloads for running commands automatically around tool use.
* [Adding agent skills for GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills) — How Copilot CLI discovers and loads `SKILL.md` folders, and where they must live.
* [About customizing GitHub Copilot responses](https://docs.github.com/en/copilot/concepts/prompting/response-customization) — How Copilot loads AGENTS.md and custom instructions across its CLI, IDE and web surfaces.
* [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices) — Anthropic's guide to working effectively with Claude Code: instruction files, workflows, tooling and context discipline.
* [Extend Claude with skills](https://code.claude.com/docs/en/skills) — How Claude Code discovers and loads skills, and where `SKILL.md` folders live.
* [Claude Code plugins overview](https://code.claude.com/docs/en/plugins) — Packaging skills, agents, hooks and MCP servers as installable plugins, distributed through marketplaces.

#### Background and legacy material

* [Context Engineering for AI Agents: Memory vs. Compaction vs. Tool Clearing](https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools) — Anthropic cookbook comparing strategies for managing long-running agent context windows.
* [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Anthropic engineering guide on curating and structuring what agents keep in context.

### 2. Workstation tooling

Tools and MCP servers used to ingest and process sources into this repo. An entry records a route, not a live install.

#### CLI tools

See [`workstation/cli/README.md`](workstation/cli/README.md) for the `command → product → folder` map. Each tool below has its own folder at `workstation/cli/<tool>/` holding the install commands, a quick start, and the packaging traps worth knowing before you run it.

* [playwright](https://playwright.dev/docs/intro) — Browser automation library for testing, scraping, and driving web pages programmatically.
* [pandoc](https://github.com/jgm/pandoc) — Universal document converter supporting dozens of markup and file formats.
* [docling](https://github.com/docling-project/docling) — Converts PDFs, Office docs, and more into structured, LLM-ready formats.
* [magick](https://github.com/imagemagick/imagemagick) — Command-line toolkit for creating, editing, and converting images.
* [defuddle](https://github.com/kepano/defuddle) — Extracts clean, readable article content from cluttered web pages.
* [tesseract](https://github.com/tesseract-ocr/tesseract) — Open-source OCR engine for extracting text from images.
* [sem-cli](https://github.com/ataraxy-labs/sem) — Semantic, entity-level version control providing diffs, blame, and impact analysis across many languages.
* [weasyprint](https://github.com/Kozea/WeasyPrint) — Renders HTML and CSS into PDF documents.
* [dbml-cli](https://dbml.dbdiagram.io/cli/#prerequisites) — Command-line converter between DBML schema files and SQL DDL in both directions.
* [plantuml-cli](https://plantuml.com/command-line) — Runs PlantUML from the terminal to render diagram sources into images.
* [mermaid-cli](https://github.com/mermaid-js/mermaid-cli) — Renders Mermaid diagram definitions into SVG, PNG, or PDF from the command line.
* [d2-cli](https://d2lang.com/tour/install/) — Renders D2 diagram scripts into SVG, PNG, PDF, and other formats from the terminal.
* [typst](https://github.com/typst/typst) — Markup-based typesetting system; the PDF engine pandoc uses here in place of LaTeX.
* [databricks-cli](https://docs.databricks.com/aws/en/dev-tools/cli/install) — Databricks' Go CLI; holds the OAuth login and issues tokens for the Genie MCP server.
* [unity-gateway](https://github.com/databricks/unity-gateway) — Databricks' `ug` CLI; runs coding agents through AI Gateway and registers Databricks MCP servers.
* [jq](https://jqlang.org/) — Lightweight command-line JSON processor used by Claude’s Databricks MCP token-header helper.
* [confluence-sync-md](https://dev.azure.com/euemadev/EA/_git/confluence-sync-md) — Publishes Markdown to Confluence Cloud with md2conf and exports pages back with cme.

#### MCP servers

Third-party MCP servers configured into this machine's agent clients. Each has a folder at [`workstation/mcp/`](workstation/mcp/README.md) holding its setup and ingested page.

* [drawio-mcp](https://www.drawio.com/docs/manual/generate/drawio-mcp-server/) — Official draw.io MCP server; opens generated XML, CSV, or Mermaid diagrams in the draw.io editor.
* [ado-remote-mcp](https://learn.microsoft.com/en-us/azure/devops/mcp-server/remote-mcp-server) — Microsoft's hosted Azure DevOps MCP Server; org-scoped Entra OAuth over HTTP, no local install.
* [databricks-mcp](https://learn.microsoft.com/en-us/azure/databricks/agents/mcp-tools/managed-mcp) — Azure Databricks' hosted MCP servers (Genie, AI Search, SQL, sandbox), authenticated through the Databricks CLI login.
