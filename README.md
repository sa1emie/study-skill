# study

An AI study coach that turns your course material into adaptive drilling,
built around **how your specific instructor teaches** rather than around what
a textbook thinks is important. Works with [Claude Code](https://claude.com/claude-code),
[Cursor](https://cursor.com), [Codex](https://openai.com/codex/),
[OpenCode](https://opencode.ai), any other coding agent that can read a
project file, and, in a reduced form, plain chat interfaces with no file
system at all.

Most study tools treat a course as a pile of facts. Your exam isn't written by
a pile of facts. It's written by one person who emphasizes certain things,
reuses certain examples, phrases questions a certain way, and skips things the
textbook covers in depth. This skill models that person from the material you
already have, then drills you against it.

## What it actually does

You drop slides, PDFs, notes, or lecture transcripts into a folder. Then:

1. **Ingest** reads each source *once*, classifies it (a syllabus and an exam
   review session carry very different signal), and distills it into small
   files. Later sessions read only the distilled files, so drilling starts
   instantly instead of re-reading your whole corpus.
2. **Authority model** extracts what your instructor emphasizes, what they
   explicitly exclude, the examples they reuse, their terminology, and (when the
   evidence supports it) how they build exam questions.
3. **Concept graph** maps prerequisites and assigns each concept a *yield*
   rating backed by evidence, not vibes.
4. **Strategy engine** picks a drilling method per concept from a library of
   eleven, based on what kind of thinking the concept demands.
5. **Drill** quizzes you, never leading with the answer, and grades honestly.
6. **Close** writes your progress to disk automatically. Nothing to copy-paste.

## The part that makes it different

**Confidence tiering.** Every claim in the instructor model is tagged:

- `OBSERVED`: a verbatim quote exists, and it's cited inline
- `INFERRED`: a pattern across three or more instances
- `SPECULATIVE`: plausible but thin, never planned around

If you have no past exams and no review sessions, the "how they write questions"
section stays **empty** rather than filling up with confident guesses. An empty
section is honest. A fabricated one will misdirect an entire semester.

**Exam review sessions are gold.** A single recorded review session usually
carries more assessment signal than a whole semester of lecture recordings,
because instructors say things like "I didn't cover that, so it won't be on the
exam" and "I write these by changing one word." If you have one, ingest it
first.

**Transcript cleanup is mandatory, not cosmetic.** Auto-transcription mangles
technical vocabulary ("alkylopoids" for "prokaryotes"). The pipeline normalizes
against your typed sources first, logs every correction, and *drops* anything it
can't resolve confidently. A missing concept is recoverable. An invented one
isn't.

## How it's organized

One file is the whole skill: [`study.md`](study.md). It's plain markdown,
written as instructions for any AI agent that can read files, with no
tool-specific syntax in it. Everything under `adapters/` is a thin file, a few
lines each, whose only job is telling a specific tool when to load
`study.md`. Install the adapter for whatever you use.

```
study.md                        the whole skill, tool-agnostic
adapters/
  claude-code/study/             self-contained, for a global install
    SKILL.md
    study.md                     (a copy, see note below)
  cursor/study.mdc                project-scoped rule, points at study.md
  agents-md/study-section.md      snippet for AGENTS.md (Codex, OpenCode, etc.)
basic-chat/README.md            fallback for plain chat UIs, no file system
```

## Install: Claude Code

Claude Code skills install globally and need to be self-contained, so this
adapter carries its own copy of `study.md` alongside `SKILL.md`.

```bash
git clone https://github.com/sa1emie/study-skill.git
mkdir -p ~/.claude/skills
cp -r study-skill/adapters/claude-code/study ~/.claude/skills/
```

Start a Claude Code session and type `/study`, or just describe what you need
("quiz me on this", "here are my slides") and it triggers automatically.

## Install: Cursor

Cursor rules are project-scoped, so this one just points back at `study.md`
rather than duplicating it. Run this inside each project you want it in:

```bash
git clone https://github.com/sa1emie/study-skill.git /tmp/study-skill
cp /tmp/study-skill/study.md .
mkdir -p .cursor/rules
cp /tmp/study-skill/adapters/cursor/study.mdc .cursor/rules/
```

Then ask Cursor to quiz you, drill a topic, or ingest material, in the same
project.

## Install: Codex, OpenCode, and other AGENTS.md tools

A growing set of coding agents read a plain `AGENTS.md` at the project root
for standing instructions. Same idea as the Cursor adapter: `study.md` lives
in your project, and a short section in `AGENTS.md` tells the agent when to
read it.

```bash
git clone https://github.com/sa1emie/study-skill.git /tmp/study-skill
cp /tmp/study-skill/study.md .
cat /tmp/study-skill/adapters/agents-md/study-section.md >> AGENTS.md
```

If you don't have an `AGENTS.md` yet, the command above creates one. If your
tool uses a different standing-instructions file, paste the same section
there instead, minus the HTML comment at the top.

## Install: any other AI coding tool

If your tool isn't listed above but can read a file when told to, you don't
need an adapter. Copy `study.md` into your project and tell the agent to read
it and follow it. That's the entire mechanism every adapter above is doing;
the adapters just automate the "tell it to" part.

## Install: plain chat (ChatGPT, Claude.ai, etc.), no coding agent

No file-reading agent, no project folder. See
[`basic-chat/README.md`](basic-chat/README.md) for the zip-and-upload method.
It works, but it gives up persistence between sessions, which is most of what
this project is for. Use one of the adapters above if you have any way to.

## Quickstart

```bash
mkdir -p ~/study/my-course/raw
# drop slides, PDFs, transcripts, notes into ~/study/my-course/raw/
```

Then:

```
here's the material for my cell bio midterm, exam is in 9 days
```

It ingests, builds the model, and starts drilling. No menus, no setup wizard.

Later sessions:

```
quiz me
```

## Configuration

Optional. Create `~/study/config.md`:

```markdown
tone: terse
answer_length: short
deep_dives_per_session: 2
grading: strict-with-override
```

| Key | Default | Effect |
|---|---|---|
| `study_root` | `~/study/` | Where units live |
| `tone` | `neutral` | `neutral`, `terse` (no praise or padding), or `warm` |
| `answer_length` | `short` | `short` (1 to 10 words) or `full` (paragraphs) |
| `deep_dives_per_session` | `2` | Times per session it asks for a full explanation |
| `grading` | `strict-with-override` | Also `strict` or `self-graded` |
| `style_rules` | none | Free-text output constraints |

Absent file means defaults. It won't ask you about anything the file answers.

## Works for

- University courses (any subject; it detects the shape of the material)
- Standardized exams with a published blueprint (MCAT, NREMT, etc.)
- Certifications
- Self-teaching from books or docs, with no exam at all

It contains no hardcoded course, subject, or instructor list. Subject handling
is derived from the material: a statistics course gets problem-solving drills
for its computational content and interpretive drills for its study-design
content, without anyone configuring that.

## The pedagogy, briefly

The loop library is built on retrieval practice, spaced repetition,
interleaving, elaborative interrogation, and worked-example fading. Two
non-obvious choices:

- **Worked examples before problem solving, then the reverse.** For quantitative
  material, fully worked examples beat problem solving while you're acquiring a
  skill, because cognitive load is the binding constraint before schemas form.
  Once schemas exist, the advantage flips. A tool that picks one method is wrong
  half the time, so this one switches based on your mastery data.
- **Error *type*, not error count.** On quantitative work it tracks whether you
  made an algebra slip, chose the wrong method, or misread the setup. Those need
  completely different remediation, and "you got 6/10" tells you none of it.

Deliberately excluded: rereading, highlighting, and passive summarizing. They
feel productive and barely move retention.

## Privacy

An `authority.md` built from real lectures is a file of quotes attributed to a
named instructor. **Keep it local.** Don't commit or share one without that
instructor's consent, and check your institution's policy on recording lectures
before building a corpus from them.

The example in `examples/` is entirely fabricated for this reason.

## Non-goals

No scheduler, no calendar integration, no flashcard export, no browser
automation, no database, no background jobs. Plain files, runs when invoked.

## Maintaining this repo

`study.md` at the repo root is the only copy anyone should edit. The Claude
Code adapter carries a second copy for the reason explained above (a global
install has to be self-contained); after editing the root file, resync it:

```bash
cp study.md adapters/claude-code/study/study.md
```

The Cursor and AGENTS.md adapters point at `study.md` rather than duplicating
it, so they need no resync.

## Credits

Built by [sa1emie](https://github.com/sa1emie), with [Claude](https://claude.com/claude-code)
and [Cursor](https://cursor.com).

Contributions welcome. If you use this for a subject shape the loop library
handles badly, open an issue describing what the material looked like and what
the drilling got wrong. That feedback is more useful than a patch.

## License

MIT. See [LICENSE](LICENSE).
