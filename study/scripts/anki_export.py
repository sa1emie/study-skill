#!/usr/bin/env python3
"""Anki export of misses only. Use ONLY when the student says they use Anki
(or Mochi, RemNote, any SRS app that imports Anki files).

usage: anki_export.py UNIT CARDS.json [--all] [--out DIR]
CARDS.json: [{"concept": "c5-lateral-inhibition", "front": "...", "back": "...",
              "source": "Ch5 slide 24, 'sharpens contrasts...'"}, ...]
Keeps a card only if its concept is weak in mastery.json: score < 0.7, or any
recorded error / miss. --all skips the filter. Writes <unit>-misses.apkg with
genanki when it is installed, else a TSV (front, back, source, tags) with a
#separator header that Anki imports natively. Says which one it wrote.
"""
import json, os, sys, hashlib

a = sys.argv[1:]
unit, cards_path = os.path.expanduser(a[0]), a[1]
out_dir = a[a.index("--out") + 1] if "--out" in a else os.path.join(unit, "out")
cards = json.load(open(cards_path))
m = json.load(open(os.path.join(unit, "mastery.json")))
store = m.get("concepts") or m.get("types") or {k: v for k, v in m.items() if isinstance(v, dict)}


def weak(cid):
    c = store.get(cid)
    if c is None:
        return False  # never drilled: no miss to export
    score = c.get("score")
    errs = c.get("errors") or c.get("error_patterns") or []
    return (score is not None and float(score) < 0.7) or bool(errs and float(score or 0) < 1.0)


keep = cards if "--all" in a else [c for c in cards if weak(c["concept"])]
name = os.path.basename(os.path.normpath(unit))
os.makedirs(out_dir, exist_ok=True)
try:
    import genanki
    mid = int(hashlib.md5(b"study-misses").hexdigest()[:8], 16)
    model = genanki.Model(mid, "study misses", fields=[{"name": "Front"}, {"name": "Back"}, {"name": "Source"}],
                          templates=[{"name": "Card", "qfmt": "{{Front}}",
                                      "afmt": "{{FrontSide}}<hr id=answer>{{Back}}<br><small>{{Source}}</small>"}])
    deck = genanki.Deck(int(hashlib.md5(name.encode()).hexdigest()[:8], 16), f"{name}::misses")
    for c in keep:
        deck.add_note(genanki.Note(model=model, fields=[c["front"], c["back"], c.get("source", "")], tags=[c["concept"]]))
    path = os.path.join(out_dir, f"{name}-misses.apkg")
    genanki.Package(deck).write_to_file(path)
except ImportError:
    path = os.path.join(out_dir, f"{name}-misses.txt")
    with open(path, "w") as f:
        f.write("#separator:tab\n#html:true\n#tags column:4\n#columns:Front\tBack\tSource\tTags\n")
        for c in keep:
            row = [c["front"], c["back"], c.get("source", ""), c["concept"]]
            f.write("\t".join(x.replace("\t", " ").replace("\n", "<br>") for x in row) + "\n")
print(f"{len(keep)} of {len(cards)} cards kept (weak concepts only) -> {path}")
