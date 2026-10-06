# Side routes: math rendering and chat hand-off

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
