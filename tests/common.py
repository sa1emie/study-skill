"""Shared helpers for the test suite. Stdlib only, so it runs anywhere Python does."""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, "study")
SCHED = os.path.join(SKILL, "scripts", "schedule.py")
PY = sys.executable

HEAD = "| id | name | shape | prereqs | yield | evidence |\n|---|---|---|---|---|---|\n"


def graph(*rows):
    """rows: (id, name, prereqs, yield). Returns a concepts.md body."""
    out = [HEAD]
    for cid, name, prereqs, y in rows:
        out.append("| %s | %s | mechanism | %s | %s | quote |\n" % (cid, name, prereqs, y))
    return "".join(out)


def make_unit(tmp, concepts, mastery=None):
    """Write a unit folder under tmp and return its path."""
    os.makedirs(tmp, exist_ok=True)
    if concepts is not None:
        with open(os.path.join(tmp, "concepts.md"), "w", encoding="utf-8") as f:
            f.write(concepts)
    if mastery is not None:
        with open(os.path.join(tmp, "mastery.json"), "w", encoding="utf-8") as f:
            json.dump(mastery, f, indent=2)
    return tmp


def row(score=0.5, attempts=1, interval=1.0, last="2026-02-01", next_due="2026-02-02", **kw):
    d = {"score": score, "attempts": attempts, "interval": interval,
         "last": last, "next_due": next_due, "errors": []}
    d.update(kw)
    return d


def sched(*args):
    """Run schedule.py with args. Returns (exit_code, stdout)."""
    p = subprocess.run([PY, SCHED] + [str(a) for a in args],
                       capture_output=True, text=True, cwd=REPO)
    return p.returncode, p.stdout


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
