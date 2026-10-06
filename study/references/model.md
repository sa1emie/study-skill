# Ingest, authority model, concept graph (Phases 1-3, full detail)

Loaded from `SKILL.md`. Read this file before doing the work it covers.

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
| `notes` (the student's own) | Medium | What they already attended to, their current framing |
| `textbook` | Low for emphasis, high for correctness | Ground truth for mechanism |

A review transcript is not a lecture transcript. Telling them apart is the
single highest-value judgment in this phase. Markers of a review transcript:
questions asked in series, answers given immediately, options walked and
rejected, phrases like "this will be on the exam", "what's the answer",
"I could switch it".

State each classification back in one line so it can be corrected.

### 1.3 Vocabulary normalization, REQUIRED

Auto-transcribed audio is dirty. Real examples from transcripts: "alkylopoids"
(alkaloids), "light and scented reactions" (light-dependent reactions). Left
uncorrected these become concepts in the graph and the student gets drilled on
nonsense.

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

### 3.2 Yield
`high | medium | low`. Every rating above `low` must name its evidence:
an emphasis count, a syllabus weighting, or a scope quote. No bare assertions.

### 3.3 The path is computed, never stored
Topological sort on prereqs, then reorder by yield and deadline pressure. A
stored path goes stale the moment mastery changes, and a stale plan is worse
than none because it gets trusted.

