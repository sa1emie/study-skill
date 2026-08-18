<h1 align="center">study</h1>
<p align="center">
  <strong>Drills you the way your professor actually tests, not the way a textbook does.</strong>
</p>
<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/sa1emie/study-skill?style=flat" alt="License"></a>
</p>

Point it at your slides, transcripts, past exams, and review-session
recordings. It models what your specific instructor emphasizes, excludes, and
asks, then either drills you against that or builds you a complete study
package from it.

## Install

Pick your tool. Each one is a copy-paste block.

### Claude Code

Skills install globally, so this adapter is self-contained.

```bash
git clone https://github.com/sa1emie/study-skill.git /tmp/study-skill
mkdir -p ~/.claude/skills
cp -r /tmp/study-skill/adapters/claude-code/study ~/.claude/skills/
```

Then type `/study`, or just say what you need ("here are my slides, exam is
Friday") and it triggers on its own.

### Codex, OpenCode, and other AGENTS.md tools

These read a plain `AGENTS.md` from your project root. Run this inside the
folder you want to study in:

```bash
git clone https://github.com/sa1emie/study-skill.git /tmp/study-skill
cp /tmp/study-skill/study.md .
cat /tmp/study-skill/adapters/agents-md/study-section.md >> AGENTS.md
```

Creates `AGENTS.md` if you don't have one.

### Cursor

Cursor rules are project-scoped. Run this inside each project you want it in:

```bash
git clone https://github.com/sa1emie/study-skill.git /tmp/study-skill
cp /tmp/study-skill/study.md .
mkdir -p .cursor/rules
cp /tmp/study-skill/adapters/cursor/study.mdc .cursor/rules/
```

### Plain chat (ChatGPT, Claude.ai, Gemini)

No coding agent needed. Download [`study.md`](study.md), upload it to the chat,
and send:

> Read study.md in full and follow it exactly for the rest of this
> conversation, including the "Degraded mode" section, since you have no file
> system here. Here's my course material.

You lose progress tracking between sessions, so prefer One-shot mode here (see
below), which barely degrades without a file system. Details and the
persistent-project-file workaround in
[`basic-chat/README.md`](basic-chat/README.md).

### Anything else

If your tool can read a file when told to, no adapter is needed. Drop
[`study.md`](study.md) in your project and tell the agent to read and follow
it. That is all any adapter above actually does.

Longer notes, configuration, and quickstart in [INSTALL.md](INSTALL.md).

## Two ways to use it

Same engine underneath. Both read your material the same way, build the same
instructor model, and weight concepts by the same evidence. They differ only
in what you get back.

<table>
<tr>
<td width="50%" valign="top">

### Companion

An ongoing study partner. Drills you, grades honestly, tracks what you miss,
and adapts across sessions.

For people who want to be taught and tested over weeks.

</td>
<td width="50%" valign="top">

### One-shot

A complete study package built from your material: guides, flashcards, Anki
decks, practice exams, cheat sheets. Yours to use with the AI closed.

For people who want to hand over their files, make one decision, and get
something good.

</td>
</tr>
</table>

Pick either on first run. Switch any time, without losing state or re-reading
your material. "Quiz me" turns a One-shot unit into a Companion one; "just
build the guide" goes the other way.

## What changes

<table>
<tr>
<td width="50%">

## Before

> Q: What is the function of the Golgi apparatus?

Same question every study app asks. No idea what your professor actually
tests.

</td>
<td width="50%">

## After

> Skipping the individual electron transport chain complexes, your professor's
> material says know what goes in and out, not memorize each one. Sticking
> close to membranes, since she called that the theme of the whole course.
>
> Q: A protein just left the ER. Which organelle modifies it next? (Her
> wrong-answer options are always adjacent organelles like ER or lysosome,
> never something random like mitochondria.)

</td>
</tr>
</table>

## How it works

Phases 1 to 3 run in both modes and are where the real work happens.

1. **Ingest** reads your material once, classifies each source (a review
   session and a syllabus carry very different signal), and distills it.
2. **Authority model** extracts what your instructor emphasizes, excludes,
   and reuses, every claim tagged `OBSERVED` (a quote), `INFERRED` (a
   pattern), or `SPECULATIVE` (never planned around).
3. **Concept graph** maps prerequisites and weights each concept by evidence,
   not guesswork.

Then it forks on your mode.

**Companion:** picks a drilling method per concept from a library of eleven
based on what kind of thinking it demands, quizzes you without ever leading
with the answer, and writes your progress to disk so nothing gets
copy-pasted between sessions.

**One-shot:** sizes the package to how long you have until the exam,
recommends a combination of outputs, builds them, and hands them over. Every
artifact has to stand on its own with the AI closed and the lecture over.

Full pipeline in [`study.md`](study.md).

## Works for

- University courses, any subject (it detects the shape of the material, no
  hardcoded subject list)
- Standardized exams with a published blueprint (MCAT, NREMT, etc.)
- Certifications
- Self-teaching from books or docs, with no exam at all

## Tune it

Most of it is config, not code. Create `~/study/config.md` to set tone, answer
length, grading strictness, and a default mode (so it stops asking) without
touching anything else. See [INSTALL.md](INSTALL.md#configuration).

For deeper changes, edit [`study.md`](study.md) directly, it's the entire
skill in one file, then resync the Claude Code copy per
[INSTALL.md](INSTALL.md#maintaining-this-repo).

## Privacy

An `authority.md` built from real lectures is a file of quotes attributed to
a named instructor. Keep it local. Don't commit or share one without that
instructor's consent, and check your institution's policy on recording
lectures before building a corpus from them. The example in `examples/` is
entirely fabricated for this reason.

## Credits

Built by [sa1emie](https://github.com/sa1emie), with [Claude](https://claude.com/claude-code)
and [Cursor](https://cursor.com).

Contributions welcome. If you use this for a subject shape the loop library
handles badly, open an issue describing what the material looked like and
what the drilling got wrong. That feedback is more useful than a patch.

## License

MIT.
