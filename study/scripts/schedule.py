#!/usr/bin/env python3
"""Spacing scheduler with prerequisite credit, pre/post tests, a state check,
and the fresh-question reserve ledger.

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
        "hint_streak": 0,                # consecutive hint-graded attempts
        "confidence": 4,                 # last confidence rating, 1 to 5
        "override": true                 # only when a grade was overridden
      }
    },
    "tests": [{"date": "..", "kind": "pre"|"post", "label": "..", "correct": n, "total": n}]
  }

Commands:
  schedule.py UNIT record ID hit|hint|miss [--date D] [--deadline D] [--force]
      [--error CLASS] [--confidence 1-5] [--override]
  schedule.py UNIT due [--date D] [--limit 10] [--json]
  schedule.py UNIT test pre|post CORRECT TOTAL [--label "Ch 5 Vision"] [--date D]
      [--conditions supported|open-book|timed]
  schedule.py UNIT tests [--json]
  schedule.py UNIT check [--date D] [--json] [--fix]
  schedule.py UNIT rename OLD NEW [--force]
  schedule.py UNIT questions [--json]
  schedule.py UNIT questions add ID CONCEPT [--state S] [--force]
  schedule.py UNIT questions mark ID STATE [--date D]

Rules (the skill's Spacing section):
  hit (first try)  interval x 2.5    hint  interval x 1.5    miss  interval = 1 day
  A second hint-graded attempt in a row holds the interval where it is; a third
  resets it to a day. Intervals stay between 1 and 90 days. An interval that
  would land past the deadline is shortened to about 60% of the remaining
  window, so the final reviews taper in instead of stacking on deadline day.
  A hit passes implicit credit down the prerequisite graph: direct prereqs get
  0.5 of a hit, theirs 0.25, and so on (stops under 0.1). Credit only ever pushes
  next_due later, and skips prereqs never learned (score < 0.5).
  A miss pulls weak direct prereqs (score < 0.7) to tomorrow: the miss may be a
  prerequisite gap.
  `due` ranks due concepts by knockout value: reviewing an advanced concept also
  covers its due prerequisites, so the one covering the most goes first, then yield.

`record` refuses a concept id that is not in concepts.md unless --force is given,
and prints the closest ids. That refusal is the guard against orphan rows, which
is how a state file quietly stops describing the unit. `rename` moves a state row
onto a real graph id, so an orphan can be reconciled without hand-editing state.

`check` reports what a session should know before drilling: ids in the state that
are not in the graph, graph ids with no state row, missing or malformed fields,
malformed prerequisites, cycles, stale next_due values, a missing deadline,
pre-tests with no matching post-test, and a low fresh-question reserve when
`questions.json` exists. Exit code 0 clean, 1 warnings, 2 errors. `--fix`
repairs only what is reversible (shape migration, missing fields, score
clamping, numeric text converted, unknown field removal) and never deletes a
concept row. A mastery.json that does not parse, or whose `concepts` is not an
object, is reported and never overwritten; `--fix` moves it aside as
mastery.json.corrupt, bytes preserved, never over an earlier backup. One that
exists but cannot be opened (permissions) is refused and never moved.
`rename` also moves the questions.json items that tracked the old id.

Exit codes, any command: 0 done or clean; 1 warnings, or a write refused;
2 errors, or the command could not run (bad arguments, unreadable state).
"""
import datetime as dt, difflib, json, math, os, re, sys

YIELD = {"high": 3, "medium": 2, "low": 1}
CONCEPT_FIELDS = ["score", "attempts", "interval", "last", "next_due", "errors"]
EXTRA_FIELDS = ["implicit", "override", "error_patterns", "hint_streak", "confidence"]
ALLOWED_FIELDS = CONCEPT_FIELDS + EXTRA_FIELDS
RETURN = {"hit": 1.0, "hint": 0.5, "miss": 0.0}
CONDITIONS = ("supported", "open-book", "timed")
INTERVAL_CEILING = 90
COMPRESS = 0.6
QUESTION_STATES = ("unseen", "seen-correct", "seen-wrong", "taught-not-drilled", "burnt")
RESERVE_FLOOR = {"high": 3, "medium": 2, "low": 1}


class UsageError(Exception):
    """Bad flags or unreadable state: the command did not run."""


# ---------------------------------------------------------------- graph + state

def parse_concepts(unit):
    """concepts.md -> {id: {prereqs, yield, name}}. Empty when unreadable."""
    graph = {}
    path = os.path.join(unit, "concepts.md")
    if not os.path.exists(path):
        return graph
    try:
        with open(path, encoding="utf-8-sig") as f:
            lines = f.readlines()
    except (OSError, ValueError) as e:
        raise UsageError("%s could not be read as UTF-8 text (%s); fix or re-save it"
                         % (path, e.__class__.__name__))
    header = None
    for line in lines:
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
    """-> (data, store, path, shape).

    Shapes: canonical | types | flat | empty (no rows yet) | unreadable (the
    file exists but could not be opened: permissions, a folder) | corrupt
    (will not parse, or is not an object) | broken ('concepts' exists but is
    not an object of rows). Unreadable, corrupt and broken files are never
    written to. A UTF-8 byte order mark is accepted.
    """
    path = os.path.join(unit, "mastery.json")
    if not os.path.exists(path):
        data = {"concepts": {}}
        return data, data["concepts"], path, "empty"
    try:
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
    except OSError:
        data = {"concepts": {}}
        return data, data["concepts"], path, "unreadable"
    except ValueError:
        data = {"concepts": {}}
        return data, data["concepts"], path, "corrupt"
    try:
        data = json.loads(text)
    except ValueError:
        data = {"concepts": {}}
        return data, data["concepts"], path, "corrupt"
    if not isinstance(data, dict):
        data = {"concepts": {}}
        return data, data["concepts"], path, "corrupt"
    if "concepts" in data and not isinstance(data["concepts"], dict):
        data = {"concepts": {}}
        return data, data["concepts"], path, "broken"
    if isinstance(data.get("concepts"), dict):
        return data, data["concepts"], path, "canonical"
    if isinstance(data.get("types"), dict):
        return data, data["types"], path, "types"
    store = {k: v for k, v in data.items()
             if isinstance(v, dict) and ("score" in v or "attempts" in v or "next_due" in v)}
    return data, store, path, ("flat" if store else "empty")


def refuse_unusable(shape, path):
    """True when the state file cannot be read. Nothing may be written then."""
    if shape == "unreadable":
        print("refused: %s exists but could not be opened (permissions, or not a file); "
              "nothing was written." % path)
        print("  fix its permissions; it may be perfectly good state, so nothing moves it aside.")
        return True
    if shape == "corrupt":
        print("refused: %s does not parse as a JSON object; nothing was written." % path)
        print("  it holds your only state. Fix it by hand, or move it aside to start fresh.")
        return True
    if shape == "broken":
        print("refused: %s parses, but 'concepts' is not an object of rows; nothing was written." % path)
        print("  fix it by hand, or move it aside to start fresh; nothing overwrites it.")
        return True
    return False


def quarantine(path):
    """Move an unparseable state file aside, bytes intact. This never deletes,
    and never overwrites an earlier backup: the hard link fails if the name was
    taken, even by another process between the check and the move."""
    n = 1
    while True:
        backup = path + ".corrupt" if n == 1 else "%s.corrupt-%d" % (path, n)
        n += 1
        try:
            os.link(path, backup)
        except FileExistsError:
            continue
        except OSError:
            # filesystems without hard links (FAT, some network mounts)
            if os.path.exists(backup):
                continue
            os.replace(path, backup)
            return backup
        os.unlink(path)
        return backup


def legacy_metadata(data, store):
    """Top-level keys of a legacy file that are not its concept rows. Identity,
    not name: a new row called 'tests' must not swallow the real tests list."""
    return {k: v for k, v in data.items()
            if k not in ("concepts", "types") and not (k in store and store[k] is v)}


def save(data, store, path, shape):
    if shape in ("corrupt", "broken", "unreadable"):
        raise RuntimeError("refusing to write over unreadable state")
    if not isinstance(data.get("concepts"), dict):
        keep = legacy_metadata(data, store)
        data = {"concepts": store}
        data.update(keep)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
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


def parse_day(s):
    """A date argument from the command line, or a refusal. Never a traceback."""
    try:
        return dt.date.fromisoformat(s)
    except (ValueError, TypeError):
        raise UsageError("expected a date like 2026-03-01, got '%s'" % s)


def num(v, default=0.0):
    """float(v) when it is a real number, default otherwise. State is hand-edited."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f if math.isfinite(f) else default


def row_of(store, cid):
    """The state row for cid, or {} when it is missing or not an object."""
    c = store.get(cid)
    return c if isinstance(c, dict) else {}


def type_drift(c):
    """[(field, message, fixable)] for row fields whose JSON type is wrong but which
    the scheduler would otherwise read silently. Hand edits produce these."""
    out = []
    for f in ("score", "attempts", "interval"):
        v = c.get(f)
        if isinstance(v, (str, bool)) and num(v, None) is not None:
            out.append((f, "%s is %r, not a number; --fix converts it" % (f, v), True))
    a = c.get("attempts")
    if "attempts" in c and not isinstance(a, (str, bool)) and (num(a, None) is None or num(a) < 0):
        out.append(("attempts", "attempts %r is not a count" % (a,), False))
    e = c.get("errors")
    if "errors" in c and not isinstance(e, list):
        ok = isinstance(e, str) and bool(e)
        out.append(("errors", "errors is %s, not a list%s" % (type(e).__name__,
                    "; --fix wraps it in one" if ok else ""), ok))
    if "confidence" in c:
        v = c.get("confidence")
        if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 5:
            out.append(("confidence", "confidence %r is not a whole number 1 to 5" % (v,), False))
    if "hint_streak" in c:
        v = c.get("hint_streak")
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            out.append(("hint_streak", "hint_streak %r is not a count" % (v,), False))
    return out


def compress(iv, today, deadline):
    """Shorten an interval that would land past the deadline. Reviews taper in
    near the deadline instead of stacking onto deadline day."""
    if not deadline:
        return iv
    remaining = (deadline - today).days
    if remaining <= 0:
        return 1.0
    return max(1.0, round(remaining * COMPRESS, 2)) if days(iv) > remaining else iv


def arg(a, name, default=None):
    if name not in a:
        return default
    i = a.index(name)
    if i + 1 >= len(a) or a[i + 1].startswith("--"):
        raise UsageError("%s needs a value" % name)
    return a[i + 1]


def arg_all(a, name):
    """Every value given for a repeatable flag like --error."""
    out = []
    for i, tok in enumerate(a):
        if tok == name:
            if i + 1 >= len(a) or a[i + 1].startswith("--"):
                raise UsageError("%s needs a value" % name)
            out.append(a[i + 1])
    return out


def flags_ok(a, allowed):
    for tok in a:
        if tok.startswith("--") and tok not in allowed:
            raise UsageError("unknown flag %s here (known: %s)"
                             % (tok, ", ".join(sorted(allowed))))


def nearest(cid, graph, n=3):
    return difflib.get_close_matches(cid, list(graph), n=n, cutoff=0.4)


def ancestors(graph, cid):
    out, stack = {}, [(p, 1) for p in graph.get(cid, {}).get("prereqs", [])]
    while stack:
        p, depth = stack.pop()
        if p == cid:
            continue  # a self-prereq or a cycle: no concept credits or covers itself
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
            if p == cid:
                continue  # E_PREREQ_SELF reports self-references; not a cycle
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

def record(unit, cid, result, today, deadline, force=False, errors=(), confidence=None, override=False):
    graph = parse_concepts(unit)
    data, store, path, shape = load(unit)
    if refuse_unusable(shape, path):
        return 2
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
    if deadline is None:
        deadline = safe_d(data.get("deadline"))
    elif data.get("deadline") != deadline.isoformat():
        data["deadline"] = deadline.isoformat()
        print("deadline set to %s" % deadline.isoformat())
    existing = store.get(cid)
    if existing is not None and not isinstance(existing, dict):
        print("refused: row '%s' is %s, not an object; nothing was written."
              % (cid, type(existing).__name__))
        print("  run check to see it, then edit or remove that row by hand.")
        return 1
    c = store.setdefault(cid, {"score": 0.0, "attempts": 0})
    iv = num(c.get("interval"), 1.0)
    streak = max(0, int(num(c.get("hint_streak"), 0)))
    if result == "hit":
        iv = max(1.0, iv * 2.5)
    elif result == "hint":
        if streak >= 2:
            iv = 1.0
        elif streak == 0:
            iv = max(1.0, iv * 1.5)
    else:
        iv = 1.0
    iv = compress(min(max(iv, 1.0), INTERVAL_CEILING), today, deadline)
    c["interval"] = round(iv, 2)
    c["attempts"] = int(num(c.get("attempts"), 0)) + 1
    c["score"] = round(0.7 * num(c.get("score")) + 0.3 * RETURN[result], 3)
    c["hint_streak"] = streak + 1 if result == "hint" else 0
    c["last"] = today.isoformat()
    c["next_due"] = capped(today + dt.timedelta(days=days(iv)), deadline).isoformat()
    if errors:
        old = c.get("errors")
        seen = old if isinstance(old, list) else ([old] if isinstance(old, str) and old else [])
        for e in errors:
            if e not in seen:
                seen.append(e)
        c["errors"] = seen
    if override:
        c["override"] = True
    if confidence is not None:
        c["confidence"] = confidence
    notes = []
    if errors:
        notes.append("errors: %s" % ", ".join(dict.fromkeys(errors)))
    if override:
        notes.append("override")
    if confidence is not None:
        notes.append("confidence %d" % confidence)
    log = ["%s: %s, interval %g d, next %s%s"
           % (cid, result, c["interval"], c["next_due"],
              ("  [%s]" % "; ".join(notes)) if notes else "")]
    if result == "hit":
        for p, depth in sorted(ancestors(graph, cid).items(), key=lambda x: x[1]):
            credit = 0.5 ** depth
            pc = row_of(store, p)
            if credit < 0.1 or not pc or num(pc.get("score")) < 0.5:
                continue
            piv = compress(min(INTERVAL_CEILING, num(pc.get("interval"), 1.0) * (1 + 1.5 * credit)),
                           today, deadline)
            new = capped(today + dt.timedelta(days=days(piv)), deadline)
            old = safe_d(pc.get("next_due"), today)
            if new > old:
                pc["interval"] = round(piv, 2)
                pc["next_due"] = new.isoformat()
                pc["implicit"] = round(num(pc.get("implicit")) + credit, 3)
                log.append("  credit %g -> %s: next %s" % (credit, p, pc["next_due"]))
    elif result == "miss":
        for p in graph.get(cid, {}).get("prereqs", []):
            pc = store.get(p)
            if isinstance(pc, dict) and num(pc.get("score")) < 0.7:
                pc["next_due"] = (today + dt.timedelta(days=1)).isoformat()
                log.append("  weak prereq %s pulled to tomorrow" % p)
    save(data, store, path, shape)
    print("\n".join(log))
    return 0


def rename(unit, old, new, force=False):
    """Move a state row onto a new id. The graph rename happens in concepts.md."""
    if old == new:
        print("refused: old and new ids are the same.")
        return 1
    data, store, path, shape = load(unit)
    if refuse_unusable(shape, path):
        return 2
    if old not in store:
        print("refused: no state row '%s' in %s." % (old, path))
        return 1
    if new in store:
        print("refused: '%s' already has a state row; merging two rows is a hand job." % new)
        return 1
    graph = parse_concepts(unit)
    items, qpath, qshape, qdata = load_questions(unit)
    if qshape == "corrupt":
        print("refused: %s does not parse, so its items could not follow the rename; "
              "fix it first." % qpath)
        return 1
    if not graph:
        print("warning: no parseable concepts.md here, so '%s' could not be validated." % new)
    elif new not in graph and not force:
        close = nearest(new, graph)
        print("refused: '%s' is not in concepts.md, so the rename would only make a new orphan." % new)
        if close:
            print("  closest ids: %s" % ", ".join(close))
        print("  rename the row in concepts.md, use one of those ids, or pass --force.")
        return 1
    store[new] = store.pop(old)
    save(data, store, path, shape)
    print("renamed state row %s -> %s" % (old, new))
    moved = [qid for qid, it in items.items() if q_concept(it) == old]
    if moved:
        for qid in moved:
            items[qid]["concept"] = new
        save_questions(qdata, qpath)
        print("moved %d questions.json item%s to %s" % (len(moved), "" if len(moved) == 1 else "s", new))
    return 0


def due(unit, today, limit, as_json=False):
    graph = parse_concepts(unit)
    data, store, path, shape = load(unit)
    if refuse_unusable(shape, path):
        return 2
    ids = set(graph) | set(store)
    is_due = {i for i in ids
              if safe_d(row_of(store, i).get("next_due"), today) <= today}
    rows = []
    for i in is_due:
        covers = [p for p in ancestors(graph, i) if p in is_due]
        y = graph.get(i, {}).get("yield", "low")
        rows.append((len(covers), YIELD[y], -num(row_of(store, i).get("score")), i, covers, y))
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
              "Add one with `record ID hit --deadline YYYY-MM-DD`; it persists.")
    if len(picked) < len(is_due):
        print("(%d more due, --limit to see them)" % (len(is_due) - len(picked)))
    return 0


def test(unit, kind, correct, total, label, today, conditions=None):
    if kind not in ("pre", "post"):
        print("refused: kind must be pre or post, got '%s'." % kind)
        return 1
    if total <= 0 or correct < 0 or correct > total:
        print("refused: %d/%d is not a possible score." % (correct, total))
        return 1
    data, store, path, shape = load(unit)
    if refuse_unusable(shape, path):
        return 2
    tests = data.get("tests", [])
    if not isinstance(tests, list):
        print("refused: 'tests' in %s is %s, not a list; nothing was written."
              % (path, type(tests).__name__))
        return 2
    entry = {"date": today.isoformat(), "kind": kind, "label": label,
             "correct": correct, "total": total}
    if kind == "post" and pre_for(tests + [entry], entry) is None:
        print("warning: no earlier pre-test labelled '%s' to compare this against." % (label or ""))
    if conditions:
        entry["conditions"] = conditions
    tests.append(entry)
    data["tests"] = tests
    save(data, store, path, shape)
    show(unit)
    return 0


def pre_for(tests, post):
    """The pre-test a post-test is measured against: same label, taken before it
    (an earlier date, or the same date and earlier in the file), the most recent
    such. A pre-test taken after the post never counts. None when there is none."""
    label = post.get("label") or ""
    when = safe_d(post.get("date"))
    pos = next((i for i, t in enumerate(tests) if t is post), len(tests))
    best, best_key = None, None
    for i, t in enumerate(tests):
        if not isinstance(t, dict) or t.get("kind") != "pre" or (t.get("label") or "") != label:
            continue
        td = safe_d(t.get("date"))
        if when and td:
            if td > when or (td == when and i > pos):
                continue
        elif i > pos:
            continue
        key = (td or dt.date.min, i)
        if best_key is None or key >= best_key:
            best, best_key = t, key
    return best


def show(unit, as_json=False):
    data, _, path, shape = load(unit)
    if refuse_unusable(shape, path):
        return 2
    raw = data.get("tests", [])
    if not isinstance(raw, list):
        raw = []
    tests = [t for t in raw if isinstance(t, dict)]
    if as_json:
        print(json.dumps(tests, indent=2))
        return 0
    for t in tests:
        total = num(t.get("total"))
        pct = 100 * num(t.get("correct")) / total if total else 0
        line = "%s %-4s %s/%s (%.0f%%) %s" % (t.get("date"), t.get("kind"), t.get("correct"),
                                              t.get("total"), pct, t.get("label") or "")
        if t.get("conditions"):
            line += " [%s]" % t["conditions"]
        if t.get("kind") == "post":
            pre = pre_for(tests, t)
            if pre is not None:
                ptotal = num(pre.get("total"))
                ppct = 100 * num(pre.get("correct")) / ptotal if ptotal else 0
                line += "  gain %+.0f pts" % (pct - ppct)
                pd, td = safe_d(pre.get("date")), safe_d(t.get("date"))
                if pd and td and (td - pd).days > 7:
                    line += " over %d days" % (td - pd).days
        print(line)
    return 0


# ------------------------------------------------- the fresh-question reserve

def load_questions(unit):
    """-> (items, path, shape, data). shapes: none (no file) | ok | corrupt.

    items maps an item id to {"concept": cid, "state": state, "last": day|None};
    data is the whole file, so other top-level keys survive a save.
    """
    path = os.path.join(unit, "questions.json")
    if not os.path.exists(path):
        data = {"items": {}}
        return data["items"], path, "none", data
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (ValueError, OSError):
        return {}, path, "corrupt", None
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, dict):
        return {}, path, "corrupt", None
    return items, path, "ok", data


def save_questions(data, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def q_concept(it):
    """The concept id an item tracks, or None when it is missing or not a string."""
    c = it.get("concept") if isinstance(it, dict) else None
    return c if isinstance(c, str) and c else None


def questions_add(unit, qid, cid, state, force=False):
    if state not in QUESTION_STATES:
        raise UsageError("state must be one of: %s, got '%s'"
                         % (", ".join(QUESTION_STATES), state))
    graph = parse_concepts(unit)
    items, path, shape, qdata = load_questions(unit)
    if shape == "corrupt":
        print("refused: %s does not parse; fix or remove it by hand." % path)
        return 2
    if qid in items:
        if isinstance(items[qid], dict):
            print("refused: item '%s' already exists; mark it instead of adding again." % qid)
        else:
            print("refused: item '%s' is %s, not an object; fix questions.json by hand."
                  % (qid, type(items[qid]).__name__))
        return 1
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
        print("warning: '%s' is not in concepts.md; tracked anyway (--force)." % cid)
    items[qid] = {"concept": cid, "state": state, "last": None}
    save_questions(qdata, path)
    print("added %s (%s, %s)" % (qid, cid, state))
    return 0


def questions_mark(unit, qid, state, today):
    if state not in QUESTION_STATES:
        raise UsageError("state must be one of: %s, got '%s'"
                         % (", ".join(QUESTION_STATES), state))
    items, path, shape, qdata = load_questions(unit)
    if shape == "corrupt":
        print("refused: %s does not parse; fix or remove it by hand." % path)
        return 2
    it = items.get(qid)
    if not isinstance(it, dict):
        print("refused: no item '%s' in questions.json; add it first with "
              "`questions add %s <concept>`." % (qid, qid))
        return 1
    it["state"] = state
    it["last"] = today.isoformat()
    save_questions(qdata, path)
    print("%s -> %s (last %s)" % (qid, state, today.isoformat()))
    return 0


def questions_report(unit, as_json=False):
    items, path, shape, _ = load_questions(unit)
    if shape == "corrupt":
        print("refused: %s does not parse as a JSON object with an items object." % path)
        return 2
    if shape == "none":
        print("no questions.json yet, so the fresh-question reserve is not tracked.")
        print("start it with: schedule.py <unit> questions add <id> <concept>")
        return 0
    graph = parse_concepts(unit)
    counts = {}
    for qid in sorted(items):
        it = items[qid] if isinstance(items[qid], dict) else {}
        cid = q_concept(it) or "(no concept)"
        st = it.get("state") if it.get("state") in QUESTION_STATES else "(bad state)"
        counts.setdefault(cid, {})
        counts[cid][st] = counts[cid].get(st, 0) + 1
    # drilled graph concepts with no items are under the floor too, as in check
    _, store, _, mshape = load(unit)
    if mshape not in ("corrupt", "broken", "unreadable"):
        for cid in graph:
            if cid not in counts and num(row_of(store, cid).get("attempts")) > 0:
                counts[cid] = {}
    if as_json:
        print(json.dumps({"path": path, "items": items, "by_concept": counts}, indent=2))
        return 0
    print("%d items in questions.json; reserve floor by yield (high 3, medium 2, low 1)"
          % len(items))
    for cid in sorted(counts):
        unseen = counts[cid].get("unseen", 0)
        used = sum(n for st, n in counts[cid].items() if st != "unseen")
        y = graph.get(cid, {}).get("yield", "low")
        floor = RESERVE_FLOOR[y]
        mark = "  LOW" if unseen < floor else ""
        print("  %-28s unseen %2d  used %2d  floor %d%s" % (cid, unseen, used, floor, mark))
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

    # ---- is the state file usable at all?
    if shape == "unreadable":
        add("error", "E_STATE_UNREADABLE",
            "mastery.json exists but could not be opened (permissions, or not a file)")
        return findings, graph, data, store, path, shape
    if shape == "corrupt":
        add("error", "E_STATE_CORRUPT",
            "mastery.json does not parse as a JSON object, so nothing in it could be read")
        return findings, graph, data, store, path, shape
    if shape == "broken":
        add("error", "E_STATE_BROKEN",
            "mastery.json parses, but 'concepts' is not an object of rows, so nothing in it could be read")
        return findings, graph, data, store, path, shape

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
    drilled = any(isinstance(c, dict) and num(c.get("attempts")) > 0 for c in store.values()) \
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
            if f in c:
                continue
            if f in ("last", "errors"):
                add("info", "I_FIELD_ABSENT", "%s has no '%s' yet (fine until it is graded)" % (cid, f), cid)
            else:
                add("warning", "W_FIELD_MISSING", "%s has no '%s'; --fix fills a default" % (cid, f), cid)
        for f in c:
            if f not in ALLOWED_FIELDS:
                add("warning", "W_FIELD_UNKNOWN", "%s has unknown field '%s'; --fix drops it" % (cid, f), cid)
        for _, msg, _ in type_drift(c):
            add("warning", "W_FIELD_TYPE", "%s %s" % (cid, msg), cid)
        if "score" in c:
            s = num(c.get("score"), None)
            if s is None:
                add("error", "E_SCORE_TYPE", "%s score %r is not a number" % (cid, c.get("score")), cid)
            elif not 0.0 <= s <= 1.0:
                add("error", "E_SCORE_RANGE", "%s score %s is outside 0..1; --fix clamps it" % (cid, s), cid)
        if c.get("next_due"):
            try:
                when = d(c["next_due"])
                if when < today:
                    add("info", "I_STALE_DUE", "%s was due %s" % (cid, c["next_due"]), cid)
            except ValueError:
                add("error", "E_NEXT_DUE", "%s next_due %r is not a date; --fix rebuilds it from interval"
                    % (cid, c.get("next_due")), cid)
        if "interval" in c:
            iv = num(c.get("interval"), None)
            if iv is None:
                add("error", "E_INTERVAL", "%s interval %r is not a number" % (cid, c.get("interval")), cid)
            elif iv <= 0:
                add("error", "E_INTERVAL", "%s interval must be positive" % cid, cid)

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
    raw_tests = data.get("tests", [])
    if not isinstance(raw_tests, list):
        add("warning", "W_TEST_ENTRY", "'tests' is %s, not a list" % type(raw_tests).__name__)
        raw_tests = []
    for t in raw_tests:
        if not isinstance(t, dict):
            add("warning", "W_TEST_ENTRY", "a tests entry is %s, not an object" % type(t).__name__)
            continue
        total_n = num(t.get("total"))
        if total_n <= 0:
            add("warning", "W_TEST_TOTAL", "a %s test has total %r" % (t.get("kind"), t.get("total")))
        elif num(t.get("correct")) > total_n:
            add("warning", "W_TEST_TOTAL",
                "a %s test scores %s/%s" % (t.get("kind"), t.get("correct"), t.get("total")))
    for t in raw_tests:
        if isinstance(t, dict) and t.get("kind") == "post" and pre_for(raw_tests, t) is None:
            add("info", "I_UNPAIRED_POST",
                "post-test '%s' has no earlier pre-test with that label, so no gain can be shown"
                % (t.get("label") or ""))

    # ---- fresh-question reserve (questions.json, read only when it exists)
    items, qpath, qshape, _ = load_questions(unit)
    if qshape == "corrupt":
        add("warning", "W_QUESTIONS_FILE",
            "questions.json does not parse, so the reserve ledger was ignored")
    elif qshape == "ok":
        for qid in sorted(items):
            it = items[qid]
            if not isinstance(it, dict) or it.get("state") not in QUESTION_STATES:
                add("warning", "W_QUESTIONS_ENTRY",
                    "item '%s' in questions.json has a missing or unknown state; check the file" % qid)
            elif q_concept(it) is None:
                add("warning", "W_QUESTIONS_ENTRY",
                    "item '%s' in questions.json has a missing or non-text concept; check the file" % qid)
            elif graph and it["concept"] not in graph:
                add("warning", "W_QUESTIONS_ORPHAN",
                    "item '%s' tracks concept '%s', which is not in concepts.md" % (qid, it["concept"]))
        low = []
        for cid, g in sorted(graph.items()):
            floor = RESERVE_FLOOR[g["yield"]]
            tracked = any(q_concept(it) == cid for it in items.values())
            drilled_c = num(row_of(store, cid).get("attempts")) > 0
            if not tracked and not drilled_c:
                continue
            unseen = sum(1 for it in items.values()
                         if q_concept(it) == cid and it.get("state") == "unseen")
            if unseen < floor:
                low.append("%s %d/%d" % (cid, unseen, floor))
        if low:
            add("warning", "W_RESERVE_LOW",
                "fresh-question reserve under the floor: %s%s"
                % (", ".join(low[:6]), " ..." if len(low) > 6 else ""))

    # ---- shape
    if shape in ("types", "flat"):
        add("warning", "W_LEGACY_SHAPE",
            "mastery.json uses the legacy '%s' shape; --fix rewrites it in the canonical shape" % shape)

    return findings, graph, data, store, path, shape


def _repair(data, store, path, shape, today):
    """Repair only what is reversible. Never deletes a concept row.
    Returns (fixed, cannot); cannot lists what only a human can fix."""
    fixed, cannot = [], []
    try:
        deadline = d(data["deadline"]) if data.get("deadline") else None
    except ValueError:
        deadline = None
    if shape in ("types", "flat"):
        if shape == "types":
            data["concepts"] = store
            data.pop("types", None)
        else:
            keep = legacy_metadata(data, store)
            data = {"concepts": store}
            data.update(keep)
        data.setdefault("concepts", store)
        fixed.append("migrated mastery.json to the canonical shape")
    elif shape == "empty":
        data.setdefault("concepts", store)
        fixed.append("wrote mastery.json in the canonical shape")
    for cid in list(store):
        c = store[cid]
        if not isinstance(c, dict):
            cannot.append("row '%s' is %s, not an object; edit or remove it by hand"
                          % (cid, type(c).__name__))
            continue
        for f, msg, ok in type_drift(c):
            if not ok:
                cannot.append("%s %s; edit it by hand" % (cid, msg))
            elif f == "errors":
                c["errors"] = [c["errors"]]
                fixed.append("%s.errors wrapped in a list" % cid)
            else:
                v = num(c[f])
                c[f] = int(v) if f == "attempts" and v == int(v) else v
                fixed.append("%s.%s converted to %r" % (cid, f, c[f]))
        for f, v in (("score", 0.0), ("attempts", 0), ("interval", 1.0),
                     ("last", None), ("errors", [])):
            if f not in c:
                c[f] = v
                fixed.append("%s.%s = %r" % (cid, f, v))
        if not c.get("next_due"):
            step = days(num(c.get("interval"), 1.0))
            c["next_due"] = capped(today + dt.timedelta(days=step), deadline).isoformat()
            fixed.append("%s.next_due = %s (from interval)" % (cid, c["next_due"]))
        s = num(c.get("score"), None)
        if s is None:
            c["score"] = 0.0
            fixed.append("%s.score reset to 0.0" % cid)
        elif not 0.0 <= s <= 1.0:
            c["score"] = min(1.0, max(0.0, s))
            fixed.append("%s.score clamped to %s" % (cid, c["score"]))
        iv = num(c.get("interval"), None)
        if iv is None or iv <= 0:
            c["interval"] = 1.0
            fixed.append("%s.interval reset to 1.0" % cid)
        if c.get("next_due"):
            try:
                d(c["next_due"])
            except ValueError:
                step = days(num(c.get("interval"), 1.0))
                c["next_due"] = capped(today + dt.timedelta(days=step), deadline).isoformat()
                fixed.append("%s.next_due rebuilt as %s" % (cid, c["next_due"]))
        for f in [f for f in c if f not in ALLOWED_FIELDS]:
            c.pop(f, None)
            fixed.append("%s dropped unknown field '%s'" % (cid, f))
    if data.get("deadline"):
        try:
            d(data["deadline"])
        except ValueError:
            data.pop("deadline", None)
            fixed.append("dropped malformed deadline")
    save(data, store, path, shape)
    return fixed, cannot


def check(unit, today, fix=False, as_json=False):
    findings, graph, data, store, path, shape = analyze(unit, today)
    fixed, cannot = [], []
    if fix and os.path.exists(path):
        if shape == "unreadable":
            cannot.append("mastery.json could not be opened; fix its permissions by hand "
                          "(it is not moved aside, it may be good state)")
        elif shape in ("corrupt", "broken"):
            backup = quarantine(path)
            fixed.append("moved unreadable mastery.json to %s (bytes preserved)"
                         % os.path.basename(backup))
        else:
            fixed, cannot = _repair(data, store, path, shape, today)
        findings, graph, data, store, path, shape = analyze(unit, today)

    errors = [f for f in findings if f["severity"] == "error"]
    warns = [f for f in findings if f["severity"] == "warning"]
    code = 2 if errors else (1 if warns else 0)

    if as_json:
        print(json.dumps({"unit": unit, "shape": shape, "graph_concepts": len(graph),
                          "state_concepts": len(store), "deadline": data.get("deadline"),
                          "errors": len(errors), "warnings": len(warns),
                          "findings": findings, "fixed": fixed, "cannot_fix": cannot,
                          "exit": code}, indent=2))
        return code

    print("%s: %d concepts in the graph, %d with state, shape %s, exit %d"
          % (unit, len(graph), len(store), shape, code))
    for f in findings:
        print("  %-7s %-18s %s" % (f["severity"], f["code"], f["message"]))
    for line in fixed:
        print("  fixed   %s" % line)
    for line in cannot:
        print("  cannot  %s" % line)
    if not findings and not fixed and not cannot:
        print("  clean")
    return code


def main():
    try:
        return run(sys.argv[1:])
    except UsageError as e:
        print("schedule.py: %s" % e)
        return 2
    except OSError as e:
        print("schedule.py: could not read or write %s (%s); nothing else was changed."
              % (e.filename or "a file", e.strerror or e.__class__.__name__))
        return 2


def run(a):
    if len(a) < 2:
        print(__doc__.strip())
        return 2
    unit, cmd = os.path.expanduser(a[0]), a[1]
    if not os.path.isdir(unit):
        raise UsageError("%s is not a folder. Point it at a study unit." % unit)
    raw_date = arg(a, "--date", None)
    today = parse_day(raw_date) if raw_date else dt.date.today()
    if cmd == "record":
        flags_ok(a, ("--date", "--deadline", "--force", "--error", "--confidence", "--override"))
        if len(a) < 4:
            raise UsageError("usage: schedule.py UNIT record ID hit|hint|miss")
        if a[3] not in RETURN:
            raise UsageError("result must be hit, hint or miss, got '%s'" % a[3])
        dl = arg(a, "--deadline", None)
        dl = parse_day(dl) if dl else None
        conf = arg(a, "--confidence", None)
        if conf is not None:
            try:
                conf = int(conf)
            except ValueError:
                raise UsageError("--confidence takes a whole number 1 to 5, got '%s'" % conf)
            if not 1 <= conf <= 5:
                raise UsageError("--confidence takes 1 to 5, got %d" % conf)
        return record(unit, a[2], a[3], today, dl, "--force" in a,
                      errors=arg_all(a, "--error"), confidence=conf,
                      override="--override" in a)
    if cmd == "due":
        flags_ok(a, ("--date", "--limit", "--json"))
        raw = arg(a, "--limit", None)
        try:
            limit = 10 if raw is None else int(raw)
        except ValueError:
            raise UsageError("--limit takes a whole number, got '%s'" % raw)
        if limit < 1:
            raise UsageError("--limit takes 1 or more, got %d" % limit)
        return due(unit, today, limit, "--json" in a)
    if cmd == "test":
        flags_ok(a, ("--date", "--label", "--conditions"))
        if len(a) < 5:
            raise UsageError("usage: schedule.py UNIT test pre|post CORRECT TOTAL [--label ..]")
        try:
            correct, total = int(a[3]), int(a[4])
        except ValueError:
            raise UsageError("CORRECT and TOTAL must be whole numbers, got '%s' and '%s'"
                             % (a[3], a[4]))
        cond = arg(a, "--conditions", None)
        if cond is not None and cond not in CONDITIONS:
            raise UsageError("--conditions takes one of: %s, got '%s'"
                             % (", ".join(CONDITIONS), cond))
        return test(unit, a[2], correct, total, arg(a, "--label", ""), today, cond)
    if cmd == "tests":
        flags_ok(a, ("--json",))
        return show(unit, "--json" in a)
    if cmd == "check":
        flags_ok(a, ("--date", "--json", "--fix"))
        return check(unit, today, "--fix" in a, "--json" in a)
    if cmd == "rename":
        flags_ok(a, ("--force",))
        if len(a) < 4:
            raise UsageError("usage: schedule.py UNIT rename OLD NEW")
        return rename(unit, a[2], a[3], "--force" in a)
    if cmd == "questions":
        if len(a) > 2 and a[2] == "add":
            flags_ok(a, ("--date", "--state", "--force"))
            if len(a) < 5:
                raise UsageError("usage: schedule.py UNIT questions add ID CONCEPT [--state S]")
            return questions_add(unit, a[3], a[4], arg(a, "--state", "unseen"), "--force" in a)
        if len(a) > 2 and a[2] == "mark":
            flags_ok(a, ("--date",))
            if len(a) < 5:
                raise UsageError("usage: schedule.py UNIT questions mark ID STATE")
            return questions_mark(unit, a[3], a[4], today)
        flags_ok(a, ("--date", "--json"))
        if len(a) > 2 and not a[2].startswith("--"):
            raise UsageError("questions takes 'add' or 'mark', or no verb to report; got '%s'"
                             % a[2])
        return questions_report(unit, "--json" in a)
    raise UsageError("unknown command '%s'; run schedule.py with no arguments for usage" % cmd)


if __name__ == "__main__":
    sys.exit(main())
