"""schedule.py: the CLI contract, checking, and repair. Runs against temp units."""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import graph, load, make_unit, row, sched

T = "2026-03-01"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="study-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def unit(self, concepts, mastery=None, name="u"):
        return make_unit(os.path.join(self.tmp, name), concepts, mastery)


class Record(Base):
    def test_hit_grows_interval_and_score(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        code, out = sched(u, "record", "a", "hit", "--date", T)
        self.assertEqual(code, 0, out)
        m = load(os.path.join(u, "mastery.json"))
        c = m["concepts"]["a"]
        self.assertEqual(c["interval"], 2.5)
        self.assertEqual(c["attempts"], 1)
        self.assertEqual(c["score"], 0.3)
        self.assertEqual(c["next_due"], "2026-03-04")  # 2.5 days rounds up
        self.assertEqual(m["concepts"]["a"]["last"], T)

    def test_hint_and_miss_rates(self):
        u = self.unit(graph(("a", "A", "-", "high"), ("b", "B", "-", "high")), {"concepts": {}})
        sched(u, "record", "a", "hint", "--date", T)
        sched(u, "record", "b", "miss", "--date", T)
        m = load(os.path.join(u, "mastery.json"))["concepts"]
        self.assertEqual(m["a"]["score"], 0.15)
        self.assertEqual(m["a"]["next_due"], "2026-03-03")  # 1.5 days rounds up
        self.assertEqual(m["b"]["score"], 0.0)
        self.assertEqual(m["b"]["next_due"], "2026-03-02")

    def test_unknown_id_is_refused_with_suggestions(self):
        u = self.unit(graph(("active-transport", "A", "-", "high")))
        code, out = sched(u, "record", "active-transprot", "hit", "--date", T)
        self.assertEqual(code, 1)
        self.assertIn("refused", out)
        self.assertIn("active-transport", out)
        self.assertFalse(os.path.exists(os.path.join(u, "mastery.json")), "no write on refusal")

    def test_force_records_anyway(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        code, out = sched(u, "record", "b", "hit", "--date", T, "--force")
        self.assertEqual(code, 0, out)
        self.assertIn("warning", out)
        self.assertIn("b", load(os.path.join(u, "mastery.json"))["concepts"])

    def test_hit_pushes_learned_prereq_later(self):
        u = self.unit(graph(("p", "P", "-", "high"), ("d", "D", "p", "high")),
                      {"concepts": {"p": row(score=0.8, interval=2, next_due="2026-03-01")}})
        sched(u, "record", "d", "hit", "--date", T)
        p = load(os.path.join(u, "mastery.json"))["concepts"]["p"]
        self.assertGreater(p["next_due"], "2026-03-01")
        self.assertGreater(p["implicit"], 0)

    def test_hit_skips_unlearned_prereq(self):
        u = self.unit(graph(("p", "P", "-", "high"), ("d", "D", "p", "high")),
                      {"concepts": {"p": row(score=0.2, interval=2, next_due="2026-03-01")}})
        sched(u, "record", "d", "hit", "--date", T)
        p = load(os.path.join(u, "mastery.json"))["concepts"]["p"]
        self.assertEqual(p["next_due"], "2026-03-01", "weak prereq keeps its own schedule")

    def test_miss_pulls_weak_prereq_to_tomorrow(self):
        u = self.unit(graph(("p", "P", "-", "high"), ("d", "D", "p", "high")),
                      {"concepts": {"p": row(score=0.5, interval=10, next_due="2026-04-01")}})
        code, out = sched(u, "record", "d", "miss", "--date", T)
        self.assertIn("weak prereq p pulled", out)
        p = load(os.path.join(u, "mastery.json"))["concepts"]["p"]
        self.assertEqual(p["next_due"], "2026-03-02")

    def test_deadline_flag_caps_next_due(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        sched(u, "record", "a", "hit", "--date", T, "--deadline", "2026-03-02")
        self.assertEqual(load(os.path.join(u, "mastery.json"))["concepts"]["a"]["next_due"], "2026-03-02")

    def test_deadline_in_state_caps_next_due(self):
        u = self.unit(graph(("a", "A", "-", "high")),
                      {"deadline": "2026-03-02", "concepts": {}})
        sched(u, "record", "a", "hit", "--date", T)
        self.assertEqual(load(os.path.join(u, "mastery.json"))["concepts"]["a"]["next_due"], "2026-03-02")


class Due(Base):
    def test_due_orders_by_knockout_value(self):
        u = self.unit(graph(("a", "A", "-", "high"), ("b", "B", "a", "medium"), ("c", "C", "b", "low")))
        code, out = sched(u, "due", "--date", T)
        self.assertEqual(code, 0)
        self.assertIn("3 due", out)
        lines = [l.strip() for l in out.splitlines() if l.strip().startswith("c ")]
        self.assertEqual(len(lines), 1, out)
        self.assertIn("also covers b, a", lines[0])

    def test_due_json(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        code, out = sched(u, "due", "--date", T, "--json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["due"], 1)
        self.assertEqual(data["order"][0]["id"], "a")

    def test_due_notes_missing_deadline(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        _, out = sched(u, "due", "--date", T)
        self.assertIn("no deadline", out)

    def test_due_survives_hand_edited_dates(self):
        u = self.unit(graph(("a", "A", "-", "high"), ("b", "B", "-", "high")),
                      {"concepts": {"a": {"score": 0.2, "next_due": "soon"},
                                    "b": row(next_due="2020-01-01")}})
        code, out = sched(u, "due", "--date", T)
        self.assertEqual(code, 0, out)
        self.assertIn("2 due", out)

    def test_record_survives_malformed_state_dates(self):
        u = self.unit(graph(("p", "P", "-", "high"), ("d", "D", "p", "high")),
                      {"deadline": "whenever",
                       "concepts": {"p": row(score=0.8, interval=2, next_due="garbage")}})
        code, out = sched(u, "record", "d", "hit", "--date", T)
        self.assertEqual(code, 0, out)
        p = load(os.path.join(u, "mastery.json"))["concepts"]["p"]
        self.assertEqual(p["next_due"], "2026-03-05")


class Tests(Base):
    def test_pre_post_gain_is_printed(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        sched(u, "test", "pre", 2, 5, "--label", "membranes", "--date", T)
        code, out = sched(u, "test", "post", 4, 5, "--label", "membranes", "--date", T)
        self.assertEqual(code, 0)
        self.assertIn("gain +40 pts", out)

    def test_impossible_score_is_refused(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        code, out = sched(u, "test", "pre", 6, 5, "--date", T)
        self.assertEqual(code, 1)
        self.assertIn("refused", out)

    def test_bad_kind_is_refused(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        code, out = sched(u, "test", "mid", 2, 5, "--date", T)
        self.assertEqual(code, 1)
        self.assertIn("pre or post", out)


class Check(Base):
    def test_healthy_unit_exits_0(self):
        u = self.unit(
            graph(("a", "A", "-", "high"), ("b", "B", "a", "medium")),
            {"deadline": "2026-12-01", "concepts": {"a": row(next_due="2025-01-01"),
                                                     "b": row()},
             "tests": [{"date": T, "kind": "pre", "label": "x", "correct": 1, "total": 5},
                       {"date": T, "kind": "post", "label": "x", "correct": 4, "total": 5}]})
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 0, out)
        self.assertNotIn("warning", out)

    def test_check_json_shape(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        code, out = sched(u, "check", "--date", T, "--json")
        data = json.loads(out)
        self.assertEqual(data["exit"], code)
        self.assertEqual(data["graph_concepts"], 1)
        self.assertEqual(data["state_concepts"], 0)

    def test_orphan_warns(self):
        u = self.unit(graph(("a", "A", "-", "high")),
                      {"deadline": "2026-12-01", "concepts": {"c1-gradients": row()}})
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 1, out)
        self.assertIn("W_ORPHAN", out)

    def test_dangling_prereq_errors(self):
        u = make_unit(os.path.join(self.tmp, "u2"), graph(("a", "A", "ghost", "high")))
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 2, out)
        self.assertIn("E_PREREQ_MISSING", out)

    def test_cycle_errors(self):
        u = self.unit(graph(("a", "A", "b", "high"), ("b", "B", "a", "high")), {"concepts": {}})
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 2, out)
        self.assertIn("E_PREREQ_CYCLE", out)

    def test_state_behind_warns(self):
        rows = [("c%02d" % i, "C", "-", "high") for i in range(12)]
        u = self.unit(graph(*rows),
                      {"deadline": "2026-12-01",
                       "concepts": {"c00": row(score=0.5), "c01": row(score=0.5)},
                       "tests": [{"date": T, "kind": "pre", "label": "x", "correct": 1, "total": 5}]})
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 1, out)
        self.assertIn("W_STATE_BEHIND", out)

    def test_fix_migrates_flat_and_repairs(self):
        u = self.unit(graph(("a", "A", "-", "high"), ("b", "B", "a", "high")),
                      {"unit": "legacy",
                       "a": {"score": 1.4, "attempts": 2, "next_due": "2020-01-01", "junk": 1},
                       "b": {"score": 0.5, "next_due": "not-a-date", "interval": 10}})
        code, out = sched(u, "check", "--fix", "--date", T)
        self.assertIn("migrated", out)
        m = load(os.path.join(u, "mastery.json"))
        self.assertIn("concepts", m)
        self.assertEqual(m["unit"], "legacy")
        self.assertEqual(m["concepts"]["a"]["score"], 1.0)
        self.assertNotIn("junk", m["concepts"]["a"])
        self.assertEqual(m["concepts"]["b"]["next_due"], "2026-03-11")  # today + 10 from interval
        self.assertEqual(m["concepts"]["b"]["last"], None)
        self.assertEqual(m["concepts"]["b"]["errors"], [])
        # the rerun is clean of the things fix repaired; only warnings we cannot fix remain
        code2, out2 = sched(u, "check", "--date", T)
        self.assertNotIn("E_SCORE_RANGE", out2)
        self.assertNotIn("W_LEGACY_SHAPE", out2)
        self.assertEqual(code2, 1, out2)  # W_NO_DEADLINE remains

    def test_fix_never_deletes_rows(self):
        u = self.unit(graph(("a", "A", "-", "high")),
                      {"concepts": {"a": row(), "zz-orphan": {"score": 0.6, "attempts": 1}}})
        sched(u, "check", "--fix", "--date", T)
        m = load(os.path.join(u, "mastery.json"))
        self.assertIn("zz-orphan", m["concepts"], "orphans are reported, not deleted")

    def test_no_graph_warns(self):
        u = self.unit(None, {"concepts": {"a": row()}})
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 1, out)
        self.assertIn("W_NO_GRAPH", out)


if __name__ == "__main__":
    unittest.main()
