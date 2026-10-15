#!/usr/bin/env python3
"""Spacing scheduler with prerequisite credit, pre/post tests, and a state check.

Reads <unit>/concepts.md (markdown table with id, prereqs, yield columns) and
updates <unit>/mastery.json in place. Canonical shape, the shape `check --fix`
migrates anything else into:

  {
    "deadline": "YYYY-MM-DD",            # optional; caps every next_due
    "concepts": {
      "<concept-id>": {
        "score": 0.0,                    # 0..1, EWMA of hit 1 / hint 0.5 / miss 0
        "attempts": 0,                   # graded attempts
        "interval": 1.0,                 # days, current spacing
        "last": "YYYY-MM-DD",            # last graded attempt
        "next_due": "YYYY-MM-DD",        # when it comes back
        "errors": ["..."],               # named error classes, not a diary
        "override": true                 # only when a grade was overridden
      }
    },
    "tests": [{"date": "..", "kind": "pre"|"post", "label": "..", "correct": n, "total": n}]
  }

Commands:
  schedule.py UNIT record ID hit|hint|miss [--date D] [--deadline D] [--force]
  schedule.py UNIT due [--date D] [--limit 10] [--json]
  schedule.py UNIT test pre|post CORRECT TOTAL [--label "Ch 5 Vision"] [--date D]
  schedule.py UNIT tests [--json]
  schedule.py UNIT check [--date D] [--json] [--fix]

Rules (the skill's Spacing section):
  hit (first try)  interval x 2.5    hint  interval x 1.5    miss  interval = 1 day
  A hit passes implicit credit down the prerequisite graph: direct prereqs get
  0.5 of a hit, theirs 0.25, and so on (stops under 0.1). Credit only ever pushes
  next_due later, and skips prereqs never learned (score < 0.5).
  A miss pulls weak direct prereqs (score < 0.7) to tomorrow: the miss may be a
  prerequisite gap.
  next_due never lands past the deadline (--deadline, or deadline in mastery.json).
  `due` ranks due concepts by knockout value: reviewing an advanced concept also
  covers its due prerequisites, so the one covering the most goes first, then yield.

`record` refuses a concept id that is not in concepts.md unless --force is given,
and prints the closest ids. That refusal is the guard against orphan rows, which
is how a state file quietly stops describing the unit.

`check` reports what a session should know before drilling: ids in the state that
are not in the graph, graph ids with no state row, missing or malformed fields,
malformed prerequisites, cycles, stale next_due values, a missing deadline, and
pre-tests with no matching post-test. Exit code 0 clean, 1 warnings, 2 errors.
`--fix` repairs only what is reversible (shape migration, missing fields, score
clamping, unknown field removal). It never deletes a concept row.
"""
import datetime as dt, difflib, json, os, re, sys

YIELD = {"high": 3, "medium": 2, "low": 1}
CONCEPT_FIELDS = ["score", "attempts", "interval", "last", "next_due", "errors"]
RETURN = {"hit": 1.0, "hint": 0.5, "miss": 0.0}


# ---------------------------------------------------------------- graph + state

def parse_concepts(unit):
    """concepts.md -> {id: {prereqs, yield, name}}. Empty when unreadable."""
    graph = {}
    path = os.path.join(unit, "concepts.md")
    if not os.path.exists(path):
        return graph
    header = None
    for line in open(path, encoding="utf-8"):
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            low = [re.sub(r"[*`]", "", c).lower() for c in cells]
            if "id" in low:
                header = low
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        row = dict(zip(header, cells))
        cid = clean(row.get("id", ""))
        if not cid:
            continue
        pre = clean(row.get("prereqs", ""))
        prereqs = [p.strip() for p in re.split(r"[,;]", pre)
                   if re.search(r"[A-Za-z0-9]", p) and p.strip().lower() not in ("none", "-")]
        y = re.sub(r"[^a-z]", "", row.get("yield", "").lower())
        graph[cid] = {"prereqs": prereqs, "yield": y if y in YIELD else "low",
                      "name": row.get("name", "")}
    return graph


def clean(s):
    return re.sub(r"[*`]", "", s or "").strip()


def load(unit):
    """-> (data, store, path, shape). shape: canonical | types | flat | empty."""
    path = os.path.join(unit, "mastery.json")
    data = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {"concepts": {}}
    if not isinstance(data, dict):
        data = {"concepts": {}}
    if isinstance(data.get("concepts"), dict):
        return data, data["concepts"], path, "canonical"
    if isinstance(data.get("types"), dict):
        return data, data["types"], path, "types"
    store = {k: v for k, v in data.items()
             if isinstance(v, dict) and ("score" in v or "attempts" in v or "next_due" in v)}
    return data, store, path, ("flat" if store else "empty")


def save(data, store, path):
    if not isinstance(data.get("concepts"), dict):
        keep = {k: v for k, v in data.items() if not isinstance(v, dict) or k == "tests"}
        data = {"concepts": store}
        data.update({k: v for k, v in keep.items() if k != "concepts"})
    tmp = path + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def d(s):
    return dt.date.fromisoformat(str(s)[:10])


def safe_d(s, default=None):
    """Parse a date, returning default instead of raising. Hand-edited files exist."""
    try:
        return d(s)
    except (ValueError, TypeError, IndexError):
        return default


def days(iv):
    """Days for an interval, rounded half up: round(2.5) is 2 in Python, which is a trap."""
    return max(1, int(float(iv) + 0.5))


def capped(day, deadline):
    return min(day, deadline) if deadline else day


def arg(a, name, default=None):
    return a[a.index(name) + 1] if name in a else default


def nearest(cid, graph, n=3):
    return difflib.get_close_matches(cid, list(graph), n=n, cutoff=0.4)


def ancestors(graph, cid):
    out, stack = {}, [(p, 1) for p in graph.get(cid, {}).get("prereqs", [])]
    while stack:
        p, depth = stack.pop()
        if p in out and out[p] <= depth:
            continue
        out[p] = depth
        stack += [(q, depth + 1) for q in graph.get(p, {}).get("prereqs", [])]
    return out


def cycles(graph):
    """Return one list of ids per prerequisite cycle found."""
    found, state = [], {}

    def walk(cid, path):
        state[cid] = 1
        for p in graph.get(cid, {}).get("prereqs", []):
            if p not in graph:
                continue
            if state.get(p) == 1:
                i = path.index(p) if p in path else 0
                found.append(path[i:] + [p])
            elif state.get(p) is None:
                walk(p, path + [p])
        state[cid] = 2

    for cid in graph:
        if state.get(cid) is None:
            walk(cid, [cid])
    return found


# -------------------------------------------------------------------- commands

def record(unit, cid, result, today, deadline, force=False):
    graph = parse_concepts(unit)
    data, store, path, shape = load(unit)
    if not graph:
        print("warning: no parseable concepts.md here, so '%s' could not be validated." % cid)
    elif cid not in graph and not force:
        close = nearest(cid, graph)
        print("refused: '%s' is not in concepts.md." % cid)
        if close:
            print("  closest ids: %s" % ", ".join(close))
        print("  add the row to concepts.md, use one of those ids, or pass --force.")
        return 1
    if graph and cid not in graph:
        print("warning: '%s' is not in concepts.md; recorded anyway (--force)." % cid)
    deadline = deadline or safe_d(data.get("deadline"))
    c = store.setdefault(cid, {"score": 0.0, "attempts": 0})
    iv = float(c.get("interval", 1))
    if result == "hit":
        iv = max(1.0, iv * 2.5)
    elif result == "hint":
        iv = max(1.0, iv * 1.5)
    else:
        iv = 1.0
    c["interval"] = round(iv, 2)
    c["attempts"] = c.get("attempts", 0) + 1
    c["score"] = round(0.7 * float(c.get("score") or 0) + 0.3 * RETURN[result], 3)
    c["last"] = today.isoformat()
    c["next_due"] = capped(today + dt.timedelta(days=days(iv)), deadline).isoformat()
    log = ["%s: %s, interval %g d, next %s" % (cid, result, iv, c["next_due"])]
    if result == "hit":
        for p, depth in sorted(ancestors(graph, cid).items(), key=lambda x: x[1]):
            credit = 0.5 ** depth
            pc = store.get(p)
            if credit < 0.1 or pc is None or float(pc.get("score") or 0) < 0.5:
                continue
            piv = float(pc.get("interval", 1)) * (1 + 1.5 * credit)
            new = capped(today + dt.timedelta(days=days(piv)), deadline)
            old = safe_d(pc.get("next_due"), today)
            if new > old:
                pc["interval"] = round(piv, 2)
                pc["next_due"] = new.isoformat()
                pc["implicit"] = round(pc.get("implicit", 0) + credit, 3)
                log.append("  credit %g -> %s: next %s" % (credit, p, pc["next_due"]))
    elif result == "miss":
        for p in graph.get(cid, {}).get("prereqs", []):
            pc = store.get(p)
            if pc is not None and float(pc.get("score") or 0) < 0.7:
                pc["next_due"] = (today + dt.timedelta(days=1)).isoformat()
                log.append("  weak prereq %s pulled to tomorrow" % p)
    save(data, store, path)
    print("\n".join(log))
    return 0


def due(unit, today, limit, as_json=False):
    graph = parse_concepts(unit)
    data, store, _, _ = load(unit)
    ids = set(graph) | set(store)
    is_due = {i for i in ids
              if safe_d(store.get(i, {}).get("next_due"), today) <= today}
    rows = []
    for i in is_due:
        covers = [p for p in ancestors(graph, i) if p in is_due]
        y = graph.get(i, {}).get("yield", "low")
        rows.append((len(covers), YIELD[y], -float(store.get(i, {}).get("score") or 0), i, covers, y))
    rows.sort(reverse=True)
    picked, covered = [], set()
    for r in rows:
        if r[3] in covered:
            continue
        picked.append(r)
        covered.update(r[4])
        covered.add(r[3])
        if len(picked) >= limit:
            break
    if as_json:
        print(json.dumps({"date": today.isoformat(), "due": len(is_due),
                          "deadline": data.get("deadline"),
                          "order": [{"id": r[3], "yield": r[5], "score": round(-r[2], 3),
                                     "also_covers": r[4]} for r in picked]}, indent=2))
        return 0
    print("%d due on %s; review order (covered prereqs skipped):" % (len(is_due), today))
    for n, _, s, i, covers, y in picked:
        extra = ", also covers %s" % ", ".join(covers) if covers else ""
        print("  %s [%s, score %.2f]%s" % (i, y, -s, extra))
    if not data.get("deadline"):
        print("note: no deadline in mastery.json, so reviews are not capped. "
              "Pass --deadline, or set it (the skill records it at ingest).")
    if len(picked) < len(is_due):
        print("  (%d more due, --limit to see them)" % (len(is_due) - len(picked)))
    return 0


def test(unit, kind, correct, total, label, today):
    if kind not in ("pre", "post"):
        print("refused: kind must be pre or post, got '%s'." % kind)
        return 1
    if total <= 0 or correct < 0 or correct > total:
        print("refused: %d/%d is not a possible score." % (correct, total))
        return 1
    data, store, path, _ = load(unit)
    tests = data.setdefault("tests", [])
    if kind == "post":
        wants = [t for t in tests if t["kind"] == "pre" and (t.get("label") or "") == (label or "")]
        if not wants:
            print("warning: no pre-test labelled '%s' to compare this against." % (label or ""))
    tests.append({"date": today.isoformat(), "kind": kind, "label": label,
                  "correct": correct, "total": total})
    save(data, store, path)
    show(unit)
    return 0


def show(unit, as_json=False):
    data, _, _, _ = load(unit)
    tests = data.get("tests", [])
    if as_json:
        print(json.dumps(tests, indent=2))
        return 0
    pre = None
    for t in tests:
        total = t.get("total") or 0
        pct = 100 * (t.get("correct") or 0) / total if total else 0
        line = "%s %-4s %s/%s (%.0f%%) %s" % (t.get("date"), t.get("kind"), t.get("correct"),
                                              t.get("total"), pct, t.get("label") or "")
        if t.get("kind") == "pre":
            pre = (pct, t.get("label"))
        elif pre and pre[1] == t.get("label"):
            line += "  gain %+.0f pts" % (pct - pre[0])
        print(line)
    return 0


def analyze(unit, today):
    """Findings about one unit's graph and state. Read-only."""
    graph = parse_concepts(unit)
    data, store, path, shape = load(unit)
    findings = []

    def add(sev, code, msg, cid=None):
        findings.append({"severity": sev, "code": code, "concept": cid, "message": msg})

    # ---- graph
    if not graph and (store or os.path.exists(os.path.join(unit, "mastery.json"))):
        add("warning", "W_NO_GRAPH",
            "concepts.md is missing or has no parseable rows, so state cannot be validated")
    for cid, g in sorted(graph.items()):
        for p in g["prereqs"]:
            if p == cid:
                add("error", "E_PREREQ_SELF", "%s lists itself as a prerequisite" % cid, cid)
            elif p not in graph:
                close = nearest(p, graph, 1)
                add("error", "E_PREREQ_MISSING",
                    "%s has prereq '%s', which is not a concept id%s"
                    % (cid, p, (" (did you mean '%s'?)" % close[0]) if close else ""), cid)
    for cycle in cycles(graph):
        add("error", "E_PREREQ_CYCLE", "prerequisite cycle: %s" % " -> ".join(cycle))

    # ---- state
    orphans = sorted(set(store) - set(graph))
    untracked = sorted(set(graph) - set(store))
    for cid in orphans:
        close = nearest(cid, graph)
        add("warning", "W_ORPHAN",
            "%s is in mastery.json but not in concepts.md%s"
            % (cid, (" (closest: %s)" % ", ".join(close)) if close else ""), cid)
    if untracked:
        add("info", "I_UNTRACKED",
            "%d of %d graph concepts have no state row yet: %s"
            % (len(untracked), len(graph),
               ", ".join(untracked[:5]) + (" ..." if len(untracked) > 5 else "")))
    drilled = any(float(c.get("score") or 0) for c in store.values() if isinstance(c, dict)) \
        or bool(data.get("tests"))
    if store and drilled and len(untracked) > max(5, int(0.5 * len(graph))):
        add("warning", "W_STATE_BEHIND",
            "the unit has been drilled but %d of %d graph concepts still have no state row; "
            "either the graph grew past the state or sessions stopped writing it, so the "
            "review queue cannot be trusted until they are reconciled" % (len(untracked), len(graph)))
    for cid in sorted(store):
        c = store[cid]
        if not isinstance(c, dict):
            add("error", "E_ROW_TYPE", "%s is %s, not an object" % (cid, type(c).__name__), cid)
            continue
        for f in CONCEPT_FIELDS:
            if f not in c and f not in ("last", "errors"):
                add("warning", "W_FIELD_MISSING", "%s has no '%s'; --fix fills a default" % (cid, f), cid)
            elif f not in c:
                add("info", "I_FIELD_ABSENT", "%s has no '%s' yet (fine until it is graded)" % (cid, f), cid)
        for f in c:
            if f not in CONCEPT_FIELDS + ["implicit", "override", "error_patterns"]:
                add("warning", "W_FIELD_UNKNOWN", "%s has unknown field '%s'; --fix drops it" % (cid, f), cid)
        try:
            s = float(c.get("score", 0))
            if not 0.0 <= s <= 1.0:
                add("error", "E_SCORE_RANGE", "%s score %s is outside 0..1; --fix clamps it" % (cid, s), cid)
        except (TypeError, ValueError):
            add("error", "E_SCORE_TYPE", "%s score %r is not a number" % (cid, c.get("score")), cid)
        if c.get("next_due"):
            try:
                when = d(c["next_due"])
                if when < today:
                    add("info", "I_STALE_DUE", "%s was due %s" % (cid, c["next_due"]), cid)
            except ValueError:
                add("error", "E_NEXT_DUE", "%s next_due %r is not a date; --fix rebuilds it from interval"
                    % (cid, c.get("next_due")), cid)
        try:
            if float(c.get("interval", 1)) <= 0:
                add("error", "E_INTERVAL", "%s interval must be positive" % cid, cid)
        except (TypeError, ValueError):
            add("error", "E_INTERVAL", "%s interval %r is not a number" % (cid, c.get("interval")), cid)

    # ---- deadline
    if not data.get("deadline") and (store or graph):
        add("warning", "W_NO_DEADLINE",
            "no deadline in mastery.json, so reviews are never capped; record it when it is known")
    else:
        try:
            if data.get("deadline"):
                d(data["deadline"])
        except ValueError:
            add("error", "E_DEADLINE", "deadline %r is not a date" % data.get("deadline"))

    # ---- tests
    pre_by_label = {}
    for t in data.get("tests", []):
        if not (t.get("total") or 0) > 0:
            add("warning", "W_TEST_TOTAL", "a %s test has total %r" % (t.get("kind"), t.get("total")))
        elif (t.get("correct") or 0) > t["total"]:
            add("warning", "W_TEST_TOTAL", "a %s test scores %s/%s" % (t.get("kind"), t.get("correct"), t["total"]))
        if t.get("kind") == "pre":
            pre_by_label[t.get("label") or ""] = t
    for t in data.get("tests", []):
        if t.get("kind") == "post" and (t.get("label") or "") not in pre_by_label:
            add("info", "I_UNPAIRED_POST",
                "post-test '%s' has no matching pre-test, so no gain can be shown" % (t.get("label") or ""))

    # ---- shape
    if shape in ("types", "flat"):
        add("warning", "W_LEGACY_SHAPE",
            "mastery.json uses the legacy '%s' shape; --fix rewrites it in the canonical shape" % shape)

    return findings, graph, data, store, path, shape


def _repair(data, store, path, shape, today):
    """Repair only what is reversible. Never deletes a concept row."""
    fixed = []
    try:
        deadline = d(data["deadline"]) if data.get("deadline") else None
    except ValueError:
        deadline = None
    if shape in ("types", "flat"):
        if shape == "types":
            data["concepts"] = store
            data.pop("types", None)
        else:
            keep = {k: v for k, v in data.items() if not isinstance(v, dict)}
            data = {"concepts": store}
            data.update(keep)
        data.setdefault("concepts", store)
        fixed.append("migrated mastery.json to the canonical shape")
    for cid in list(store):
        c = store[cid]
        if not isinstance(c, dict):
            continue
        for f, v in (("score", 0.0), ("attempts", 0), ("interval", 1.0),
                     ("last", None), ("errors", [])):
            if f not in c:
                c[f] = v
                fixed.append("%s.%s = %r" % (cid, f, v))
        if not c.get("next_due"):
            try:
                step = days(c.get("interval") or 1)
            except (TypeError, ValueError):
                step = 1
            c["next_due"] = capped(today + dt.timedelta(days=step), deadline).isoformat()
            fixed.append("%s.next_due = %s (from interval)" % (cid, c["next_due"]))
        try:
            s = float(c.get("score", 0))
            if not 0.0 <= s <= 1.0:
                c["score"] = min(1.0, max(0.0, s))
                fixed.append("%s.score clamped to %s" % (cid, c["score"]))
        except (TypeError, ValueError):
            c["score"] = 0.0
            fixed.append("%s.score reset to 0.0" % cid)
        try:
            if float(c.get("interval", 1)) <= 0:
                c["interval"] = 1.0
                fixed.append("%s.interval reset to 1.0" % cid)
        except (TypeError, ValueError):
            c["interval"] = 1.0
            fixed.append("%s.interval reset to 1.0" % cid)
        if c.get("next_due"):
            try:
                d(c["next_due"])
            except ValueError:
                try:
                    step = days(c.get("interval") or 1)
                except (TypeError, ValueError):
                    step = 1
                c["next_due"] = capped(today + dt.timedelta(days=step), deadline).isoformat()
                fixed.append("%s.next_due rebuilt as %s" % (cid, c["next_due"]))
        for f in [f for f in c if f not in CONCEPT_FIELDS + ["implicit", "override", "error_patterns"]]:
            c.pop(f, None)
            fixed.append("%s dropped unknown field '%s'" % (cid, f))
    if data.get("deadline"):
        try:
            d(data["deadline"])
        except ValueError:
            data.pop("deadline", None)
            fixed.append("dropped malformed deadline")
    save(data, store, path)
    return fixed


def check(unit, today, fix=False, as_json=False):
    findings, graph, data, store, path, shape = analyze(unit, today)
    fixed = []
    if fix:
        fixed = _repair(data, store, path, shape, today)
        findings, graph, data, store, path, shape = analyze(unit, today)

    errors = [f for f in findings if f["severity"] == "error"]
    warns = [f for f in findings if f["severity"] == "warning"]
    code = 2 if errors else (1 if warns else 0)

    if as_json:
        print(json.dumps({"unit": unit, "shape": shape, "graph_concepts": len(graph),
                          "state_concepts": len(store), "deadline": data.get("deadline"),
                          "errors": len(errors), "warnings": len(warns),
                          "findings": findings, "fixed": fixed, "exit": code}, indent=2))
        return code

    print("%s: %d concepts in the graph, %d with state, shape %s, exit %d"
          % (unit, len(graph), len(store), shape, code))
    for f in findings:
        print("  %-7s %-18s %s" % (f["severity"], f["code"], f["message"]))
    for line in fixed:
        print("  fixed   %s" % line)
    if not findings and not fixed:
        print("  clean")
    return code


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    unit, cmd = os.path.expanduser(a[0]), a[1]
    if not os.path.isdir(unit):
        sys.exit("schedule.py: %s is not a folder. Point it at a study unit." % unit)
    today = d(arg(a, "--date", dt.date.today().isoformat()))
    dl = arg(a, "--deadline")
    if cmd == "record":
        if len(a) < 4:
            sys.exit("usage: schedule.py UNIT record ID hit|hint|miss")
        if a[3] not in RETURN:
            sys.exit("schedule.py: result must be hit, hint or miss, got '%s'." % a[3])
        return record(unit, a[2], a[3], today, d(dl) if dl else None, "--force" in a)
    if cmd == "due":
        return due(unit, today, int(arg(a, "--limit", 10)), "--json" in a)
    if cmd == "test":
        if len(a) < 5:
            sys.exit("usage: schedule.py UNIT test pre|post CORRECT TOTAL [--label ..]")
        return test(unit, a[2], int(a[3]), int(a[4]), arg(a, "--label", ""), today)
    if cmd == "tests":
        return show(unit, "--json" in a)
    if cmd == "check":
        return check(unit, today, "--fix" in a, "--json" in a)
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
