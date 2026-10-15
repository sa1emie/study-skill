# Changelog

## 2.2 (2026-10-15)

- **State files fail loudly instead of quietly.** A `mastery.json` that does
  not parse, or whose `concepts` is not a row object, is a named finding
  (`E_STATE_CORRUPT`, `E_STATE_BROKEN`). Every command refuses out of it with
  exit 2 instead of tracebacking, and `check --fix` quarantines the file as
  `mastery.json.corrupt` (bytes preserved, suffixed on collision) rather than
  rewriting it.
- **`record` writes what the docs promised.** `--error CLASS` (repeatable),
  `--confidence 1-5` and `--override` now land in the row, and `--deadline`
  persists into `mastery.json` on the call that learns it, so the review cap
  survives later sessions.
- **Command line errors are explanations, not tracebacks.** Bad dates,
  dangling flags and flags that belong to another command exit 2 with one
  line. The exit code contract is documented: 0 done, 1 warnings or a refused
  write, 2 errors or could not run.
- **Spacing rules.** Intervals cap at 90 days. A first consecutive hint grows
  the interval 1.5x, a second holds it, a third resets to a day. Close to a
  deadline, intervals compress so reviews taper in instead of stacking onto
  deadline day. Constants live at the top of `scripts/schedule.py`.
- **Fresh-question reserve index.** An optional `questions.json` tracks item
  ids and their five exposure states (`questions add`, `questions mark`), and
  `check` warns (`W_RESERVE_LOW`) when a tracked concept drops under its
  unseen floor: 3 high yield, 2 medium, 1 low. Units without the file get no
  nagging.
- **`rename` command** for reconciling a renamed concept row, and repaired
  pairing: a post-test matches the most recent pre-test with the same label
  and notes the day gap when it is long.
- **Hardening elsewhere.** `due`, `record`, `test` and `check` survive
  hand-broken rows (non-object rows, junk scores) without crashing; what only
  a human can fix is printed as cannot-fix lines; `check --fix` never creates
  a missing state file; metadata like `exam` and `unit` survives migration;
  self-prerequisite rows report once; `anki_export.py` survives junk scores
  and unreadable card files.
- **Tests and CI**: 35 new regression tests (73 total), ResourceWarning leaks
  fixed, Python 3.9 added to the CI matrix.

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
