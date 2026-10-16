# State: schema, integrity, resume (full detail)

Loaded from `SKILL.md`. Read before the first write to `mastery.json`, and at
the start of any session on a unit that already exists.

## Canonical shape

`mastery.json` is the only file the scheduler trusts. Six shapes exist in the
wild; only the first is written:

| Shape | What it looks like | Action |
|---|---|---|
| canonical | `{"deadline": .., "concepts": {..}, "tests": [..]}` | use as is |
| types | the concept rows live under a `types` key | `check --fix` |
| flat | concept rows at the top level, metadata mixed in | `check --fix` |
| empty | no file yet, or a file with no recognizable rows | created or canonicalized on the first write |
| corrupt | does not parse as a JSON object | hand fix, or `check --fix` quarantines it |
| broken | parses, but `concepts` is not an object of rows | same as corrupt |

Corrupt and broken files are never rewritten: the bytes could be the only
record of a term's work. Every command refuses out of them with exit 2.
`check --fix` alone moves the file aside as `mastery.json.corrupt` (bytes
preserved, `-2` and `-3` suffix on collision) so a fresh, empty canonical file
can start, and says so.

Per-concept fields:

| Field | Type | Meaning |
|---|---|---|
| `score` | 0..1 | EWMA of graded attempts: hit 1, hint 0.5, miss 0, weight 0.3 |
| `attempts` | int | graded attempts so far |
| `interval` | days | current spacing |
| `last` | date | last graded attempt |
| `next_due` | date | when the concept comes back |
| `errors` | list of strings | named error classes, deduped, written by `record --error` |
| `implicit` | number | credit inherited from a dependent's hit |
| `override` | bool | the student overrode a grade ("I knew that"), written by `record --override` |
| `confidence` | 1..5 | the student's own rating, latest wins, written by `record --confidence` |
| `hint_streak` | int | consecutive hints; drives the hint spacing rule |

`deadline` caps every `next_due`, and `tests` holds the pre/post records. Only
the fields above plus `error_patterns` are recognized; `check --fix` drops
anything else, deliberately: a state file stops describing the unit once every
session invents its own keys.

Spacing rules, so the queue is predictable: a `hit` multiplies the interval by
2.5; a `hint` multiplies by 1.5 on the first consecutive hint, holds on the
second, and resets to 1 day on the third; a `miss` resets to 1 day. Intervals
never exceed 90 days. Near a deadline, an interval that would land past it is
compressed to roughly 60% of the days remaining, so reviews taper in instead of
stacking onto deadline day. These are conventions, not laws; the constants sit
at the top of `scripts/schedule.py` if a unit argues for different ones.

## Writing

- Grades go through the script, never hand-edited:
  `schedule.py <unit> record <id> hit|hint|miss`,
  `schedule.py <unit> test pre|post <correct> <total> --label "<topic>" [--conditions supported|open-book|timed]`.
- `record` refuses an id that is not in `concepts.md` and prints the closest
  ids. That refusal guards against orphan rows. Add the row, use a real id, or
  pass `--force` when the id is genuinely new. `record` also refuses to touch a
  concept row that is not an object; that one needs a human.
- Optional flags on `record`, all written into the row: `--error CLASS`
  (repeatable, deduped) names what broke, `--confidence 1..5` stores the
  student's own rating, `--override` marks a student overrule of the grade.
  These were once documented but unwritable; now they write.
- The deadline is written into `mastery.json` on the `record` call that first
  learns it (`record ID hit --deadline YYYY-MM-DD`), and it stays: every later
  `record` reads it back. A deadline that lives only in a conversation caps
  nothing.
- `schedule.py <unit> rename OLD NEW [--force]` moves a state row onto a new
  id after the row itself was renamed in `concepts.md`. It refuses a new id
  that is not in the graph unless `--force` is passed, and refuses to merge
  two rows; that one is a careful hand job.
- Arguments are checked before anything runs: a bad date, a dangling flag, or
  a flag that does not apply to the command exits 2 with a one-line message,
  never a traceback.
- Write during the session, not at the end.
- One writer at a time. If another session may have run, re-read the file
  before writing.

## Reading at session start

Order: `config.md` if present, then `unit.md`, then:

1. If `mastery.json` exists, run `schedule.py <unit> check`.
2. If it is not clean, say what is off in one sentence and fix it before
   drilling. Never silently drill a queue built from a broken state file.
3. Then `schedule.py <unit> due` for today's queue.
4. Then the pre-test (5C.0). That is the actual reconnect with the material.

Resume rules for the opening message:

- One line of where things stood: last session, weakest area, first due concept.
- Never open a resumed session by asking the student where they got to, and
  never treat their memory of the state as more authoritative than the files.
  Files win; if they disagree with a score, the student may override it.
- If `log.md` has an open loop (a question parked for later, an artifact
  promised), do that first, then the pre-test.
- Do not recap everything. A resume is a sentence, then work.

## The check command

```
python3 SKILL_DIR/scripts/schedule.py <unit> check [--fix] [--json]
```

Exit codes: 0 clean, 1 warnings or a refused write, 2 errors or could-not-run
(bad arguments, unreadable state). The whole script keeps this contract. Run
it after ingesting new material into an existing unit, at the start of a
resumed session, and after any hand edit. `--json` is for scripting and
includes `fixed` and `cannot_fix`. `--fix` repairs only what is reversible
(shape migration, missing fields, clamped scores, rebuilt dates, dropped
unknown keys), never deletes a concept row, never creates a missing state
file, and quarantines a corrupt one instead of rewriting it. What only a
human can fix (a row that is not an object) prints as `cannot` lines and
keeps the exit at 2. It re-checks after fixing, so the exit code describes
the file as it now is.

Finding codes, for reading the output fast:

| Code | Severity | Meaning |
|---|---|---|
| `E_PREREQ_SELF`, `E_PREREQ_MISSING` | error | a prereq id in `concepts.md` does not resolve |
| `E_PREREQ_CYCLE` | error | prerequisites form a cycle |
| `E_SCORE_RANGE`, `E_SCORE_TYPE` | error | score outside 0..1, or not a number |
| `E_NEXT_DUE`, `E_DEADLINE` | error | a date field that is not a date |
| `E_INTERVAL` | error | interval not positive |
| `E_ROW_TYPE` | error | a concept row that is not an object; only a human can fix it |
| `E_STATE_CORRUPT`, `E_STATE_BROKEN` | error | the state file could not be read at all; every command refuses until it is dealt with |
| `W_ORPHAN` | warning | a state id that is not in `concepts.md` |
| `W_STATE_BEHIND` | warning | a drilled unit whose state covers under half the graph |
| `W_FIELD_MISSING`, `W_FIELD_UNKNOWN` | warning | schema drift inside a row |
| `W_NO_DEADLINE` | warning | reviews are not capped |
| `W_TEST_TOTAL` | warning | an impossible or empty test score |
| `W_TEST_ENTRY` | warning | a tests entry that is not an object |
| `W_RESERVE_LOW` | warning | fresh-question reserve under the floor for a tracked or drilled concept |
| `W_QUESTIONS_FILE`, `W_QUESTIONS_ENTRY`, `W_QUESTIONS_ORPHAN` | warning | the reserve ledger is unreadable, an entry is malformed, or it names a concept that is gone |
| `W_LEGACY_SHAPE` | warning | a pre-canonical file |
| `W_NO_GRAPH` | warning | `concepts.md` missing or unparseable, so state cannot be validated |
| `I_UNTRACKED`, `I_STALE_DUE`, `I_FIELD_ABSENT`, `I_UNPAIRED_POST` | info | normal states, no action owed |

## Drift triage

| Finding | Usually means | Do |
|---|---|---|
| Orphan (state id not in the graph) | the id was renamed or the row removed | rename the row in `concepts.md`, then `schedule.py <unit> rename OLD NEW`; or restore the row. Never delete state silently. |
| Corrupt or broken file | a hand edit, a partial write, or disk trouble | `check --fix` quarantines it; restore from the quarantined copy or start fresh |
| `W_STATE_BEHIND` | the graph was expanded after drilling, or sessions stopped recording | sweep the untracked ids through one light item each, or leave them untracked so the queue offers them |
| `W_RESERVE_LOW` | top-ups stopped, or the floor is higher than the bank | add fresh items to `questions.json`, or write more questions into the next artifact |
| `W_NO_DEADLINE` | the deadline was never learned, or predates this rule | ask once, then write it. If the unit honestly has no deadline, say so once; the warning stays deliberately, because a missing deadline on a real exam unit is worse than a nag. |
| Missing fields, odd scores, bad dates | a hand-written or legacy file | `check --fix` |
| `I_STALE_DUE` | normal, time passed | nothing; `due` will surface them |
| `E_PREREQ_MISSING`, cycle | a typed wrong id, or a rewritten graph | fix `concepts.md`; the graph owns the ids |

## Legacy migration

`check --fix` rewrites old shapes in place, keeps unknown top-level metadata
(`unit`, `exam`, `register`, notes) and invents nothing. Run it once on every
old unit. State files are local and never committed; the repo's `.gitignore`
already covers them.

## Fresh-question reserve (questions.json)

The reserve is an index, not a bank: item ids, states, and nothing else. The
questions themselves live in `log.md` and in artifacts; scoring never sees
them. The index exists so the scheduler can warn when drill material is being
spent without top-ups.

```json
{"items": {"q12": {"concept": "c5-lateral-inhibition", "state": "unseen",
                   "last": null}}}
```

```
schedule.py <unit> questions                          # counts by concept, marks LOW
schedule.py <unit> questions add ID CONCEPT [--state S] [--force]
schedule.py <unit> questions mark ID STATE [--date D]
```

States: `unseen`, `seen-correct`, `seen-wrong`, `taught-not-drilled`, `burnt`.
Only `unseen` items are fresh. Floors by yield: high 3, medium 2, low 1. A
floor applies once its concept has an index entry or has been drilled; a unit
with no `questions.json` gets no findings at all, so nothing nags a unit that
never opted in.

## Handoff records (One-shot)

A One-shot unit must be resumable without the session that built it. Record in
`unit.md`: the artifact list with paths and dates, the register, the one-line
authority summary, the label used for in-artifact pre/post tests, and the five
weakest concepts at handoff. A package that cannot be picked up later without
the original chat wasted the build.

## Degraded mode (no files)

Keep the tally in the conversation, print the close block, and say plainly:
"paste this back next session, I will not remember it." Do not claim to have
written a file that does not exist.

## What never goes in state

- Full notes or quotes about a real person. That belongs in `authority.md`, and
  even there it stays local.
- Fresh-question items or answers: the questions live in `log.md` and in
  artifacts; only the id/state index goes in `questions.json`, and it is never
  scored.
- Secrets, student ID numbers, images, or anything the student marked private.
- Invented history. An attempt that was never graded gets no row.
