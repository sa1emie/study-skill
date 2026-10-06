# Changelog

## 2.0 (2026-10-06)

- The skill is now a folder (`study/`) with progressive disclosure: a short
  `SKILL.md` plus `references/` loaded only when needed. `study.md` is
  generated from it for single-file tools.
- **Register**: `standard` or `plain` explanations, with a plain-language voice
  guide. Plain changes the words, never whether you attempt first.
- **Pre-test and post-test** every session and in every study guide, logged so
  you can see what a session actually moved.
- **Scheduler** (`scripts/schedule.py`): transparent spacing with prerequisite
  credit, review ordering by how much each review covers, deadline caps.
- **Visual outputs**: rendered and checked diagrams; narrated explainer videos
  made locally with Manim and Kokoro (`scripts/explainer/`), each ending in
  retrieval questions; "predict, then drag" simulations (`scripts/sim/`).
- **HTML design system** (`assets/study.css`, `study.js`, `template.html`,
  `references/design.md`): one consistent look for every generated page, light
  and dark, self-scoring quizzes, flashcards; `scripts/inline.py` makes pages
  single-file.
- **Anki export** of missed concepts only, when you say you use Anki.
- Math rendering guidance and a KaTeX checker; a chat hand-off prompt.
- Demo site in `docs/` built from one real chapter.

## 1.1 (2026-08-18)

- One-shot mode alongside Companion.

## 1.0

- Initial release: ingest, instructor model with confidence tiers, concept
  graph, Companion drilling.
