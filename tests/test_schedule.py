"""schedule.py: the CLI contract, checking, and repair. Runs against temp units."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SCHED, graph, load, make_unit, row, sched

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


class RecordFlags(Base):
    def test_deadline_flag_is_persisted(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        code, out = sched(u, "record", "a", "hit", "--date", T, "--deadline", "2026-04-01")
        self.assertEqual(code, 0, out)
        self.assertEqual(load(os.path.join(u, "mastery.json"))["deadline"], "2026-04-01")

    def test_deadline_survives_later_records(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        sched(u, "record", "a", "hit", "--date", T, "--deadline", "2026-04-01")
        sched(u, "record", "a", "hit", "--date", "2026-03-04")
        m = load(os.path.join(u, "mastery.json"))
        self.assertEqual(m["deadline"], "2026-04-01")
        self.assertLessEqual(m["concepts"]["a"]["next_due"], "2026-04-01")

    def test_error_classes_append_and_dedupe(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        sched(u, "record", "a", "miss", "--date", T, "--error", "setup", "--error", "sign")
        sched(u, "record", "a", "hint", "--date", T, "--error", "setup")
        c = load(os.path.join(u, "mastery.json"))["concepts"]["a"]
        self.assertEqual(c["errors"], ["setup", "sign"])

    def test_confidence_and_override_are_stored(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        code, out = sched(u, "record", "a", "hit", "--date", T, "--confidence", "4", "--override")
        self.assertEqual(code, 0, out)
        c = load(os.path.join(u, "mastery.json"))["concepts"]["a"]
        self.assertEqual(c["confidence"], 4)
        self.assertIs(c["override"], True)

    def test_bad_confidence_is_a_usage_error(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        code, out = sched(u, "record", "a", "hit", "--date", T, "--confidence", "9")
        self.assertEqual(code, 2, out)

    def test_hint_streak_holds_then_resets_interval(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        sched(u, "record", "a", "hint", "--date", "2026-03-01")
        self.assertEqual(load(os.path.join(u, "mastery.json"))["concepts"]["a"]["interval"], 1.5)
        sched(u, "record", "a", "hint", "--date", "2026-03-03")
        self.assertEqual(load(os.path.join(u, "mastery.json"))["concepts"]["a"]["interval"], 1.5,
                         "a second consecutive hint holds the interval")
        sched(u, "record", "a", "hint", "--date", "2026-03-05")
        self.assertEqual(load(os.path.join(u, "mastery.json"))["concepts"]["a"]["interval"], 1.0,
                         "a third consecutive hint resets to daily")

    def test_record_refuses_row_that_is_not_an_object(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {"a": "oops"}})
        with open(os.path.join(u, "mastery.json"), encoding="utf-8") as f:
            before = f.read()
        code, out = sched(u, "record", "a", "hit", "--date", T)
        self.assertEqual(code, 1, out)
        self.assertIn("not an object", out)
        with open(os.path.join(u, "mastery.json"), encoding="utf-8") as f:
            self.assertEqual(f.read(), before)


class Spacing(Base):
    def test_interval_ceiling(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        for i in range(6):
            sched(u, "record", "a", "hit", "--date", "2026-03-%02d" % (1 + i))
        self.assertEqual(load(os.path.join(u, "mastery.json"))["concepts"]["a"]["interval"], 90)

    def test_interval_compresses_toward_deadline(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        sched(u, "record", "a", "hit", "--date", "2026-03-01", "--deadline", "2026-03-21")
        sched(u, "record", "a", "hit", "--date", "2026-03-04")
        sched(u, "record", "a", "hit", "--date", "2026-03-11")
        c = load(os.path.join(u, "mastery.json"))["concepts"]["a"]
        self.assertEqual(c["interval"], 6.0, "15.625 days would land past the deadline")
        self.assertEqual(c["next_due"], "2026-03-17")


class CorruptState(Base):
    def _write(self, u, text):
        with open(os.path.join(u, "mastery.json"), "w", encoding="utf-8") as f:
            f.write(text)

    def test_check_reports_corrupt_json(self):
        u = self.unit(graph(("a", "A", "-", "high")), None)
        self._write(u, '{"concepts": {"a": ')
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 2, out)
        self.assertIn("E_STATE_CORRUPT", out)

    def test_record_refuses_corrupt_and_keeps_bytes(self):
        u = self.unit(graph(("a", "A", "-", "high")), None)
        self._write(u, "not json at all")
        code, out = sched(u, "record", "a", "hit", "--date", T)
        self.assertEqual(code, 2, out)
        with open(os.path.join(u, "mastery.json"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "not json at all")

    def test_due_refuses_corrupt(self):
        u = self.unit(graph(("a", "A", "-", "high")), None)
        self._write(u, "oops")
        code, out = sched(u, "due", "--date", T)
        self.assertEqual(code, 2, out)

    def test_fix_quarantines_corrupt_file(self):
        u = self.unit(graph(("a", "A", "-", "high")), None)
        self._write(u, '{"concepts": [')
        code, out = sched(u, "check", "--fix", "--date", T)
        self.assertIn("fixed", out)
        self.assertNotIn("E_STATE_CORRUPT", out)
        self.assertFalse(os.path.exists(os.path.join(u, "mastery.json")))
        with open(os.path.join(u, "mastery.json.corrupt"), encoding="utf-8") as f:
            self.assertEqual(f.read(), '{"concepts": [')
        self.assertEqual(code, 1, out)

    def test_second_quarantine_gets_a_suffix(self):
        u = self.unit(graph(("a", "A", "-", "high")), None)
        self._write(u, "bad")
        with open(os.path.join(u, "mastery.json.corrupt"), "w", encoding="utf-8") as f:
            f.write("older")
        sched(u, "check", "--fix", "--date", T)
        self.assertTrue(os.path.exists(os.path.join(u, "mastery.json.corrupt-2")))

    def test_broken_concepts_shape_is_refused(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": ["a", "b"]})
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 2, out)
        self.assertIn("E_STATE_BROKEN", out)
        code, out = sched(u, "record", "a", "hit", "--date", T)
        self.assertEqual(code, 2, out)
        self.assertTrue(load(os.path.join(u, "mastery.json"))["concepts"] == ["a", "b"])

    def test_bare_list_state_is_refused(self):
        u = self.unit(graph(("a", "A", "-", "high")), None)
        self._write(u, '["a", "b"]')
        code, out = sched(u, "record", "a", "hit", "--date", T)
        self.assertEqual(code, 2, out)
        sched(u, "check", "--fix", "--date", T)
        self.assertTrue(os.path.exists(os.path.join(u, "mastery.json.corrupt")))

    def test_fix_never_creates_state(self):
        u = self.unit(graph(("a", "A", "-", "high")), None)
        sched(u, "check", "--fix", "--date", T)
        self.assertFalse(os.path.exists(os.path.join(u, "mastery.json")))


class MalformedRows(Base):
    def test_due_survives_bad_rows_and_scores(self):
        u = self.unit(graph(("a", "A", "-", "high"), ("b", "B", "-", "high")),
                      {"concepts": {"a": "oops",
                                    "b": {"score": "high", "attempts": "x",
                                          "interval": "no", "next_due": "2026-02-01"}}})
        code, out = sched(u, "due", "--date", T)
        self.assertEqual(code, 0, out)
        self.assertIn("2 due", out)

    def test_check_reports_and_cannot_fix_bad_row(self):
        u = self.unit(graph(("a", "A", "-", "high"), ("b", "B", "-", "high")),
                      {"concepts": {"a": "oops", "b": row(next_due="2026-02-02")}})
        code, out = sched(u, "check", "--fix", "--date", T)
        self.assertEqual(code, 2, out)
        self.assertIn("E_ROW_TYPE", out)
        self.assertIn("cannot", out)
        m = load(os.path.join(u, "mastery.json"))
        self.assertEqual(m["concepts"]["a"], "oops", "cannot-fix rows stay put")

    def test_junk_tests_entry_is_reported_not_crashed(self):
        u = self.unit(graph(("a", "A", "-", "high")),
                      {"deadline": "2026-12-01", "concepts": {},
                       "tests": ["junk", {"date": T, "kind": "pre", "label": "x",
                                          "correct": 1, "total": 5}]})
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 1, out)
        self.assertIn("W_TEST_ENTRY", out)
        code, out = sched(u, "tests")
        self.assertEqual(code, 0, out)

    def test_state_behind_counts_misses_too(self):
        rows = [("c%02d" % i, "C", "-", "high") for i in range(12)]
        u = self.unit(graph(*rows),
                      {"deadline": "2026-12-01",
                       "concepts": {"c00": row(score=0.0, attempts=2),
                                    "c01": row(score=0.0, attempts=1)}})
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 1, out)
        self.assertIn("W_STATE_BEHIND", out)


class CliErrors(Base):
    def test_bad_date_is_a_usage_error(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        code, out = sched(u, "due", "--date", "soon")
        self.assertEqual(code, 2, out)
        self.assertIn("expected a date", out)

    def test_dangling_and_bad_flags_are_usage_errors(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        for args in (["due", "--limit"], ["due", "--limit", "abc"],
                     ["due", "--deadline", "2026-01-01"], ["check", "--fixx"]):
            code, out = sched(u, *args)
            self.assertEqual(code, 2, "%s -> %s" % (args, out))
            self.assertIn("schedule.py:", out)

    def test_dangling_deadline_after_record(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        code, out = sched(u, "record", "a", "hit", "--deadline")
        self.assertEqual(code, 2, out)
        self.assertIn("--deadline needs a value", out)


class SelfPrereq(Base):
    def test_self_prereq_reported_once(self):
        u = self.unit(graph(("x", "X", "x", "high")), {"concepts": {}})
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 2, out)
        self.assertIn("E_PREREQ_SELF", out)
        self.assertNotIn("E_PREREQ_CYCLE", out)


class PostTests(Base):
    def test_gain_pairs_by_label_not_order(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        sched(u, "test", "pre", 1, 5, "--label", "ch4", "--date", "2026-03-01")
        sched(u, "test", "pre", 5, 5, "--label", "ch5", "--date", "2026-03-02")
        code, out = sched(u, "test", "post", 3, 5, "--label", "ch4", "--date", "2026-03-03")
        self.assertEqual(code, 0, out)
        self.assertIn("gain +40 pts", out)

    def test_gain_notes_a_long_gap(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        sched(u, "test", "pre", 1, 5, "--label", "x", "--date", "2026-03-01")
        code, out = sched(u, "test", "post", 3, 5, "--label", "x", "--date", "2026-03-20")
        self.assertIn("gain +40 pts over 19 days", out)

    def test_conditions_recorded_and_shown(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        code, out = sched(u, "test", "post", 3, 5, "--label", "x", "--date", T,
                          "--conditions", "supported")
        self.assertEqual(code, 0, out)
        self.assertIn("[supported]", out)
        code, out = sched(u, "test", "post", 3, 5, "--label", "x", "--date", T,
                          "--conditions", "vibes")
        self.assertEqual(code, 2, out)


class Reserve(Base):
    def test_questions_flow(self):
        u = self.unit(graph(("a", "A", "-", "high"), ("b", "B", "-", "high")), {"concepts": {}})
        code, out = sched(u, "questions")
        self.assertEqual(code, 0)
        self.assertIn("no questions.json", out)
        code, out = sched(u, "questions", "add", "q1", "a")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.exists(os.path.join(u, "questions.json")))
        code, out = sched(u, "questions", "add", "q1", "a")
        self.assertEqual(code, 1, out)
        code, out = sched(u, "questions", "add", "q2", "aa")
        self.assertEqual(code, 1, out)
        self.assertIn("closest ids", out)
        sched(u, "questions", "add", "q3", "a", "--state", "burnt")
        code, out = sched(u, "questions", "mark", "q3", "seen-wrong", "--date", T)
        self.assertEqual(code, 0, out)
        q = load(os.path.join(u, "questions.json"))["items"]
        self.assertEqual(q["q3"]["state"], "seen-wrong")
        self.assertEqual(q["q3"]["last"], T)
        code, out = sched(u, "questions", "mark", "q9", "burnt")
        self.assertEqual(code, 1, out)
        code, out = sched(u, "questions", "--json")
        data = json.loads(out)
        self.assertIn("q1", data["items"])

    def test_reserve_low_warns_in_check(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {"a": row()}})
        with open(os.path.join(u, "questions.json"), "w", encoding="utf-8") as f:
            json.dump({"items": {"q1": {"concept": "a", "state": "unseen", "last": None}}}, f)
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 1, out)
        self.assertIn("W_RESERVE_LOW", out)

    def test_corrupt_questions_file_is_a_warning(self):
        u = self.unit(graph(("a", "A", "-", "high")),
                      {"deadline": "2026-12-01", "concepts": {}})
        with open(os.path.join(u, "questions.json"), "w", encoding="utf-8") as f:
            f.write("{{{")
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 1, out)
        self.assertIn("W_QUESTIONS_FILE", out)


class Rename(Base):
    def test_rename_moves_row_after_graph_rename(self):
        u = self.unit(graph(("a-new", "A", "-", "high")), {"concepts": {"a-old": row()}})
        code, out = sched(u, "rename", "a-old", "a-new")
        self.assertEqual(code, 0, out)
        m = load(os.path.join(u, "mastery.json"))
        self.assertIn("a-new", m["concepts"])
        self.assertNotIn("a-old", m["concepts"])

    def test_rename_refusals(self):
        u = self.unit(graph(("a", "A", "-", "high"), ("b", "B", "-", "high")),
                      {"concepts": {"a": row(), "b": row()}})
        code, out = sched(u, "rename", "ghost", "a")
        self.assertEqual(code, 1, out)
        code, out = sched(u, "rename", "a", "b")
        self.assertEqual(code, 1, out)
        self.assertIn("already has a state row", out)
        code, out = sched(u, "rename", "a", "zz-nowhere")
        self.assertEqual(code, 1, out)
        self.assertIn("not in concepts.md", out)


class Metadata(Base):
    def test_fix_keeps_dict_metadata(self):
        u = self.unit(graph(("a", "A", "-", "high")),
                      {"exam": {"date": "2026-06-01", "room": "B2"},
                       "a": {"score": 0.5, "attempts": 1, "next_due": "2026-03-01", "interval": 1}})
        sched(u, "check", "--fix", "--date", T)
        m = load(os.path.join(u, "mastery.json"))
        self.assertEqual(m["exam"]["date"], "2026-06-01")

    def test_record_keeps_dict_metadata_on_flat_file(self):
        u = self.unit(graph(("a", "A", "-", "high")),
                      {"exam": {"date": "2026-06-01"},
                       "a": {"score": 0.5, "attempts": 1, "next_due": "2026-03-01", "interval": 1}})
        sched(u, "record", "a", "hit", "--date", T)
        m = load(os.path.join(u, "mastery.json"))
        self.assertEqual(m["exam"]["date"], "2026-06-01")
        self.assertEqual(m["concepts"]["a"]["attempts"], 2)


class AuditFixes(Base):
    """Regressions found by the v2.2 audit. Each one crashed, lost data, or
    printed a wrong number before 2.2.1."""

    def write(self, u, name, text, mode="w"):
        with open(os.path.join(u, name), mode) as f:
            f.write(text)

    def test_self_prereq_and_cycle_give_no_self_credit(self):
        for rows in ((("a", "A", "a", "high"),),
                     (("a", "A", "b", "high"), ("b", "B", "a", "high"))):
            u = self.unit(graph(*rows), {"concepts": {"a": row(score=0.9, attempts=3, interval=4)}},
                          name="u%d" % len(rows))
            code, out = sched(u, "record", "a", "hit", "--date", T)
            self.assertEqual(code, 0, out)
            c = load(os.path.join(u, "mastery.json"))["concepts"]["a"]
            self.assertEqual(c["interval"], 10.0, out)
            self.assertNotIn("implicit", c)

    def test_gain_ignores_a_later_pre_test(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        sched(u, "test", "pre", 2, 10, "--label", "X", "--date", "2026-01-01")
        sched(u, "test", "post", 8, 10, "--label", "X", "--date", "2026-01-05")
        sched(u, "test", "pre", 9, 10, "--label", "X", "--date", "2026-02-01")
        code, out = sched(u, "tests")
        self.assertIn("gain +60 pts", out)
        self.assertNotIn("gain -10", out)

    def test_post_before_any_pre_is_unpaired(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"deadline": "2026-12-01", "concepts": {}})
        code, out = sched(u, "test", "post", 8, 10, "--label", "X", "--date", "2026-01-05")
        self.assertIn("no earlier pre-test", out)
        sched(u, "test", "pre", 2, 10, "--label", "X", "--date", "2026-02-01")
        code, out = sched(u, "check", "--date", T)
        self.assertIn("I_UNPAIRED_POST", out)

    def test_hint_hold_keeps_the_one_day_floor(self):
        u = self.unit(graph(("a", "A", "-", "high")),
                      {"concepts": {"a": row(interval=0.3, hint_streak=1)}})
        sched(u, "record", "a", "hint", "--date", T)
        self.assertEqual(load(os.path.join(u, "mastery.json"))["concepts"]["a"]["interval"], 1.0)

    def test_bad_questions_concepts_do_not_crash(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"deadline": "2026-12-01", "concepts": {}})
        self.write(u, "questions.json", json.dumps({"items": {
            "q1": {"concept": ["a"], "state": "unseen"},
            "q2": {"concept": 5, "state": "unseen"},
            "q3": {"concept": "a", "state": "unseen"}}}))
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 1, out)
        self.assertIn("W_QUESTIONS_ENTRY", out)
        self.assertNotIn("Traceback", out)
        code, out = sched(u, "questions")
        self.assertEqual(code, 0, out)

    def test_unreadable_text_files_exit_2_without_traceback(self):
        u = self.unit(None, {"concepts": {}})
        self.write(u, "concepts.md", b"| id | prereqs | yield |\n|---|---|---|\n| caf\xe9 | - | high |\n", "wb")
        for cmd in (("due",), ("check",), ("record", "a", "hit")):
            p = subprocess.run([sys.executable, SCHED, u] + list(cmd), capture_output=True, text=True)
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)

    def test_bom_state_is_read_not_quarantined(self):
        u = self.unit(graph(("a", "A", "-", "high")))
        self.write(u, "mastery.json", ("\ufeff" + json.dumps({"deadline": "2026-12-01",
                   "concepts": {"a": row()}})).encode("utf-8"), "wb")
        code, out = sched(u, "check", "--fix", "--date", T)
        self.assertNotIn("E_STATE_CORRUPT", out)
        self.assertFalse(os.path.exists(os.path.join(u, "mastery.json.corrupt")))
        self.assertIn("a", load(os.path.join(u, "mastery.json"))["concepts"])

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root reads anything")
    def test_unopenable_state_is_refused_and_never_moved(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {"a": row()}})
        path = os.path.join(u, "mastery.json")
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o644)
        code, out = sched(u, "check", "--fix", "--date", T)
        self.assertEqual(code, 2, out)
        self.assertIn("E_STATE_UNREADABLE", out)
        self.assertTrue(os.path.exists(path))
        self.assertFalse(os.path.exists(path + ".corrupt"))
        code, out = sched(u, "record", "a", "hit", "--date", T)
        self.assertEqual(code, 2, out)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root writes anything")
    def test_unwritable_unit_exits_2_without_traceback(self):
        u = self.unit(graph(("a", "A", "-", "high")))
        os.chmod(u, 0o555)
        self.addCleanup(os.chmod, u, 0o755)
        p = subprocess.run([sys.executable, SCHED, u, "record", "a", "hit"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertNotIn("Traceback", p.stderr)

    def test_quarantine_never_overwrites_a_backup(self):
        u = self.unit(graph(("a", "A", "-", "high")))
        path = os.path.join(u, "mastery.json")
        self.write(u, "mastery.json.corrupt", "first")
        self.write(u, "mastery.json", "{{second")
        sched(u, "check", "--fix")
        with open(path + ".corrupt") as f:
            self.assertEqual(f.read(), "first")
        with open(path + ".corrupt-2") as f:
            self.assertEqual(f.read(), "{{second")

    def test_rename_carries_question_items(self):
        u = self.unit(graph(("a2", "A", "-", "high")), {"concepts": {"a": row()}})
        self.write(u, "questions.json", json.dumps({"version": 1, "items": {
            "q1": {"concept": "a", "state": "unseen", "last": None}}}))
        code, out = sched(u, "rename", "a", "a2")
        self.assertEqual(code, 0, out)
        q = load(os.path.join(u, "questions.json"))
        self.assertEqual(q["items"]["q1"]["concept"], "a2")
        self.assertEqual(q["version"], 1)

    def test_rename_warns_without_a_graph(self):
        u = self.unit(None, {"concepts": {"a": row()}})
        code, out = sched(u, "rename", "a", "b")
        self.assertEqual(code, 0, out)
        self.assertIn("could not be validated", out)

    def test_questions_file_keeps_top_level_keys(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        self.write(u, "questions.json", json.dumps({"version": 3, "items": {}}))
        sched(u, "questions", "add", "q1", "a")
        sched(u, "questions", "mark", "q1", "burnt", "--date", T)
        self.assertEqual(load(os.path.join(u, "questions.json"))["version"], 3)

    def test_questions_report_lists_drilled_concepts_with_no_items(self):
        u = self.unit(graph(("a", "A", "-", "high"), ("b", "B", "-", "low")),
                      {"concepts": {"a": row(attempts=2)}})
        self.write(u, "questions.json", json.dumps({"items": {
            "q1": {"concept": "b", "state": "unseen", "last": None}}}))
        code, out = sched(u, "questions")
        self.assertRegex(out, r"a\s+unseen\s+0 .*LOW")

    def test_flat_row_named_tests_keeps_test_history(self):
        u = self.unit(graph(("tests", "T", "-", "high")),
                      {"x": {"score": 0.5, "attempts": 1},
                       "tests": [{"kind": "pre", "label": "", "correct": 1, "total": 2,
                                  "date": "2026-01-01"}]})
        code, out = sched(u, "record", "tests", "hit", "--date", T)
        self.assertEqual(code, 0, out)
        m = load(os.path.join(u, "mastery.json"))
        self.assertIsInstance(m["tests"], list)
        self.assertEqual(m["concepts"]["tests"]["attempts"], 1)

    def test_flag_values_and_dates_are_strict(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {}})
        for args in (("record", "a", "miss", "--error", "--override"),
                     ("record", "a", "hit", "--date", "2026-01-01junk"),
                     ("due", "--limit", "0"), ("due", "--limit", "-3")):
            code, out = sched(u, *args)
            self.assertEqual(code, 2, (args, out))
        self.assertEqual(load(os.path.join(u, "mastery.json")), {"concepts": {}})

    def test_check_reports_and_fixes_type_drift(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"deadline": "2026-12-01", "concepts": {
            "a": row(score="0.5", attempts="2", errors="old-note", confidence=99, hint_streak=-4)}})
        code, out = sched(u, "check", "--date", T)
        self.assertEqual(code, 1, out)
        for field in ("score", "attempts", "errors", "confidence", "hint_streak"):
            self.assertRegex(out, r"W_FIELD_TYPE\s+a %s" % field)
        code, out = sched(u, "check", "--fix", "--date", T)
        c = load(os.path.join(u, "mastery.json"))["concepts"]["a"]
        self.assertEqual((c["score"], c["attempts"], c["errors"]), (0.5, 2, ["old-note"]))
        self.assertEqual(c["confidence"], 99, "not reversible, so left for a human")
        self.assertIn("cannot", out)

    def test_record_keeps_a_hand_written_error_note(self):
        u = self.unit(graph(("a", "A", "-", "high")), {"concepts": {"a": row(errors="old-note")}})
        sched(u, "record", "a", "miss", "--error", "new", "--date", T)
        self.assertEqual(load(os.path.join(u, "mastery.json"))["concepts"]["a"]["errors"],
                         ["old-note", "new"])


if __name__ == "__main__":
    unittest.main()
