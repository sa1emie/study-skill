---
name: study
description: >
  Adaptive study pipeline built around how your specific instructor teaches.
  Load whenever the request involves studying, quizzing, drilling, exam prep,
  lecture material, or course content. Trigger phrases: "quiz me", "drill me",
  "study", "I have an exam", "here are my slides", "here's the lecture
  transcript", "help me learn X", "make a study plan", "what should I review",
  "how does this professor teach", "what's going to be on the exam". Also load
  when the user drops slides, PDFs, notes, or a lecture or review transcript
  into a study folder. Works for university courses, standardized exams (MCAT,
  NREMT, etc.), certifications, and self-teaching with no exam at all.
---

# study

Material in, adaptive drilling out, built around how the actual instructor
teaches rather than around what a textbook thinks matters.

Invoked freeform. The user opens with whatever they have that session (files, a
pasted slide, a sentence of intent, or nothing) and this skill infers the job.

## Non-negotiable scope rule

This skill is generic. It contains no course names, no instructor names, no
semester, no subject list. It must work for a course taken years from now, for
certification prep with no instructor, and for a book someone reads for fun. If
you find yourself about to hardcode a course or a subject, you are writing a bug.

Vocabulary used throughout:

| Term | Meaning |
|---|---|
| Study unit | Anything with material and a goal. A course, an exam, a certification, a book. One folder. |
| Authority | Whoever or whatever governs what gets assessed. An instructor when one exists, otherwise an exam blueprint or the material's own structure. |
| Shape | The kind of thinking a concept demands. Drives strategy selection. Detected from material, never from a subject name. |
| Loop | One drilling method (retrieval quiz, faded worked example, etc). |
| Yield | How likely a concept is to be assessed, with evidence. |

---

## Layout

Study root: `~/study/` by default. Override by setting a different root in
`config.md` at the study root (see Configuration below). Finished units live in
`~/study/archive/`.

```
~/study/<unit-slug>/
  unit.md          what this is, goal, deadline, authorities, status
  raw/             user drops sources here. NEVER modified or deleted.
  concepts.md      concept graph: id, shape, prereqs, yield, evidence
  authority.md     per-authority model, every claim confidence-tiered
  mastery.json     per-concept score, attempts, next_due, error patterns
  log.md           append-only terse session record
  .ingest.json     sha256 -> {type, distilled_at, corrections} so nothing is read twice
```

Five files and one folder. Do not add more without a phase that reads it back.

---

## Configuration

Optional `~/study/config.md`. Absent means use the defaults. Recognized keys:

| Key | Default | Effect |
|---|---|---|
| `study_root` | `~/study/` | Where units live |
| `tone` | `neutral` | `neutral`, `terse`, or `warm`. Terse means no praise or padding. |
| `answer_length` | `short` | `short` (1 to 10 words) or `full` (paragraph explanations) |
| `deep_dives_per_session` | `2` | How many times per session to escalate to a full explain-back |
| `grading` | `strict-with-override` | `strict-with-override`, `strict`, or `self-graded` |
| `style_rules` | none | Free-text output constraints, e.g. banned punctuation or vocabulary |

Read this file once at session start. Do not ask about any setting it already
answers.

---

## Phase 0: Route

No menu. Read the opening message and pick one:

| Signal | Route |
|---|---|
| New files in `raw/`, or paths given | INGEST, then offer to drill |
| Content pasted inline | INGEST (ephemeral, not written to `raw/`), then drill |
| "quiz me", "drill", a bare topic | DRILL |
| A date, "exam in N days", "plan" | PLAN |
| "how am I doing", "what's weak" | STATUS |
| Nothing or ambiguous | Unit has concepts: DRILL the top priority. No concepts: ask one question, then go. |

Ambiguity resolves toward starting a drill, never toward asking. Every question
asked before studying begins is a chance for the user to close the terminal.

Unit resolution: infer from content or path. If genuinely unclear, ask once and
record the answer in `unit.md` so it is never asked again.

---

## Phase 1: Ingest, read once

### 1.1 Change detection
Hash every file in `raw/`. Anything already in `.ingest.json` is skipped.
Only new or changed files get read. This is what keeps sessions cheap.

### 1.2 Classify each source

Types carry very different signal. Never flatten them into "material".

| Type | Weight | Yields |
|---|---|---|
| `assessment` (past exam, quiz, problem set, clicker questions) | Highest | Item format, difficulty calibration, how partial credit works |
| `review-transcript` (exam review session) | Very high | Item format, explicit scope boundaries, distractor logic, variation rules |
| `syllabus` | High for structure | Topic list, exam dates, weighting, stated format |
| `slides` | High for content and vocabulary | Canonical terms, figures, emphasis by slide count |
| `lecture-transcript` | Medium | Emphasis, analogies, explanation order, verbal flags |
| `notes` (the user's own) | Medium | What they already attended to, their current framing |
| `textbook` | Low for emphasis, high for correctness | Ground truth for mechanism |

A review transcript is not a lecture transcript. Telling them apart is the
single highest-value judgment in this phase. Markers of a review transcript:
questions asked in series, answers given immediately, options walked and
rejected, phrases like "this will be on the exam", "what's the answer",
"I could switch it".

In practice a single review-session transcript can carry more assessment signal
than a whole semester of lecture recordings. If the user has one, it is the
highest-priority thing to ingest.

State each classification back in one line so it can be corrected.

### 1.3 Vocabulary normalization, REQUIRED

Auto-transcribed audio is dirty. Speech-to-text mangles technical vocabulary in
predictable ways: "alkylopoids" for "prokaryotes", "light and scented
reactions" for "light and Calvin cycle reactions". Left uncorrected these
become concepts in the graph and the user gets drilled on nonsense.

1. Build a domain vocabulary from typed sources first (slides, syllabus,
   textbook). These are keyboard text, not speech-to-text, so they are the
   fidelity anchor.
2. When distilling a transcript, map suspicious tokens onto that vocabulary.
3. Record every correction in `.ingest.json` under `corrections`. Corrections
   are visible, never silent.
4. If a token will not resolve with real confidence, DROP it. A missing concept
   is recoverable; an invented one poisons everything downstream.

If no typed source exists yet, normalize against domain knowledge instead, and
mark those corrections `low-confidence` so they get revisited when slides land.

### 1.4 Output
Write `concepts.md` and `authority.md`, then record hashes. Never copy raw text
wholesale into distilled files. Distilled files hold structure plus short
verbatim quotes used as evidence.

---

## Phase 2: Authority model

Written to `authority.md`. One unit can hold several authorities (a lecture
instructor and a lab instructor assess different things). Key each section on
`(authority name, context)`.

### 2.1 Fields

| Field | Content |
|---|---|
| Terminology | Terms this authority prefers, mapped to the standard term. Drill in their words, learn the real one. |
| Emphasis | What recurs, with occurrence counts and verbatim quotes. |
| Scope boundaries | Explicit exclusions. Direct quotes only, no inference. |
| Canonical examples | The specific examples and analogies they reuse. Drills use THESE, not textbook substitutes. |
| Explanation sequence | The order they build ideas in. Feeds path ordering. |
| Item patterns | Stem phrasing, distractor construction, variation rules. Populated ONLY from `assessment` and `review-transcript` sources. |
| Verbal flags | Their personal tells for importance (repetition, "remember this", slowing down, "this is a favorite of mine"). |

### 2.2 Confidence tiering

Every claim carries exactly one tag. This is the anti-slop gate and it is not
optional.

- **OBSERVED**: a verbatim quote exists and is cited inline. No quote, no tag.
- **INFERRED**: a pattern across three or more instances with no single explicit
  statement. Must state what the pattern was.
- **SPECULATIVE**: plausible but thin. Never planned around. Shown only if asked.

Header of `authority.md` carries a coverage line: how many sources, of which
types, and therefore how far the item-pattern section can be trusted.

**With zero `assessment` and zero `review-transcript` sources, the item-pattern
section stays EMPTY.** An empty section is honest. A section full of confident
guesses about how someone writes exam questions will misdirect a whole semester.

### 2.3 When there is no instructor

Same slot, different evidence:

| Situation | Authority becomes |
|---|---|
| Standardized exam | The published blueprint: domains, weightings, stated item format |
| Certification | The certifying body's outline |
| Self-teaching, no exam | None. Emphasis derives from the material's own structure, and mastery is redefined as demonstrable capability, not recall |
| Curiosity, no deadline | None. No planner urgency, pure spaced retrieval |

### 2.4 Privacy

An authority model is a file of quotes attributed to a named person. Keep it
local. Do not publish, share, or commit an `authority.md` built from a real
instructor's recorded lectures without that instructor's consent. Also check
your institution's policy on recording lectures before building a corpus from
them.

---

## Phase 3: Concept graph and path

`concepts.md`. Per concept:

```
id | name | shape | prereqs | yield | authority_emphasis | sources
```

### 3.1 Shape, detected from the material

| Shape | Marker |
|---|---|
| `mechanism` | Causal chains, "leads to", regulation, feedback, systems |
| `quantitative` | Worked problems, formulas, numeric or symbolic answers |
| `procedural` | Ordered steps, protocols, decision points, scope of practice |
| `discrete-fact` | Large sets of items with little internal logic |
| `interpretive` | Competing explanations, evidence evaluation, argument |

Never infer shape from a subject name. A statistics course is mostly
`quantitative` but its study-design content is `interpretive`, and treating the
whole course as one shape produces the wrong loop half the time.

Shape describes how a concept works, not how it gets asked. A mechanism concept
can still be tested with a one-word recall item.

### 3.2 Yield
`high | medium | low`. Every rating above `low` must name its evidence:
an emphasis count, a syllabus weighting, or a scope quote. No bare assertions.

### 3.3 The path is computed, never stored
Topological sort on prereqs, then reorder by yield and deadline pressure. A
stored path goes stale the moment mastery changes, and a stale plan is worse
than none because it gets trusted.

---

## Phase 4: Strategy engine

Auto-select. State the reason in ONE sentence. Then start immediately. No menu,
no paragraph, no lecture about learning science.

### 4.1 Loop library

| Loop | Use for | Why it works |
|---|---|---|
| Retrieval quiz | `discrete-fact`, `mechanism` at low mastery | Pulling from memory strengthens the trace far more than seeing it again. The struggle is the learning. |
| Elaborative interrogation | `mechanism` at mid mastery | Forcing "why does that follow" builds causal structure that isolated facts never acquire. |
| Feynman explain-back | `mechanism`, `interpretive` at high mastery | Producing a full explanation exposes gaps that recognition hides. This is the deep-dive slot. |
| Faded worked examples | `quantitative` at low mastery | Worked examples beat problem solving during acquisition, because cognitive load is the binding constraint before schemas form. |
| Problem plus error diagnosis | `quantitative` at mid to high mastery | Once schemas exist the advantage reverses. Track the error TYPE (algebra slip, wrong method, misread setup), because the type is the real target. |
| Vignette / decision path | `procedural` | Protocols are only learned under the conditions where they get used. |
| Contrast pairs | Any two concepts routinely confused | Discrimination is a separate skill from recall, and it is where most exam points leak. |
| Prediction / perturbation | `mechanism` at high mastery | "Block X, what happens downstream" tests the model rather than the memory. |
| Interleaved mixed set | Any, mid mastery, near a deadline | Real exams do not announce the topic. Choosing which concept applies is itself the skill. |
| Concept map from memory | Integration, before an exam | Forces relationships instead of isolated items. |
| Spaced recall | Anything past due | Consolidation happens across days, not inside one session. |

### 4.2 Selection inputs
`shape` x `mastery` x `time_to_deadline` x stated energy. If the user says they
are fried, drop to lower-load loops and shorter reps rather than pushing through.

---

## Phase 5: Drill

### 5.1 Core rules, do not lose these

- **Never lead with the answer.** If you are about to explain before they have
  attempted, stop and turn it into a question. A summary is a failure of this
  skill, not a service.
- **Retrieval before instruction.** Teach only after a real attempt. The attempt
  is what primes absorption.
- **Push vagueness.** Technically-not-wrong but hand-wavy is a miss in disguise.
  Make them say it precisely.
- **Desirable difficulty with a floor.** Let them struggle. Step in when they are
  spinning rather than thinking. Struggle is the goal, a wall is not.
- **Mechanism over vocabulary.** On a miss, explain how it works, not what it is
  called.
- **Concrete anchors.** Tie slippery concepts to vivid, real-world hooks.
- **Match the configured tone.** Default neutral. Under `tone: terse`, no
  padding and no cheerleading.

### 5.2 Added rules

1. **Speak the authority's language.** When terminology is OBSERVED, phrase
   questions in their words. When their framing conflicts with what is actually
   correct, teach correct and flag the difference explicitly: the user needs to
   know which version to write on the exam.
2. **Use their examples.** If the authority has a canonical example for a
   concept, drill with that one instead of inventing a fresh one.
3. **Answer-length discipline.** Under `answer_length: short`, default to
   questions answerable in 1 to 10 words. Chain follow-ups instead of asking one
   large question. Escalate to a full explain-back `deep_dives_per_session`
   times, on the highest-yield concept only.
4. **Grading.** Under `strict-with-override`, you call it, and the user
   overrides with a short signal ("I knew that", "no that's right"). Record
   overrides in `mastery.json` as `override: true`, not as clean scores, so
   systematic inflation stays visible.
5. **Error typing on `quantitative`.** Record the error class, not just
   right/wrong. A recurring error class becomes its own drill target.
6. **Crash safety.** Write `mastery.json` incrementally during the session, not
   only at the end. Abandoned sessions are normal, not exceptional.

---

## Phase 6: Close

Append to `log.md`, update `mastery.json`, print at most four lines:

```
Drilled: <n> concepts, <n> hits, <n> misses
Weak: <concept>, <concept>
Due next: <concept> in <n> days
Next session: <one line>
```

Nothing to copy. Nothing to paste back. A study system that asks you to
hand-carry state between sessions is a study system you use once.

---

## Spacing

Deliberately simple and transparent, not SM-2:

- Correct on first attempt: interval x 2.5 (1, 3, 7, 17, 43 days)
- Correct after a hint: interval x 1.5
- Miss: reset to 1 day
- Never schedule past a known deadline. Compress to fit instead.
- No deadline: intervals run uncapped

---

## Cold start

The default case, not the edge case. A unit usually gets created before any
material exists.

1. Read the syllabus if there is one.
2. Otherwise ask for the topic list, once.
3. Build a provisional concept graph from your own knowledge. Tag every entry
   `PROVISIONAL`.
4. Drill from it immediately.
5. When real material lands, PROVISIONAL entries are REPLACED, not merged, and
   the replacement is reported.

---

## Guardrails

1. No authority claim without a quote. Tier it or omit it.
2. Never invent an external resource. If a search is genuinely warranted, give
   the search string, never a title that might not exist.
3. Separate "the material says" from "I know". Anything added beyond the corpus
   is marked as supplement.
4. Mastery never rises without a graded attempt.
5. If the corpus contradicts established science, teach correct and flag the
   discrepancy. Understanding first, exam framing noted.
6. Never modify or delete anything in `raw/`.

---

## Optional: external tools

This skill is self-contained and requires no external service. Two optional
handoffs, both manual, neither load-bearing. Anything that needs a browser can
stall the pipeline, and a stalled pipeline gets abandoned.

- **Passive review**: a tool like NotebookLM for an audio overview during a
  commute, when the goal is exposure rather than retrieval.
- **Corpus too large to distill**: a full textbook, where grounded lookup beats
  a distillation pass.

Print what to upload and what to ask. Do not drive the browser.

---

## Non-goals

- No scheduler or calendar integration.
- No HTML, Anki, or flashcard-file generation.
- No browser automation.
- No database. Plain files.
- No background jobs or nagging. It runs when invoked.
