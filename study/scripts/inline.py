#!/usr/bin/env python3
"""Make a study page self-contained: inline study.css, study.js and local images.

usage: inline.py PAGE.html OUT.html [--images]
PAGE.html links `study.css` and `study.js` (as in assets/template.html); they are
read from SKILL_DIR/assets. With --images, local <img src> files become data URIs
so the single file can be emailed or moved. Videos stay as links (too large).
"""
import base64, mimetypes, os, re, sys

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
a = sys.argv[1:]
src, out = a[0], a[1]
html = open(src, encoding="utf-8").read()
css = open(os.path.join(ASSETS, "study.css"), encoding="utf-8").read()
js = open(os.path.join(ASSETS, "study.js"), encoding="utf-8").read()
html, n_css = re.subn(r'<link[^>]+href="study\.css"[^>]*>', lambda m: "<style>\n" + css + "</style>", html)
html, n_js = re.subn(r'<script[^>]+src="study\.js"[^>]*></script>', lambda m: "<script>\n" + js + "</script>", html)
n_img = 0
if "--images" in a:
    base = os.path.dirname(os.path.abspath(src))
    def data(m):
        global n_img
        p = os.path.join(base, m.group(2))
        if not os.path.exists(p):
            return m.group(0)
        n_img += 1
        mt = mimetypes.guess_type(p)[0] or "application/octet-stream"
        return f'{m.group(1)}data:{mt};base64,{base64.b64encode(open(p, "rb").read()).decode()}"'
    html = re.sub(r'(<img[^>]+src=")(?!data:|https?:)([^"]+)"', data, html)
open(out, "w", encoding="utf-8").write(html)
print(f"{out}: css {'inlined' if n_css else 'NOT FOUND'}, js {'inlined' if n_js else 'NOT FOUND'}, images {n_img}")
