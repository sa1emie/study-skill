from narrated import *

IN = [10, 10, 10, 2, 2, 2]


def out_val(i):
    l = IN[i - 1] if i > 0 else IN[i]
    r = IN[i + 1] if i < len(IN) - 1 else IN[i]
    return round(IN[i] - 0.1 * (l + r), 1)


def hermann(size=0.9, gap=0.22, n=5):
    g = VGroup()
    for r in range(n):
        for c in range(n):
            g.add(Square(size, fill_color="#000000", fill_opacity=1, stroke_width=0).move_to(
                [(c - (n - 1) / 2) * (size + gap), (r - (n - 1) / 2) * (size + gap), 0]))
    bg = Rectangle(width=n * (size + gap) + gap, height=n * (size + gap) + gap, fill_color=WHITE,
                   fill_opacity=1, stroke_width=0)
    return VGroup(bg, g)


class LateralInhibition(NarratedScene):
    def construct(self):
        title = T("Lateral inhibition", 44, weight=BOLD).to_edge(UP, buff=0.45)
        grid = hermann().scale(0.95).shift(DOWN * 0.35)
        with self.beat(0):
            self.play(FadeIn(title), FadeIn(grid), run_time=1.2)
            ring = Circle(0.32, color=ORANGE, stroke_width=5).move_to(grid[1][6].get_corner(UR) + [0.11, 0.11, 0])
            self.wait(2.5)
            self.play(Create(ring), run_time=0.8)

        # beat 1: definition + cells
        with self.beat(1):
            self.play(FadeOut(grid), FadeOut(ring), run_time=0.6)
            d = T("one active neuron turns down its neighbors", 32, color=MUTED).next_to(title, DOWN, buff=0.35)
            self.play(FadeIn(d, shift=UP * 0.2), run_time=0.8)
            xs = [-5 + 2 * i for i in range(6)]
            recs = VGroup(*[RoundedRectangle(corner_radius=0.12, width=1.0, height=0.7, color=INK, stroke_width=2)
                            .move_to([x, -2.2, 0]) for x in xs])
            bips = VGroup(*[Circle(0.32, color=BLUE, stroke_width=3).move_to([x, 0.4, 0]) for x in xs])
            ups = VGroup(*[Arrow(r.get_top(), b.get_bottom(), buff=0.08, color=MUTED, stroke_width=3,
                                 max_tip_length_to_length_ratio=0.15) for r, b in zip(recs, bips)])
            hz = Line([xs[0] - 0.6, -0.9, 0], [xs[-1] + 0.6, -0.9, 0], color=RED, stroke_width=6)
            hl = T("horizontal cell", 26, color=RED).move_to([0, -1.25, 0]); hl.add_background_rectangle(color=BG, opacity=1, buff=0.08)
            rl = T("receptors", 24, color=MUTED).next_to(recs, DOWN, buff=0.15)
            bl = T("bipolar cells", 24, color=BLUE).next_to(bips, UP, buff=0.15)
            self.play(LaggedStart(*[Create(r) for r in recs], lag_ratio=0.08), FadeIn(rl), run_time=1.2)
            self.play(LaggedStart(*[GrowArrow(u) for u in ups], lag_ratio=0.06), LaggedStart(*[Create(b) for b in bips], lag_ratio=0.06), FadeIn(bl), run_time=1.2)
            self.play(Create(hz), FadeIn(hl), run_time=1.0)
            self.play(Indicate(hz, color=RED, scale_factor=1.05), run_time=1.0)
        cells = VGroup(recs, bips, ups, hz, hl, rl, bl)

        # beat 2: input bars
        with self.beat(2):
            self.play(FadeOut(cells), FadeOut(d), run_time=0.6)
            sub = T("light reaching each receptor", 30, color=MUTED).next_to(title, DOWN, buff=0.35)
            ax = Line([-5.8, -2.8, 0], [5.8, -2.8, 0], color=MUTED, stroke_width=2)
            xs = [-4.5 + 1.8 * i for i in range(6)]
            sc = 0.32
            bars = VGroup(*[Rectangle(width=1.1, height=v * sc, fill_color=ORANGE if v > 5 else "#6b5a4c",
                                      fill_opacity=0.9, stroke_width=0).move_to([x, -2.8 + v * sc / 2, 0])
                            for x, v in zip(xs, IN)])
            nums = VGroup(*[T(str(v), 30, weight=BOLD).next_to(b, UP, buff=0.12) for b, v in zip(bars, IN)])
            edge = DashedLine([0, -2.9, 0], [0, 0.9, 0], color=MUTED, dash_length=0.12)
            el = T("edge", 24, color=MUTED).next_to(ax, DOWN, buff=0.12)
            self.play(FadeIn(sub), Create(ax), run_time=0.6)
            self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.1), run_time=1.4)
            self.play(FadeIn(nums), Create(edge), FadeIn(el), run_time=0.8)

        # beat 3: rule
        with self.beat(3):
            rule = T("output = own input  -  0.1 x (left + right neighbor)", 30, color=INK)
            rule.next_to(sub, DOWN, buff=0.3)
            box = SurroundingRectangle(rule, color=RED, buff=0.18, corner_radius=0.1)
            self.play(FadeIn(rule), Create(box), run_time=1.0)
            arr = VGroup(CurvedArrow(bars[1].get_top() + UP * 0.6, bars[2].get_top() + UP * 0.6, color=RED, angle=-PI / 3),
                         CurvedArrow(bars[3].get_top() + UP * 0.6, bars[2].get_top() + UP * 0.6, color=RED, angle=PI / 3))
            self.play(Create(arr), run_time=1.0)

        # beat 4: compute outputs
        outs = [out_val(i) for i in range(6)]
        with self.beat(4):
            self.play(FadeOut(arr), FadeOut(sub), run_time=0.5)
            newbars = VGroup(*[Rectangle(width=1.1, height=v * sc, fill_color=ORANGE if IN[i] > 5 else "#6b5a4c",
                                         fill_opacity=0.9, stroke_width=0).move_to([xs[i], -2.8 + v * sc / 2, 0])
                               for i, v in enumerate(outs)])
            newnums = VGroup(*[T(f"{v:g}", 30, weight=BOLD).next_to(b, UP, buff=0.12) for b, v in zip(newbars, outs)])
            order = [0, 1, 2, 5, 4, 3]
            for k, i in enumerate(order):
                rt = 0.9 if i in (2, 3) else 0.6
                self.play(Transform(bars[i], newbars[i]), Transform(nums[i], newnums[i]), run_time=rt)
                if i in (2, 3):
                    self.play(Indicate(nums[i], color=ORANGE if i == 2 else BLUE, scale_factor=1.4), run_time=0.9)

        # beat 5: edge profile
        with self.beat(5):
            pts = []
            for i, v in enumerate(outs):
                pts += [[xs[i] - 0.55, -2.8 + v * sc, 0], [xs[i] + 0.55, -2.8 + v * sc, 0]]
            prof = VMobject(color=BLUE, stroke_width=6).set_points_as_corners(pts)
            up = T("brighter", 28, color=ORANGE, weight=BOLD).next_to(nums[2], UP, buff=0.2)
            dn = T("darker", 28, color=BLUE, weight=BOLD).next_to(bars[3], UP, buff=0.75).shift(RIGHT * 0.3)
            self.play(Create(prof), run_time=1.6)
            self.play(FadeIn(up, shift=UP * 0.2), FadeIn(dn, shift=DOWN * 0.2), run_time=0.8)
            take = T("sharpens contrast at borders", 34, color=INK, weight=BOLD)
            take.move_to(rule)
            self.play(FadeOut(rule), box.animate.become(SurroundingRectangle(take, color=ORANGE, buff=0.18, corner_radius=0.1)),
                      FadeIn(take), run_time=1.0)
        chart = VGroup(ax, bars, nums, edge, el, prof, up, dn, take, box)

        # beat 6: grid explanation
        with self.beat(6):
            self.play(FadeOut(chart), run_time=0.6)
            grid = hermann().scale(1.15).shift(DOWN * 0.45 + LEFT * 3.0)
            self.play(FadeIn(grid), run_time=0.6)
            sq = grid[1]
            cross = sq[6].get_corner(UR) + [0.11, 0.11, 0]
            street = (sq[7].get_left() + sq[6].get_right()) / 2
            cdot = Dot(cross, color=RED, radius=0.09)
            cneigh = VGroup(*[Arrow(cross + v * 0.62, cross + v * 0.16, buff=0, color=RED, stroke_width=4,
                                    max_tip_length_to_length_ratio=0.35) for v in (UP, DOWN, LEFT, RIGHT)])
            sdot = Dot(street, color=GREEN, radius=0.09)
            sneigh = VGroup(*[Arrow(street + v * 0.62, street + v * 0.16, buff=0, color=GREEN, stroke_width=4,
                                    max_tip_length_to_length_ratio=0.35) for v in (UP, DOWN)])
            t1 = T("crossroad: white on 4 sides", 28, color=RED).move_to([3.5, 0.9, 0])
            t1b = T("most inhibition, looks gray", 26, color=MUTED).next_to(t1, DOWN, buff=0.15)
            t2 = T("street: white on 2 sides", 28, color=GREEN).move_to([3.5, -1.0, 0])
            t2b = T("less inhibition, looks white", 26, color=MUTED).next_to(t2, DOWN, buff=0.15)
            self.play(FadeIn(cdot), LaggedStart(*[GrowArrow(a) for a in cneigh], lag_ratio=0.15), FadeIn(t1), FadeIn(t1b), run_time=1.6)
            self.wait(1.5)
            self.play(FadeIn(sdot), LaggedStart(*[GrowArrow(a) for a in sneigh], lag_ratio=0.15), FadeIn(t2), FadeIn(t2b), run_time=1.4)
        gview = VGroup(grid, cdot, cneigh, sdot, sneigh, t1, t1b, t2, t2b)

        # beat 7: exam cue
        with self.beat(7):
            self.play(FadeOut(gview), run_time=0.6)
            rows = [("If the question says", "Answer"),
                    ("sharpens borders / enhances contrast", "lateral inhibition"),
                    ("which cells cause it", "horizontal cells"),
                    ("which cells they inhibit", "bipolar cells")]
            tbl = VGroup()
            for k, (a, b) in enumerate(rows):
                col = MUTED if k == 0 else INK
                la = T(a, 30 if k else 26, color=col, weight=BOLD if k == 0 else NORMAL)
                lb = T(b, 30 if k else 26, color=MUTED if k == 0 else ORANGE, weight=BOLD)
                la.move_to([-2.6, 1.0 - k * 1.0, 0]).align_to([-6.0, 0, 0], LEFT)
                lb.move_to([3.6, 1.0 - k * 1.0, 0]).align_to([2.4, 0, 0], LEFT)
                tbl.add(VGroup(la, lb))
            rule_line = Line([-6.0, 0.5, 0], [6.0, 0.5, 0], color=MUTED, stroke_width=1.5)
            self.play(FadeIn(tbl[0]), Create(rule_line), run_time=0.6)
            self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.3) for r in tbl[1:]], lag_ratio=0.5), run_time=2.4)
