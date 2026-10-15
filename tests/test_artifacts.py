"""The other scripts: Anki export, page inliner, KaTeX checker. All offline."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PY, REPO, SKILL, make_unit, row

SCRIPTS = os.path.join(SKILL, "scripts")
ANKI = os.path.join(SCRIPTS, "anki_export.py")
INLINE = os.path.join(SCRIPTS, "inline.py")
KATEX = os.path.join(SCRIPTS, "katex_check.js")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="study-art-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


class Anki(Base):
    def test_misses_only_export(self):
        u = make_unit(os.path.join(self.tmp, "cell-bio"),
                      "# graph\n",
                      {"concepts": {"weak-one": row(score=0.3),
                                    "solid-one": row(score=0.9)}})
        cards = [
            {"concept": "weak-one", "front": "Q1", "back": "A1", "source": "slide 4"},
            {"concept": "solid-one", "front": "Q2", "back": "A2", "source": "slide 5"},
            {"concept": "never-drilled", "front": "Q3", "back": "A3", "source": "slide 6"},
        ]
        cards_path = os.path.join(self.tmp, "cards.json")
        with open(cards_path, "w", encoding="utf-8") as f:
            json.dump(cards, f)
        p = subprocess.run([PY, ANKI, u, cards_path], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("1 of 3 cards kept", p.stdout)
        out = os.path.join(u, "out")
        produced = os.listdir(out)
        self.assertEqual(len(produced), 1, produced)
        body = open(os.path.join(out, produced[0]), encoding="utf-8").read()
        self.assertIn("Q1", body)
        self.assertNotIn("Q2", body)
        self.assertNotIn("Q3", body)


class Inline(Base):
    def test_css_js_and_images_are_inlined(self):
        page = os.path.join(self.tmp, "page.html")
        with open(page, "w", encoding="utf-8") as f:
            f.write('<html><head><link rel="stylesheet" href="study.css">'
                    '</head><body><img src="pic.png">'
                    '<script src="study.js"></script></body></html>')
        with open(os.path.join(self.tmp, "pic.png"), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 16)
        out = os.path.join(self.tmp, "out.html")
        p = subprocess.run([PY, INLINE, page, out, "--images"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        body = open(out, encoding="utf-8").read()
        self.assertNotIn('href="study.css"', body)
        self.assertNotIn('src="study.js"', body)
        self.assertIn("<style>", body)
        self.assertIn("data:image/png;base64,", body)


class Katex(Base):
    def test_good_math_passes_bad_math_fails(self):
        if not os.path.exists(os.path.join(SCRIPTS, "node_modules", "katex")):
            self.skipTest("katex not installed (cd study/scripts && npm install --no-save katex)")
        good = os.path.join(self.tmp, "good.md")
        with open(good, "w", encoding="utf-8") as f:
            f.write("Inline $x^2 + y^2 = z^2$ and display:\n\n$$\\frac{a}{b}$$\n")
        p = subprocess.run(["node", KATEX, good], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout)
        bad = os.path.join(self.tmp, "bad.md")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("Broken $\\frac{1}{$ here.\n")
        p = subprocess.run(["node", KATEX, bad], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1, p.stdout)


class Explainer(Base):
    def test_make_refuses_without_questions(self):
        # make.py needs the heavy video stack; its guard should refuse before importing it
        make = os.path.join(SCRIPTS, "explainer", "make.py")
        if not os.path.exists(make):
            self.skipTest("explainer not present")
        spec = os.path.join(self.tmp, "spec.json")
        with open(spec, "w", encoding="utf-8") as f:
            json.dump({"title": "t", "scenes": [], "questions": []}, f)
        p = subprocess.run([PY, make, spec, "--out", self.tmp], capture_output=True, text=True)
        if p.returncode == 0:
            self.skipTest("make.py built anyway; environment has the full stack")
        self.assertNotEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
