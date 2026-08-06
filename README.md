<h1 align="center">study</h1>
<p align="center">
  <strong>Drills you the way your professor actually tests, not the way a textbook does.</strong>
</p>
<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/sa1emie/study-skill?style=flat" alt="License"></a>
</p>

## Install

🔗 [Installation Instructions](INSTALL.md)

Works with [Claude Code](https://claude.com/claude-code), [Cursor](https://cursor.com),
[Codex](https://openai.com/codex/), [OpenCode](https://opencode.ai), any other
coding agent that can read a project file, and, in a reduced form, plain chat
interfaces with no file system at all.

## What it does

A skill for your AI coding assistant that reads your slides, transcripts, and
review-session recordings, models what your specific instructor emphasizes,
excludes, and asks, then drills you against that instead of against the
textbook.

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

1. **Ingest** reads your material once, classifies each source (a review
   session and a syllabus carry very different signal), and distills it.
2. **Authority model** extracts what your instructor emphasizes, excludes,
   and reuses, every claim tagged `OBSERVED` (a quote), `INFERRED` (a
   pattern), or `SPECULATIVE` (never planned around).
3. **Concept graph** maps prerequisites and weights each concept by evidence,
   not guesswork.
4. **Strategy engine** picks a drilling method per concept from a library of
   eleven, based on what kind of thinking it demands.
5. **Drill** quizzes you, never leads with the answer, grades honestly.
6. **Close** writes your progress to disk. Nothing to copy-paste next time.

Full pipeline in [`study.md`](study.md).

## Works for

- University courses, any subject (it detects the shape of the material, no
  hardcoded subject list)
- Standardized exams with a published blueprint (MCAT, NREMT, etc.)
- Certifications
- Self-teaching from books or docs, with no exam at all

## Tune it

Most of it is config, not code. Create `~/study/config.md` to set tone,
answer length, and grading strictness without touching anything else. See
[INSTALL.md](INSTALL.md#configuration).

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
