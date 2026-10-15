# Side routes: math rendering, checking work, chat hand-off

## Math by surface

Most coding-agent terminals cannot render LaTeX. Chat apps and HTML pages can
(usually with KaTeX). Pick the format by where the math will be read:

| Surface | Math goes as |
|---|---|
| Terminal reply | Plain text: `(x^2 - 1)/(x - 1)`, `sqrt(n)`, `x-bar`. Never raw `$...$`. |
| Something the student wants rendered | A `.md` in `out/` with `$...$` / `$$...$$`, to open in a chat app or a Markdown viewer |
| HTML deliverable | KaTeX from a CDN (see `references/design.md`, "Math") |

The first time math appears in a session, say the limit in one line and offer
the `.md`. Before handing over any `.md` with math, validate it:

```bash
cd SKILL_DIR/scripts && npm install --no-save katex   # once
node SKILL_DIR/scripts/katex_check.js out/<file>.md  # exit 0 = everything renders
```

---

## CHAT HAND-OFF: a companion prompt for a chat app

When the student wants to keep studying in a chat app (phone, tablet, a chat
with rendered math), write one self-contained prompt from the unit's files and
save it as `out/<unit>-handoff.md`:

1. **Role**: a tutor that asks one question at a time, waits for the attempt,
   grades the working and the notation, not just the final answer.
2. **Scope**: what the exam covers and what it does not (from `authority.md`).
3. **Canonical notation**: the course's exact formulas and symbols, copied from
   the exams, answer keys or slides. Chat tutors drift to textbook notation
   otherwise, so this section is not optional.
4. **Where the student is**: done, weak (`mastery.json`), never touched.
5. **Error patterns**: the recorded error classes (5C.2 rule 5).
6. **Problem shapes**: 3 to 6 real past problems, rewritten, with the method named.
7. **Rules**: math in `$...$`, one question at a time, a worked example first
   when the student asks to see one solved (5C.2 rule 8).

Run the KaTeX check on the file, then give the path.

---

## CHECK WORK: verifying an attempt

When the student pastes their own attempted work (a solution, a draft, a
problem-set attempt) and asks whether it is right, or says "check my work":

1. **Verify before judging.** Work the problem or re-derive the claim first,
   from the material and the authority's method. Never pattern-match on how
   confident the answer looks.
2. **Grade on the working, not the luck:**
   - right reasoning, right answer: hit, name what was good, one line on what is next
   - right answer, reasoning missing or wrong: hint at best; ask for the reasoning before crediting anything
   - right reasoning, arithmetic slip: keep the method credited, name the error class, log the slip
   - wrong reasoning that lands on a plausible answer: miss; locate the point where the model breaks
3. **One verdict per item**, terse, and every wrong item gets a repair rep on
   the same idea instead of a re-lecture.
4. **Log the outcome.** A checked attempt is a graded attempt;
   `schedule.py record` per item.
5. **The boundary.** This route verifies the student's own work at their
   request. It does not produce a submission for them (Guardrail 8). For graded
   work: coach the method, verify their attempt, hand them a fresh analogue to
   solve, never a clean answer to submit.
