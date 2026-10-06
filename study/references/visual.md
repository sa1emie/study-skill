# Visual outputs: diagrams, explainer videos, simulations

Simple words first, then diagrams, then narrated explainer videos and
"predict, then drag" simulations. For `mechanism` concepts, offer a diagram
and, for the top one to three, a short video, in both modes.

Evidence note: retrieval practice and worked examples are well supported. There
is no controlled study yet showing AI-made diagrams or narrated video raise exam
scores, and unrestricted AI help is known to hurt unaided exam performance. So
visuals are exposure, never a replacement for the attempt-first drill: every
video ends in questions, and every simulation starts with a prediction.

## Diagrams

| Content | Tool |
|---|---|
| Pathways, anatomy-like schematics, crossings, gradients | Hand-written SVG, rendered to PNG (`rsvg-convert -w 1920 x.svg -o x.png`, or open in a browser and screenshot) |
| Flows, decision trees, hierarchies | Mermaid or Graphviz inside the HTML guide |
| Numbers that change (a curve, a bar profile) | A matplotlib PNG, or a Manim still |

Rules:
- Color carries one meaning, stated in the subtitle ("color = which half of
  the visual field").
- Cite the source in the subtitle (slide numbers, chapter).
- Labels sit beside the art with a leader line, never on top of a line.
- Use the palette in `references/design.md`.
- **Render to PNG and look at it before delivering.** Fix every overlap.
- Save in `out/diagrams/` and embed in the HTML guide.

## Explainer videos (3Blue1Brown style, local, free)

Manim Community for animation plus Kokoro-82M for narration. Both run locally;
no API key. One-time setup (about 1.2 GB):

```bash
bash SKILL_DIR/scripts/explainer/setup.sh     # prints the venv python path
```

| File | Job |
|---|---|
| `scripts/explainer/tts.py` | beats.json to one WAV per beat, `narration.wav`, `timing.json` |
| `scripts/explainer/narrated.py` | `NarratedScene` base: `with self.beat(i):` pads each beat to its audio length, logs overruns and off-frame objects; palette and `T()` text helper |
| `scripts/explainer/make.py` | TTS, Manim render, mux, `frames.png` contact sheet, and the questions page |
| `scripts/explainer/page.py` | The player page: video, then retrieval questions with hidden answers |
| `examples/lateral_inhibition.*` (repo) | A complete reference build |

```bash
cd <unit>/out/video
~/.local/share/explainer/venv/bin/python SKILL_DIR/scripts/explainer/make.py \
  topic.py SceneClass topic.json topic-dir [--draft] [--voice am_michael]
```

Procedure:
1. Pick one concept. Write 6 to 9 beats in `topic.json`: a hook (a puzzle or
   illusion from the material), the definition in the authority's words, a
   worked example with real numbers, the payoff, then the exam cue ("if the
   question says X, answer Y"). Narration at the unit's register. About 90 s.
2. Add `"questions"`: 3 to 5 retrieval questions with answers, one per key
   beat. `make.py` refuses to run without them.
3. Write `topic.py`: one `with self.beat(i):` block per beat. Use `T()` /
   `Text()` only; `MathTex` needs a LaTeX install. Clear the screen between ideas.
4. Run with `--draft` first (480p, under a minute). Read `warnings.json` and
   LOOK at `frames.png`. Fix overlaps, labels on lines, arrows pointing the
   wrong way. Then render without `--draft` (1080p60).
5. Deliver the player page (`<SceneClass>.html`) with one line: length, beats,
   what was checked.

Known failure modes: text over lines or bars, labels landing on the wrong
element after a `Transform`, a beat's animations running past its audio (the
base class logs it), stale render folders (make.py takes the newest).

Settings: `EXPLAINER_HOME` (install location), `EXPLAINER_FONT` (default Avenir
Next on macOS, DejaVu Sans elsewhere), `--voice` (any Kokoro voice, e.g.
`af_heart`, `am_michael`, `bf_emma`).

## Predict, then drag simulations

For `quantitative` concepts and `mechanism` concepts with a knob (a rate, a
strength, a dose, a parameter). Interactive simulations have moderate evidence
behind them, and predicting first is the attempt-first rule in another form.

Copy `scripts/sim/predict-drag.html` to `out/sims/<topic>.html` and edit only
the `SIM` object: title, subtitle with sources, question, options, answer,
controls, `model()`, `readout()`, explain, followups. The page contract:

1. One prediction question with 3 options. Sliders stay locked until a pick.
2. Sliders drive a live SVG plot. Keep the model honest: clamp physical limits
   (a firing rate cannot go below 0) and pick slider ranges where the effect
   stays visible instead of saturating.
3. "Check my prediction" compares the pick with the answer and explains in the
   material's wording, including the control case (knob at 0).
4. Three retrieval questions close the page, answers hidden.

Check in a browser before delivering: locked before the pick, unlocked after,
the readout changes with the slider, no horizontal overflow.
