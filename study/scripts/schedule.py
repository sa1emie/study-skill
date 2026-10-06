#!/usr/bin/env python3
"""Spacing scheduler with prerequisite credit (FIRe-lite), plus pre/post tests.

Reads <unit>/concepts.md (markdown tables with id, prereqs, yield columns) and
updates <unit>/mastery.json in place, keeping whatever shape that file already has.

  schedule.py UNIT record ID hit|hint|miss [--date YYYY-MM-DD] [--deadline YYYY-MM-DD]
  schedule.py UNIT due [--date D] [--limit 10]
  schedule.py UNIT test pre|post CORRECT TOTAL [--label "Ch 5 Vision"] [--date D]
  schedule.py UNIT tests

Rules (the skill's Spacing section):
  hit  (first try)  interval x 2.5   hint  interval x 1.5   miss  interval = 1 day
  A hit passes implicit credit down the prerequisite graph: direct prereqs get
  0.5 of a hit, theirs 0.25, and so on (stops under 0.1). Credit only ever pushes
  next_due later, and skips prereqs never learned (score < 0.5).
  A miss pulls weak direct prereqs (score < 0.7) to tomorrow: the miss may be a
  prerequisite gap.
  next_due never lands past the deadline (--deadline, or deadline in mastery.json).
  `due` ranks due concepts by knockout value: reviewing an advanced concept also
  covers its due prerequisites, so the one covering the most goes first, then yield.
"""
import datetime as dt, json, os, re, sys

YIELD = {"high": 3, "medium": 2, "low": 1}


def parse_concepts(unit):
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
        cid = re.sub(r"[*`]", "", row.get("id", "")).strip()
        if not cid:
            continue
        pre = re.sub(r"[*`]", "", row.get("prereqs", ""))
        prereqs = [p.strip() for p in re.split(r"[,;]", pre) if re.search(r"[A-Za-z0-9]", p) and p.strip().lower() != "none"]
        y = re.sub(r"[^a-z]", "", row.get("yield", "").lower())
        graph[cid] = {"prereqs": prereqs, "yield": y if y in YIELD else "low", "name": row.get("name", "")}
    return graph


def load(unit):
    path = os.path.join(unit, "mastery.json")
    data = json.load(open(path)) if os.path.exists(path) else {"concepts": {}}
    for key in ("concepts", "types"):
        if isinstance(data.get(key), dict):
            return data, data[key], path
    store = {k: v for k, v in data.items() if isinstance(v, dict) and ("score" in v or "attempts" in v)}
    return data, store, path


def save(data, store, path):
    if "concepts" not in data and "types" not in data:
        data.update(store)
    json.dump(data, open(path + ".tmp", "w"), indent=2, ensure_ascii=False)
    os.replace(path + ".tmp", path)


def d(s):
    return dt.date.fromisoformat(s[:10])


def capped(day, deadline):
    return min(day, deadline) if deadline else day


def arg(a, name, default=None):
    return a[a.index(name) + 1] if name in a else default


def ancestors(graph, cid):
    out, stack = {}, [(p, 1) for p in graph.get(cid, {}).get("prereqs", [])]
    while stack:
        p, depth = stack.pop()
        if p in out and out[p] <= depth:
            continue
        out[p] = depth
        stack += [(q, depth + 1) for q in graph.get(p, {}).get("prereqs", [])]
    return out


def record(unit, cid, result, today, deadline):
    graph = parse_concepts(unit)
    data, store, path = load(unit)
    deadline = deadline or (d(data["deadline"]) if data.get("deadline") else None)
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
    c["score"] = round(0.7 * float(c.get("score") or 0) + 0.3 * {"hit": 1, "hint": 0.5, "miss": 0}[result], 3)
    c["last"] = today.isoformat()
    c["next_due"] = capped(today + dt.timedelta(days=round(iv)), deadline).isoformat()
    log = [f"{cid}: {result}, interval {iv:g} d, next {c['next_due']}"]
    if result == "hit":
        for p, depth in sorted(ancestors(graph, cid).items(), key=lambda x: x[1]):
            credit = 0.5 ** depth
            pc = store.get(p)
            if credit < 0.1 or pc is None or float(pc.get("score") or 0) < 0.5:
                continue  # implicit credit only reinforces something already learned
            piv = float(pc.get("interval", 1)) * (1 + 1.5 * credit)
            new = capped(today + dt.timedelta(days=round(piv)), deadline)
            old = d(pc["next_due"]) if pc.get("next_due") else today
            if new > old:
                pc["interval"] = round(piv, 2)
                pc["next_due"] = new.isoformat()
                pc["implicit"] = pc.get("implicit", 0) + credit
                log.append(f"  credit {credit:g} -> {p}: next {pc['next_due']}")
    elif result == "miss":
        for p in graph.get(cid, {}).get("prereqs", []):
            pc = store.get(p)
            if pc is not None and float(pc.get("score") or 0) < 0.7:
                pc["next_due"] = (today + dt.timedelta(days=1)).isoformat()
                log.append(f"  weak prereq {p} pulled to tomorrow")
    save(data, store, path)
    print("\n".join(log))


def due(unit, today, limit):
    graph = parse_concepts(unit)
    data, store, _ = load(unit)
    ids = set(graph) | set(store)
    is_due = {i for i in ids if (store.get(i, {}).get("next_due") is None) or d(store[i]["next_due"]) <= today}
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
    print(f"{len(is_due)} due on {today}; review order (covered prereqs skipped):")
    for n, _, s, i, covers, y in picked:
        extra = f", also covers {', '.join(covers)}" if covers else ""
        print(f"  {i} [{y}, score {-s:.2f}]{extra}")


def test(unit, kind, correct, total, label, today):
    data, store, path = load(unit)
    tests = data.setdefault("tests", [])
    tests.append({"date": today.isoformat(), "kind": kind, "label": label, "correct": correct, "total": total})
    save(data, store, path)
    show(unit)


def show(unit):
    data, _, _ = load(unit)
    tests = data.get("tests", [])
    pre = None
    for t in tests:
        pct = 100 * t["correct"] / t["total"]
        line = f"{t['date']} {t['kind']:4} {t['correct']}/{t['total']} ({pct:.0f}%) {t.get('label') or ''}"
        if t["kind"] == "pre":
            pre = (pct, t.get("label"))
        elif pre and pre[1] == t.get("label"):
            line += f"  gain {pct - pre[0]:+.0f} pts"
        print(line)


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    unit, cmd = os.path.expanduser(a[0]), a[1]
    today = d(arg(a, "--date", dt.date.today().isoformat()))
    dl = arg(a, "--deadline")
    if cmd == "record":
        record(unit, a[2], a[3], today, d(dl) if dl else None)
    elif cmd == "due":
        due(unit, today, int(arg(a, "--limit", 10)))
    elif cmd == "test":
        test(unit, a[2], int(a[3]), int(a[4]), arg(a, "--label", ""), today)
    elif cmd == "tests":
        show(unit)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
