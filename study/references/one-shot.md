# One-shot track: scope, build, handoff (Phases 4O-6O, full detail)

Loaded from `SKILL.md`. Read this file before doing the work it covers.

## Phase 4O: Scope the package (One-shot)

### 4O.1 Establish the timeline

Deadline comes from the material (or an LMS integration, if the agent has one)
first. Only ask if neither has it, and then ask exactly once: "How long until the exam?"

No deadline and no exam (self-teaching, curiosity): skip urgency entirely and
build for depth.

### 4O.2 Recommend, then let them choose

Recommend a combination and say why in one or two sentences. Defaults, not rules.
The student can override, add, or ask for everything.

| Time to assessment | Default recommendation |
|---|---|
| Weeks or more | Comprehensive guide + concept map + flashcards + practice questions |
| About a week | High-yield guide + flashcards + targeted practice |
| A few days | Compressed high-yield guide + rapid-review sheet + practice questions |
| Under a day | Emergency review sheet, highest-yield concepts only, + focused questions |
| No deadline | Comprehensive guide + flashcards, spaced for the long run |

Weight the recommendation by what the corpus can actually support: amount and
type of material, assessment evidence, concept shapes, coverage gaps. A corpus
with zero `assessment` sources cannot support a credible practice exam, so do
not offer one as though it could. Say what is missing instead.

### 4O.3 Output menu

Offer these in one message, multi-select. Never one at a time.

| Output | Best when |
|---|---|
| Comprehensive study guide | Time exists, material is broad |
| High-yield review guide | Time is short, evidence separates high yield from low |
| Cheat sheet / rapid-review | Day before, or an allowed reference sheet |
| Flashcards (HTML) | `discrete-fact` heavy, wants browser or phone |
| Anki deck, misses only (`scripts/anki_export.py`) | ONLY if the student uses Anki or another SRS app (or `uses_anki: true`); never offered otherwise |
| Practice quiz | Wants self-testing without the answer key spoiling it |
| Practice exam | `assessment` sources exist to model item patterns on |
| Concept map | `mechanism` heavy, relationships matter more than facts |
| Diagrams (SVG + PNG) | Any pathway, anatomy, cycle, comparison, or "how X connects to Y" concept. Offered by default |
| Explainer video (narrated, 60-120 s) | The 1-3 highest-yield `mechanism` or `quantitative` concepts, especially ones the student keeps missing. Offered by default when time is a day or more |
| DOCX guide | Wants to print, annotate, or hand to someone else |

If the student asks for everything, build everything genuinely useful. Do not build a
comprehensive guide AND a high-yield guide AND a cheat sheet off one thin corpus.
That is three copies of the same content wearing hats. Say so, build the two that
actually differ.


---

## Phase 5O: Build (One-shot)

### 5O.1 The standalone standard

**Every artifact must work with the AI closed and the lecture over.**

A thin summary that only makes sense sitting next to the original slides is a
failure of this phase. Each artifact carries enough explanation, worked examples,
relationships, and distinctions to be studied from directly.

Concretely, a study guide entry includes: what the concept is, the mechanism or
procedure in full, the authority's canonical example when one exists, the
distinction from whatever it gets confused with, and how it has actually been
assessed.

### 5O.2 Grounding, unchanged

The evidence hierarchy from Phases 1 to 3 governs every artifact.

- Course-grounded content is the core of the package.
- Supplemental knowledge is allowed where it genuinely helps, and is visibly
  labeled as supplement. Never blended in silently.
- Gaps are named, not filled by invention. "The material does not cover X" is a
  legitimate line in a study guide, and a useful one.
- Yield ordering in the artifact is the yield already in `concepts.md`. Do not
  re-guess importance at render time.
- Authority terminology and canonical examples survive into the artifact.

### 5O.3 Generation

Build the files. Do not describe how they could build them.

| Artifact | How |
|---|---|
| HTML anything | `references/design.md` and `assets/template.html`. Open it in a browser and look before claiming done. |
| DOCX | Your agent's DOCX tool if it has one (for Claude, the docx skill); otherwise write Markdown and convert with `pandoc guide.md -o guide.docx` |
| Anki | Only if the student uses Anki. `python3 scripts/anki_export.py <unit> cards.json`: misses only, `.apkg` if genanki is installed, else an Anki-ready TSV. Say which one was produced. |
| Concept map | Inline SVG, or a mermaid diagram inside the HTML guide |
| Diagram | `references/visual.md` |
| Explainer video (+ questions page) | `references/visual.md` |
| Predict-then-drag simulation | `references/visual.md` |
| Everything else | Markdown in `out/`, unless the student named a format |

Artifacts land in `out/`. Record what was built, and when, in `unit.md`.

### 5O.4 Register inside the artifact

Every artifact is written at the unit's `register:`. At `register: plain`, follow
the voice guide in `references/register.md`; `references/design.md` owns the
look and the components.

**Required structure per section at `register: plain`:**

1. **Plain-language box first.** What the thing is, in normal words, with one
   concrete analogy. No symbols before the reader knows what they are looking at.
2. **A trigger-to-action block.** Two columns: what the problem looks like on the
   left, what to do on the right. This is the part the student will actually use under
   time pressure, so it gets to be scannable, not prose.
3. **Worked example, then practice.** Unchanged from `standard`.
4. **The mechanism, demoted but present.** A collapsed `<details>` in HTML, an
   appendix or an indented block in DOCX and Markdown. Label it optional. Never
   delete it. Demotion is the whole technique; deletion is a different and worse
   artifact.

**Also at `plain`:** open the package with a single no-theory page holding every
decision rule and formula in the unit. Most of the value of a `plain` package is
concentrated there, and it is the page they will reopen.

**At `register: standard`,** run the existing structure: mechanism inline,
reasoning visible, no toggles.

Two failure modes to avoid, both seen in practice:

- **Deleting the depth instead of demoting it.** Then the artifact cannot be
  grown into and has to be rebuilt when they want more.
- **Writing a `plain` shell around `standard` prose.** If the collapsed block
  and the plain box say the same thing at the same reading level, you added
  a toggle and no value.


---

## Phase 6O: Handoff (One-shot)

Append to `log.md`, then print at most four lines:

```
Built: <artifact>, <artifact>
Location: <study_root>/<unit>/out/
Start with: <the one to open first, and why>
```

Then, once, in plain language:

"I still have your material and study model loaded. Come back any time to ask
about something, get quizzed, add flashcards, or switch this to Companion."

Do not imply they have to. The entire point of One-shot is that they already
have what they need.


---

## The student One-shot exists for

Optimize for the student who says:

> "I don't really want to use AI. Here are all my materials. Just make me
> something good."

They should hand over material, make one mode decision and one output decision,
and receive a complete package. That is the whole interaction. Not a tutoring
session that eventually produces files.

This is a hard constraint, not a preference. Most students who reach for this
want a few high-value uses right before an exam, not a study relationship. Every
extra question asked between "here's my material" and "here's your package" is
friction charged to someone who already told you they did not want to be here.

Companion remains fully available for students who do want the ongoing version.
Serving one of them is never a reason to tax the other.
