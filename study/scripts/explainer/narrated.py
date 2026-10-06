"""Base scene that times Manim animations to narration beats.

Import in a scene file:  from narrated import *
Use:  with self.beat(0): self.play(...)
The block is padded with a wait so beat i ends exactly when its audio ends.
timing.json comes from tts.py; make.py passes its path in EXPLAINER_TIMING.
Palette: warm dark background, orange and blue accents (matches assets/study.css).
"""
import contextlib, json, os, sys
from manim import *

BG, INK, MUTED = "#1c1714", "#f3ece4", "#a89a8c"
ORANGE, BLUE, RED, GREEN = "#e8833a", "#6fa8dc", "#e06666", "#93c47d"
FONT = os.environ.get("EXPLAINER_FONT") or ("Avenir Next" if sys.platform == "darwin" else "DejaVu Sans")


def T(s, size=36, color=INK, weight=NORMAL, **kw):
    return Text(s, font=FONT, font_size=size, color=color, weight=weight, **kw)


class NarratedScene(Scene):
    def setup(self):
        self.camera.background_color = BG
        self.timing = json.load(open(os.environ["EXPLAINER_TIMING"]))
        self.warnings = []

    @contextlib.contextmanager
    def beat(self, i):
        start = self.renderer.time
        yield
        left = start + self.timing[i]["seconds"] - self.renderer.time
        if left < -0.05:
            self.warnings.append(f"beat {i}: animations run {-left:.2f}s past the narration")
        if left > 0.02:
            self.wait(left)
        self.check_bounds(i)

    def check_bounds(self, i):
        w, h = config.frame_width / 2, config.frame_height / 2
        for m in self.mobjects:
            if m.get_left()[0] < -w - .01 or m.get_right()[0] > w + .01 or m.get_bottom()[1] < -h - .01 or m.get_top()[1] > h + .01:
                self.warnings.append(f"beat {i}: {type(m).__name__} leaves the frame")

    def tear_down(self):
        path = os.environ.get("EXPLAINER_WARN")
        if path:
            json.dump(self.warnings, open(path, "w"), indent=1)
