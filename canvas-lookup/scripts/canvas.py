#!/usr/bin/env python3
"""Read-only Canvas LMS lookups. Stdlib only, runs on Python 3.9+.

Config: CANVAS_API_URL (your school's Canvas, e.g. https://school.instructure.com)
and CANVAS_API_TOKEN, from the environment or from an env file at $CANVAS_ENV_FILE
(default ~/.config/canvas-lookup/.env). The token is never printed. Every call is a GET.

  canvas.py whoami
  canvas.py courses
  canvas.py planner 2026-09-28 2026-10-04        # everything due or scheduled in the window
  canvas.py announcements COURSE_ID [DAYS=30]
  canvas.py groups COURSE_ID                     # assignment groups, weights, points: "is it graded?"
  canvas.py find TEXT                            # search active courses' assignments, modules, announcements, syllabus
  canvas.py syllabus COURSE_ID                   # syllabus body text + linked file URLs
"""
import datetime, html, json, os, re, sys, urllib.error, urllib.parse, urllib.request

ENV = os.path.expanduser(os.environ.get("CANVAS_ENV_FILE") or "~/.config/canvas-lookup/.env")
TOK = BASE = None

def cfg():
    tok, url = os.environ.get("CANVAS_API_TOKEN"), os.environ.get("CANVAS_API_URL")
    if (not tok or not url) and os.path.isfile(ENV):
        with open(ENV) as f:
            for line in f:
                k, _, v = line.strip().partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k == "CANVAS_API_TOKEN" and not tok: tok = v
                if k == "CANVAS_API_URL" and not url: url = v
    if not url: sys.exit("No CANVAS_API_URL (env or %s), e.g. https://school.instructure.com" % ENV)
    if not tok: sys.exit("No CANVAS_API_TOKEN (env or %s). Never paste it in chat." % ENV)
    url = url.rstrip("/")
    return tok, url if url.endswith("/api/v1") else url + "/api/v1"

def get(path, **params):
    out, url = [], BASE + path + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    while url:
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOK})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
            m = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("Link", ""))
        if not isinstance(data, list): return data
        out += data
        url = m.group(1) if m else None
    return out

def text(h): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h or ""))).strip()

def local(ts):
    if not ts: return "-"
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%a %m-%d %H:%M")

def courses(): return get("/courses", enrollment_state="active", per_page=100)

USAGE = {"planner": 3, "announcements": 2, "groups": 2, "find": 2, "syllabus": 2}

def main(a):
    global TOK, BASE
    cmd = a[0] if a else "help"
    if cmd not in ("whoami", "courses") and (cmd not in USAGE or len(a) < USAGE[cmd]):
        print(__doc__); return
    TOK, BASE = cfg()
    if cmd == "whoami":
        d = get("/users/self"); print(d.get("name"), "| id", d.get("id"))
    elif cmd == "courses":
        for c in courses(): print(c.get("id"), "|", c.get("course_code"), "|", c.get("name"))
    elif cmd == "planner":
        s, e = a[1], a[2]
        for it in get("/planner/items", start_date=s + "T00:00:00", end_date=e + "T23:59:59", per_page=100):
            p = it.get("plannable") or {}
            print(local(it.get("plannable_date")), "|", it.get("plannable_type"), "|",
                  (it.get("context_name") or "")[:28], "|", p.get("title") or p.get("name"))
    elif cmd == "announcements":
        days = int(a[2]) if len(a) > 2 else 30
        start = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        # Canvas caps end_date at start_date + 14 days when it is left out, so always pass it.
        for x in get("/announcements", **{"context_codes[]": "course_" + a[1], "start_date": start,
                                            "end_date": datetime.date.today().isoformat(), "per_page": 50}):
            print("*", local(x.get("posted_at")), "|", x.get("title")); print("  ", text(x.get("message"))[:800])
    elif cmd == "groups":
        c = get("/courses/" + a[1])
        print("weighted:", c.get("apply_assignment_group_weights"))
        for g in get("/courses/%s/assignment_groups" % a[1], **{"include[]": "assignments", "per_page": 50}):
            print("GROUP", g.get("name"), "| weight", g.get("group_weight"))
            for x in g.get("assignments") or []:
                print("   -", x.get("name"), "| pts", x.get("points_possible"), "| due", local(x.get("due_at")))
    elif cmd == "find":
        q = " ".join(a[1:]).lower(); today = datetime.date.today()
        since = (today - datetime.timedelta(days=120)).isoformat()
        for c in courses():
            cid, code = str(c["id"]), c.get("course_code")
            hits = []
            for x in get("/courses/%s/assignments" % cid, per_page=100):
                if q in (x.get("name") or "").lower(): hits.append("assignment: %s (due %s)" % (x["name"], local(x.get("due_at"))))
            try:
                for m in get("/courses/%s/modules" % cid, **{"include[]": "items", "per_page": 100}):
                    for i in m.get("items") or []:
                        if q in (i.get("title") or "").lower(): hits.append("module item: %s / %s" % (m.get("name"), i.get("title")))
            except urllib.error.HTTPError: pass  # some courses hide modules from students
            for x in get("/announcements", **{"context_codes[]": "course_" + cid, "start_date": since,
                                                "end_date": today.isoformat(), "per_page": 50}):
                if q in (x.get("title") or "").lower() or q in text(x.get("message")).lower():
                    hits.append("announcement %s: %s" % (local(x.get("posted_at")), x.get("title")))
            syl = text(get("/courses/" + cid, **{"include[]": "syllabus_body"}).get("syllabus_body"))
            if q in syl.lower(): hits.append("syllabus body mentions it")
            if hits: print("==", cid, code); [print("  ", h) for h in hits]
    elif cmd == "syllabus":
        b = get("/courses/" + a[1], **{"include[]": "syllabus_body"}).get("syllabus_body") or ""
        print(text(b)[:4000]); print("--- links ---")
        for u in re.findall(r'href="([^"]+)"', b): print(u)

if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except urllib.error.HTTPError as e:
        if e.code == 401:
            sys.exit("401 Unauthorized: the Canvas token is expired or revoked. Make a new one "
                     "(Canvas > Account > Settings > New Access Token) and put it in " + ENV + ". Do not ask for it in chat.")
        sys.exit("Canvas HTTP %s on %s" % (e.code, e.url.split("?")[0]))
    except urllib.error.URLError as e:
        sys.exit("Could not reach Canvas: %s" % e.reason)
