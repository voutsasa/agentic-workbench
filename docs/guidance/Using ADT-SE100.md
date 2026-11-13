# Using ASD-STE100 (Simplified Technical English)

To create a test harness or formatting harness for ASD-STE100 (Simplified Technical English, often mistyped as ADT-STE100), leverage well-respected open-source repositories and ecosystem tools:

- [ASD-STE100 Official Home](https://www.asd-ste100.org/)
- [STE100 Topic on GitHub](https://github.com/topics/ste100)

## 1. Existing Top-Tier Agent & LLM Harness Repositories

Since late 2025/2026, a massive ecosystem has emerged around turning ASD-STE100 Issue 9 into an operational harness or "skill" for AI coding agents. This strips out "AI slop" and mandates precise, unambiguous technical constraints.

Key repositories:
- [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill)
- [AminBlg/SimpleEnglish](https://github.com/AminBlg/SimpleEnglish)
- [samirsawarkar/asd-ste100-skill](https://github.com/samirsawarkar/asd-ste100-skill)

### Recommended Implementations

**[danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill)**
A highly respected Claude Code skill and baseline framework. Built specifically to rewrite and parse ambiguous prose into strict STE. Features clear evaluation rules and a robust Python script framework for direct integration into test harness pipelines. Also see: [YouTube demo](https://www.youtube.com/watch?v=xVTgczRj1YA)

**[AminBlg/SimpleEnglish](https://github.com/AminBlg/SimpleEnglish)**
A highly-rated, zero-dependency repository that acts as an agent harness for Cursor, Claude Code, and Copilot. Forces LLMs to follow the exact discipline of an Airbus or Boeing manual (e.g., maximum 20 words per instruction).

**[samirsawarkar/asd-ste100-skill](https://github.com/samirsawarkar/asd-ste100-skill)**
Integrates the international specification with linting scripts (`compile_prompt.py` and an STE-100 linter). Excellent for scaffolding a custom Python test suite.

## 2. Core Libraries for Custom Harness Logic

If writing a custom harness from scratch (e.g., in a CI/CD pipeline or automated testing workflow), integrate these community-built parser and lookup backends:

### The dfch Ecosystem

Managed by dfch, this suite provides everything needed for programmatic checking:

- **[biz.dfch.AsdSte100Vocab](https://github.com/dfch/biz.dfch.AsdSte100Vocab)**: Raw library containing the official Issue 9 vocabulary dataset
- **[biz.dfch.AsdSte100Parser](https://github.com/dfensgmbh/biz.dfch.AsdSte100Parser)**: Dedicated grammar to parse STE text using EBNF and Lark
- **[biz.dfch.AsdSte100Mcp](https://github.com/dfch/biz.dfch.AsdSte100Mcp)**: Model Context Protocol (MCP) server allowing tools to interface with the lookup database via standard JSON
- **[AsdSte100Issue9TrainingData](https://github.com/dfensgmbh/AsdSte100Issue9TrainingData)**: Training datasets for ASD-STE100 Issue 9. This training dataset let you fine-tune an LLM to better understand, what the words in the "ASD-STE100 Issue 9" standard mean. WIP no training data yet available!!

### Rule-Based Checkers

**stelint / ste100**
Rule-based checkers leveraging spaCy or regex to dynamically parse text and measure compliance against grammar constraints (e.g., blocking active "-ing" forms or passive voice).

References: [Gist example](https://gist.github.com/starise/470f53dbd16149dcd168fa45bff17d1f) | [STE100 Topic](https://github.com/topics/ste100)

## 3. Architecture of an STE-100 Harness

Structure harness components around these layers:

| Component Layer | Implementation Material / Tool |
|---|---|
| **The Validator/Linter** | Use stelint or custom spaCy NLP script to block synonyms, check sentence length bounds (max 20–25 words), and audit parts of speech |
| **The Dictionary Database** | Embed JSON or dictionary arrays from biz.dfch.AsdSte100Vocab so your test harness can look up approved verbs vs. unapproved terms |
| **Core Evaluation Logs** | Set up clean, structured Markdown output or JSON logs to flag precisely why a specific sentence failed the harness check |

Reference: [adobe/ai-repo-harness-guide](https://github.com/adobe/ai-repo-harness-guide/blob/main/guide/07-Build-Your-Harness.md)

## 4. Official Free Reference Documentation

Calibrate test assertions against the ground truth. The official specifications are available from the [ASD-STE100 Home Page](https://www.asd-ste100.org/), where the Simplified Technical English Maintenance Group (STEMG) distributes the Issue 9 PDF standard free of charge.

Additional references:
- [Uninet Tuno University](https://www.uninettunouniversity.net/en/asd-ste100.aspx)

## Next Steps

Are you building this harness to lint and validate human-written documentation in a CI/CD pipeline, or creating a prompt-engineering harness to control AI agent output? Specify your use case for precise Python script setup or CI configuration files.
