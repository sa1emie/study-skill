# State: schema, integrity, resume (full detail)

Loaded from `SKILL.md`. Read before the first write to `mastery.json`, and at
the start of any session on a unit that already exists.

## Canonical shape

`mastery.json` is the only file the scheduler trusts. Four shapes exist in the
wild; only the first is written:

| Shape | What it looks like | Action |
|---|---|---|
| canonical | `{"deadline": .., "concepts": {..}, "tests": [..]}` | use as is |
| types | the concept rows live under a `types` key | `check --fix` |
| flat | concept rows at the top level, metadata mixed in | `check --fix` |
| empty | no file yet | created on first write |

Per-concept fields:

| Field | Type | Meaning |
|---|---|---|
| `score` | 0..1 | EWMA of graded attempts: hit 1, hint 0.5, miss 0, weight 0.3 |
| `attempts` | int | graded attempts so far |
| `interval` | days | current spacing |
| `last` | date | last graded attempt |
| `next_due` | date | when the concept comes back |
| `errors` | list of strings | named error classes, not a diary |
| `implicit` | number | credit inherited from a dependent's hit |
| `override` | bool | the student overrode a grade ("I knew that") |

`deadline` caps every `next_due`, and `tests` holds the pre/post records. Only
the fields above plus `error_patterns` are recognized; `check --fix` drops
anything else, deliberately: a state file stops describing the unit once every
session invents its own keys.

## Writing

- Grades go through the script, never hand-edited:
  `schedule.py <unit> record <id> hit|hint|miss`,
  `schedule.py <unit> test pre|post <correct> <total> --label "<topic>"`.
- `record` refuses an id that is not in `concepts.md` and prints the closest
  ids. That refusal guards against orphan rows. Add the row, use a real id, or
  pass `--force` when the id is genuinely new.
- The deadline is written into `mastery.json` when it is learned, on the same
  call (`record ... --deadline YYYY-MM-DD`) or by editing the file. A deadline
  that lives only in a conversation caps nothing.
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

Exit codes: 0 clean, 1 warnings, 2 errors. Run it after ingesting new material
into an existing unit, at the start of a resumed session, and after any hand
edit. `--json` is for scripting. `--fix` repairs only what is reversible (shape
migration, missing fields, clamped scores, rebuilt dates, dropped unknown
keys) and never deletes a concept row. It re-checks after fixing, so the exit
code describes the file as it now is.

Finding codes, for reading the output fast:

| Code | Severity | Meaning |
|---|---|---|
| `E_PREREQ_SELF`, `E_PREREQ_MISSING` | error | a prereq id in `concepts.md` does not resolve |
| `E_PREREQ_CYCLE` | error | prerequisites form a cycle |
| `E_SCORE_RANGE`, `E_SCORE_TYPE` | error | score outside 0..1, or not a number |
| `E_NEXT_DUE`, `E_DEADLINE` | error | a date field that is not a date |
| `E_INTERVAL` | error | interval not positive |
| `E_ROW_TYPE` | error | a concept row that is not an object |
| `W_ORPHAN` | warning | a state id that is not in `concepts.md` |
| `W_STATE_BEHIND` | warning | a drilled unit whose state covers under half the graph |
| `W_FIELD_MISSING`, `W_FIELD_UNKNOWN` | warning | schema drift inside a row |
| `W_NO_DEADLINE` | warning | reviews are not capped |
| `W_TEST_TOTAL` | warning | an impossible or empty test score |
| `W_LEGACY_SHAPE` | warning | a pre-canonical file |
| `W_NO_GRAPH` | warning | `concepts.md` missing or unparseable, so state cannot be validated |
| `I_UNTRACKED`, `I_STALE_DUE`, `I_FIELD_ABSENT`, `I_UNPAIRED_POST` | info | normal states, no action owed |

## Drift triage

| Finding | Usually means | Do |
|---|---|---|
| Orphan (state id not in the graph) | the id was renamed or the row removed | match it to the closest graph id and rename the state row, or restore the row. Never delete state silently. |
| `W_STATE_BEHIND` | the graph was expanded after drilling, or sessions stopped recording | sweep the untracked ids through one light item each, or leave them untracked so the queue offers them |
| `W_NO_DEADLINE` | the deadline was never learned, or predates this rule | ask once, then write it |
| Missing fields, odd scores, bad dates | a hand-written or legacy file | `check --fix` |
| `I_STALE_DUE` | normal, time passed | nothing; `due` will surface them |
| `E_PREREQ_MISSING`, cycle | a typed wrong id, or a rewritten graph | fix `concepts.md`; the graph owns the ids |

## Legacy migration

`check --fix` rewrites old shapes in place, keeps unknown top-level metadata
(`unit`, `exam`, `register`, notes) and invents nothing. Run it once on every
old unit. State files are local and never committed; the repo's `.gitignore`
already covers them.

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
- Fresh-question items or answers: the reserve lives in `log.md` and in
  artifacts, never in scored state.
- Secrets, student ID numbers, images, or anything the student marked private.
- Invented history. An attempt that was never graded gets no row.
