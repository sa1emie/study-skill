#!/usr/bin/env python3
"""Player page: the video, then retrieval questions with hidden answers.

usage: page.py BEATS.json VIDEO.mp4 OUT.html
BEATS.json needs "questions": [{"q": "...", "a": "..."}, ...] (3 or more).
Every explainer video ends in questions: watching is exposure, answering is practice.
"""
import html, json, os, sys

spec, video, out = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]
qs = spec.get("questions") or []
if len(qs) < 3:
    sys.exit("page.py: beats.json needs at least 3 questions (every video ends in questions)")
rel = os.path.relpath(video, os.path.dirname(os.path.abspath(out)))
items = "\n".join(f'<details><summary>{i}. {html.escape(q["q"])}</summary><p>{html.escape(q["a"])}</p></details>'
                  for i, q in enumerate(qs, 1))
title = html.escape(spec.get("title", "Explainer"))
open(out, "w").write(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{--bg:#ffffff;--surface:#f4f1ee;--ink:#1f1a17;--muted:#6b5f55;--line:#e3ddd7;--accent:#c2410c}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#1c1714;--surface:#26201c;--ink:#f3ece4;--muted:#a89a8c;--line:#3a312b;--accent:#e8833a}}}}
:root[data-theme="dark"]{{--bg:#1c1714;--surface:#26201c;--ink:#f3ece4;--muted:#a89a8c;--line:#3a312b;--accent:#e8833a}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 "Inter",ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:960px;margin:0 auto;padding:40px 16px 72px}}h1{{font-size:28px;margin:0 0 16px}}
video{{width:100%;border-radius:10px;border:1px solid var(--line)}}
h2{{font-size:19px;margin:28px 0 4px}}.hint{{color:var(--muted);margin:0 0 10px}}
details{{background:var(--surface);border-radius:8px;padding:12px 16px;margin-bottom:8px}}summary{{cursor:pointer;font-weight:600}}
details p{{margin:8px 0 0;color:var(--muted)}}details[open] summary{{color:var(--accent)}}
</style></head><body><main><h1>{title}</h1>
<video controls preload="metadata" src="{html.escape(rel)}"></video>
<h2>Now answer without rewatching</h2><p class="hint">Say or write each answer before you open it.</p>
{items}
</main></body></html>""")
print(f"page {out} ({len(qs)} questions)")
