# Concept graph: BIOL 200 (EXAMPLE, fabricated)

> Fabricated illustration. See `examples/README.md`.

| id | name | shape | prereqs | yield | evidence |
|---|---|---|---|---|---|
| membrane-structure | Phospholipid bilayer organization | mechanism | none | high | OBSERVED, "anything involving a membrane, I care about" |
| passive-transport | Simple vs facilitated diffusion | mechanism | membrane-structure | high | OBSERVED, canonical turnstile example reused across lectures |
| active-transport | Primary vs secondary active transport | mechanism | passive-transport | high | INFERRED, re-explained in 3 lectures, no explicit flag |
| endocytosis-types | Phagocytosis, pinocytosis, receptor-mediated | discrete-fact | membrane-structure | medium | OBSERVED terminology note, "write pinocytosis on the test" |
| etc-complexes | Individual electron transport chain complexes | discrete-fact | none | low | OBSERVED exclusion, "you do not need to memorize the individual complexes" |

Note the last row. A concept with an OBSERVED exclusion quote is worth keeping
in the graph at `low` yield rather than deleting it, so a later session does not
rediscover it from the textbook and quietly promote it back.
