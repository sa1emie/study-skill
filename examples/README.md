# Example unit

Everything in `example-unit/` is **fabricated**. The course, the instructor
"Dr. A. Rivera", and every quote are invented to show what the skill produces.
No real person is described.

Real `authority.md` files contain verbatim quotes attributed to a named
instructor, built from their recorded lectures. That is why the example here is
synthetic and why the skill tells you to keep real ones local. Before you build
a corpus from recordings, check your institution's policy on recording lectures.

## What the files show

| File | Shows |
|---|---|
| `authority.md` | The confidence-tiering format. Every OBSERVED claim carries a quote; softer claims are downgraded to INFERRED, and the coverage table up top states how far the model can be trusted. |
| `concepts.md` | Concept rows with shape, prereqs, and yield backed by evidence rather than assertion. |
| `.ingest.json` | Source classification and the vocabulary-normalization audit trail, including tokens that were dropped rather than guessed. |

The pattern worth copying: notice that `authority.md` has a section called
"What this model does NOT support". A model that cannot say what it does not
know will confidently misdirect a whole semester.
