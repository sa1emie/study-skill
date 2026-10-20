---
name: canvas-lookup
description: >
  Read-only lookups in a student's Canvas LMS through the Canvas REST API. Load
  it when the student says "check Canvas", "what's due", "am I free this week",
  "is X graded", "how much is X worth", or mentions a course item you don't
  recognise ("clinic one", "lab 2 prep", "quiz 3"). Load it before building
  anything for a named course item, and before you tell anyone a session has no
  Canvas access. Covers setup, where the token lives, a tested helper script,
  and the rule to look things up instead of guessing.
---

# Canvas lookup

## Setup (once)

1. In Canvas, open Account > Settings and click **New Access Token**. Copy it.
2. Put it in `~/.config/canvas-lookup/.env` along with your school's Canvas
   address:

   ```
   CANVAS_API_URL=https://yourschool.instructure.com
   CANVAS_API_TOKEN=paste-the-token-here
   ```

   Then run `chmod 600 ~/.config/canvas-lookup/.env`. Environment variables
   with the same names take priority, and `CANVAS_ENV_FILE` points the script
   at a different file.
3. Check it: `python3 scripts/canvas.py whoami` should print your name.

Use the `*.instructure.com` host. A school's own vanity domain often serves
the web pages fine and still fails for the API.

## Rule 1: ask the API first

Before answering any question about deadlines or grades, call the API. A
calendar sync, the Canvas ICS feed, or an email digest can't stand in for it:
the ICS feed has been seen returning nothing for an entire semester, and an
agent that trusted it told the student they were free when they weren't. If
the token is on disk, the session has Canvas access. Don't claim otherwise.

## Rule 2: the token stays on disk

The script reads it from the environment or the env file. Nobody prints it,
types it into a command line, or asks for it in chat. On a 401 the token has
expired or been revoked, so tell the student to make a new one (step 1) and
replace the line in the file. Any other tool that shares that token has
stopped syncing too, and that's worth mentioning.

## Rule 3: look it up, then build

When the student names a course item:

1. `canvas.py find <words>` searches every active course: assignments, module
   items, announcements from the last 120 days, and the syllabus body.
2. Never say whether something counts toward the grade until you've run
   `canvas.py groups <course>`. Quote the group weight.
3. If the only mention is in a syllabus file, fetch the syllabus (see below)
   and read it.
4. Still nothing? Ask which course, in one line. Building for a guessed
   context is how a "clinic" assignment worth 15% of a statistics grade ends
   up treated as a hospital shift sheet that "isn't graded".

## The script

`scripts/canvas.py` uses only the standard library and runs on Python 3.9.
It never writes; every call is a GET.

```bash
C=~/.claude/skills/canvas-lookup/scripts/canvas.py
python3 $C whoami
python3 $C courses                          # id | code | name, active courses only
python3 $C planner 2026-09-28 2026-10-04    # due or scheduled in the window, local time
python3 $C announcements 123456 30          # last 30 days, HTML stripped
python3 $C groups 123456                    # weights, points, due dates
python3 $C find clinic                      # search every active course
python3 $C syllabus 123456                  # syllabus text + linked file URLs
```

Plenty of schools link the syllabus as a `.docx` from the syllabus page
rather than writing it inline. `syllabus` prints those links. Some download
without auth; for those, unzip the file and strip the tags out of
`word/document.xml`, working in a scratch folder. Ones that need a login
have to come from the student.

## Gotchas

- Leave `end_date` off a call to `/announcements` and Canvas quietly stops at
  `start_date` plus 14 days. The script always passes it. Raw calls need it
  too, or a post from three weeks ago just isn't there.
- At many schools `/calendar_events?type=event` is empty. For "what's due",
  planner items are the source to trust.
- Some instructors keep slides in Teams, OneDrive, or a course website rather
  than Canvas. When Canvas has no files, say so and suggest where they
  probably live.
