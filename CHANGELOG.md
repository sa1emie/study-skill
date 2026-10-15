# Changelog

## 2.1 (2026-10-15)

- **State integrity.** A session on an existing unit now starts with
  `schedule.py <unit> check`: it validates the concept graph and
  `mastery.json` together, reports orphans, drift, bad prereqs and impossible
  values with an exit code, and `--fix` migrates legacy files without deleting
  anything. `record` refuses concept ids that are not in `concepts.md`
  and suggests the closest ones.
- **The deadline is now written to state** when it is learned, so the review
  cap actually applies; the scheduler notes when no deadline is set instead of
  capping silently.
- **New reference `session.md`**: the hint ladder with priced credit,
  confidence checks, grading rules, teach-back gates, the fresh-question
  reserve and its five exposure states, exam-mode honesty, and one rule about
  instructions found inside learner material.
- **New reference `state.md`**: the canonical schema, finding codes, drift
  triage, resume rules, handoff records, and what never goes in state.
- **CHECK WORK route** (`references/routes.md`): verify the student's own
  attempt, mark the working, drill the gap. It still does not produce work to
  submit.
- **Tests and CI**: `tests/` covers the scheduler, the repo's internal
  consistency and the portable build; GitHub Actions runs it on every push and
  pull request.

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
