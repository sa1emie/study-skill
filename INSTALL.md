# Install

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
    study.md                     (a copy, see Maintaining below)
  cursor/study.mdc                project-scoped rule, points at study.md
  agents-md/study-section.md      snippet for AGENTS.md (Codex, OpenCode, etc.)
basic-chat/README.md            fallback for plain chat UIs, no file system
```

## Claude Code

Claude Code skills install globally and need to be self-contained, so this
adapter carries its own copy of `study.md` alongside `SKILL.md`.

```bash
git clone https://github.com/sa1emie/study-skill.git
mkdir -p ~/.claude/skills
cp -r study-skill/adapters/claude-code/study ~/.claude/skills/
```

Start a Claude Code session and type `/study`, or just describe what you need
("quiz me on this", "here are my slides") and it triggers automatically.

## Cursor

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

## Codex, OpenCode, and other AGENTS.md tools

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

## Any other AI coding tool

If your tool isn't listed above but can read a file when told to, you don't
need an adapter. Copy `study.md` into your project and tell the agent to read
it and follow it. That's the entire mechanism every adapter above is doing;
the adapters just automate the "tell it to" part.

## Plain chat (ChatGPT, Claude.ai, etc.), no coding agent

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

## Maintaining this repo

`study.md` at the repo root is the only copy anyone should edit. The Claude
Code adapter carries a second copy for the reason explained above (a global
install has to be self-contained); after editing the root file, resync it:

```bash
cp study.md adapters/claude-code/study/study.md
```

The Cursor and AGENTS.md adapters point at `study.md` rather than duplicating
it, so they need no resync.
