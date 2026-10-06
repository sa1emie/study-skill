# HTML design: how study pages should look

Generated study pages fail in predictable ways: a wall of centered text, five
accent colors, gradient headers, emoji bullets, tiny gray type, answers visible
before the question is attempted. This file is a small design system so every
page looks calm, readable and consistent. Do not improvise CSS: start from
`assets/template.html`, use the classes below, then inline.

## Build procedure

1. Copy `assets/template.html` to `out/<name>.html`. Keep the `<link
   href="study.css">` and `<script src="study.js">` lines as they are.
2. Fill it with content, using only the components below.
3. Inline: `python3 SKILL_DIR/scripts/inline.py out/<name>.html out/<name>.html --images`
   (prints what it inlined; both css and js must say "inlined").
4. Open it in a browser and look, light and dark. Check: nothing overflows
   sideways, quiz answers are hidden until "Show answers", flashcards flip,
   images load. Only then call it done.

## Principles

- **One column for reading.** Prose stays at about 70 characters per line
  (`main` is 46rem). Use `<main class="wide">` only for pages that are mostly
  tables or simulations.
- **One accent color**, used for meaning: the answer column, high-yield tags,
  the plain-language box edge, the primary button. Blue is for links and
  medium-yield tags. Nothing else gets color.
- **Hierarchy by size and weight, not decoration.** h1 for the page, h2 per
  concept, h3 inside. No colored section banners, no numbered "01 / 02" labels.
- **Answers are hidden until attempted.** Every answer lives in `.quiz .a`,
  `details`, or a `.card .back`.
- **Readable by default.** 17px body, 1.6 line height, contrast meeting WCAG AA
  in both themes (the tokens already do), visible focus outlines.
- **Light and dark both work.** Never hardcode a color in a page; use the
  `var(--...)` tokens.

## Components

| Need | Markup |
|---|---|
| Page header | `<header class="page-head"><h1>..</h1><p class="meta">exam date, scope, sources</p></header>` |
| Contents | `<nav class="toc"><ol><li><a href="#id">..</a></li></ol></nav>` |
| Concept section | `<section id=".."><h2>Name <span class="tag high">high yield</span></h2>..</section>` (`high`, `medium`, `low`) |
| Plain-language box | `<div class="plain"><p>..</p></div>`, the first thing in a section at `register: plain` |
| Cue table | `<table class="cues">` with columns "If the question says" and "Answer" |
| Hidden depth | `<details><summary>Why it works (optional)</summary>..</details>` |
| Pre-test, post-test, practice | `<section class="quiz"><h3>..</h3><ol><li>Question<div class="a">Answer</div></li></ol></section>`; study.js adds "Show answers", "I got it" boxes and a score |
| Flashcards | `<div class="cards"><div class="card"><div class="front">..</div><div class="back">..</div></div></div>` |
| Diagram or video | `<figure><img or video><figcaption>meaning of color, source</figcaption></figure>` |
| Note, pitfall | `<p class="note">..</p>`, `<p class="warn">..</p>` |
| Supplement | `<p class="supplement">..</p>` for anything not in the course material |
| Side by side | `<div class="grid-2">..</div>` (stacks on phones) |
| Wide table | wrap in `<div class="table-wrap">` |

## Do not

- Gradients, glow, glassmorphism, drop-shadow stacks, text in gradient color.
- Emoji as icons or bullets.
- Pill-shaped buttons or tags (use the square-cornered `.tag` and `.btn`).
- Centered body text, or a hero banner with two buttons.
- More than one accent color, or color without a meaning.
- Small uppercase letter-spaced labels above headings.
- External fonts or frameworks beyond KaTeX; the system font stack is fine and
  works offline.

## Math

Pages with math add the KaTeX lines that are commented out in the template's
`<head>` and write math as `\( .. \)` inline and `\[ .. \]` for display. Check a
math page in a browser: unrendered `\(` in the page means KaTeX did not load.

## Charts

Prefer inline SVG drawn from the data (bars, a line) with the tokens as colors.
If a chart library is needed, load one from a CDN and keep its default palette
replaced with `var(--accent)` and `var(--blue)`.
