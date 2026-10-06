# All Of Computing — AI Learning Companion

A planned local-first learning system for studying across disciplines with an AI tutor, practical exercises, assessments, and a portable knowledge base.

The repository currently contains the project plan. There is no working application yet. The name comes from the existing workspace; the product scope extends beyond computing.

## Start here

1. [Project plan](docs/PROJECT-PLAN.md): product vision, learning workflows, architecture, milestones, risks, and decisions.
2. [Screen design plan](docs/design-plans/learning-companion.md): eight user-facing screens and their acceptance criteria.
3. [Data and knowledge contract](docs/DATA-CONTRACT.md): ownership, concept relationships, assessment evidence, exports, and Obsidian compatibility.
4. [First build brief](docs/FIRST-BUILD.md): a bounded first implementation with a concrete completion test.

## What the system should make possible

- Say what you want to understand and receive an achievable learning path.
- Discover existing knowledge through low-pressure diagnostics and demonstrations.
- Learn through explanations, dialogue, teach-back, quizzes, essays, walkthroughs, and projects.
- See what you have encountered, what you have demonstrated, and what needs review.
- Resume a learning session without having to reconstruct the history yourself.
- Keep readable Markdown notes compatible with Obsidian, with structured records you can export.

## Current decisions

- **Confirmed:** runs on the user's computer, with optional cloud AI.
- **Proposed:** local browser GUI, Markdown knowledge library, SQLite records, a single orchestrated AI workflow, and provider adapters.
- **Unresolved:** first subject, initial AI provider, budget, preferred teaching language, and software license.

Planning date: 2026-10-06. Implementation starts with [the first build brief](docs/FIRST-BUILD.md).
