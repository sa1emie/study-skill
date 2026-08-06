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
   > in this zip too, that's what we're studying.

4. **Study normally.** It will ingest whatever you gave it, build the
   instructor model and concept graph in its reply instead of on disk, and
   drill you the same way the full pipeline does.

5. **At the end of the session**, it will give you a short recap block. Save
   that yourself (copy it into a note) and paste it back at the start of your
   next session if you want any continuity. This manual step is the one thing
   the full pipeline exists to eliminate; here, it's the best available option.

## If your platform supports persistent project files

Some chat platforms let you attach a file to a project or custom assistant
once, and it stays available across every conversation in that project
(rather than re-uploading a zip every time). If yours does, upload `study.md`
there instead of doing the zip-and-paste dance each session. It won't give you
real mastery tracking or an ingest folder, but it does mean you stop having to
re-explain the instructions from scratch, which is most of what the zip method
costs you.
