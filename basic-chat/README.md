# Using this without a coding agent

Everything above assumes an AI tool that can read and write files on its own
across sessions (Claude Code, Cursor, Codex, OpenCode, etc.). If you only have
a plain chat interface with file upload (ChatGPT, Claude.ai, Gemini, and
similar), you can still use this, just with less of it working.

**Be honest with yourself about the tradeoff first.** The whole point of the
adapters above is a real file system: material gets ingested once, the
instructor model and your progress persist on disk, and nothing has to be
copy-pasted between sessions. None of that survives in a chat window with no
file system. You will be re-explaining your progress by hand, which is exactly
the failure mode this project exists to avoid. Use an adapter above if you can.
This is the fallback for when you genuinely can't.

**Which mode to use here.** The two modes degrade very differently without a
file system:

- **One-shot works nearly as well.** It reads your material, builds the model,
  and hands you a study guide, flashcards, and practice questions in the
  conversation. You copy those out once and you own them. Nothing needs to
  survive to next session, so nothing is lost. If you only have a chat window,
  this is the mode to use.
- **Companion is the one that suffers.** Its whole value is remembering what
  you missed and scheduling it back. With no `mastery.json` that memory is
  gone, and every session restarts blind unless you hand-carry a recap.

Ask for One-shot explicitly in your first message and you skip the question.

## How to do it

1. **Zip the instructions.** From this repo:

   ```bash
   zip study-kit.zip study.md
   ```

   Optionally add your own material to the same zip (slides exported as text,
   a lecture transcript, your notes) so it all uploads together.

2. **Upload the zip** to your chat interface using its normal file upload.

3. **Paste this priming prompt** as your first message:

   > Unzip and read study.md in full. It's a complete instruction set for
   > acting as an adaptive study coach. Follow it exactly for the rest of
   > this conversation, including the "Degraded mode" section near the end,
   > since you don't have a file system here. If I attached course material
   > in this zip too, that's what we're studying. Use One-shot mode.

   Drop the last sentence if you want it to drill you instead of building you
   a package, or if you want it to ask.

4. **It ingests and delivers.** In One-shot it builds the instructor model and
   concept graph, then writes out your study guide, flashcards, and practice
   questions in the conversation. In Companion it drills you the same way the
   full pipeline does, just without saving anything.

5. **Copy out what you want to keep.** One-shot artifacts are yours once
   pasted into a doc. In Companion, it will give you a short recap block at
   the end; save that and paste it back next session if you want continuity.
   That manual step is the one thing the full pipeline exists to eliminate,
   and here it is the best available option.

## If your platform supports persistent project files

Some chat platforms let you attach a file to a project or custom assistant
once, and it stays available across every conversation in that project
(rather than re-uploading a zip every time). If yours does, upload `study.md`
there instead of doing the zip-and-paste dance each session. It won't give you
real mastery tracking or an ingest folder, but it does mean you stop having to
re-explain the instructions from scratch, which is most of what the zip method
costs you.
