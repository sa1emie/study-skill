#!/usr/bin/env python3
"""Build study.md, the single-file version of the skill, from study/.

The Claude Code skill folder (study/) is the source of truth. Tools that read
one file (Cursor rules, AGENTS.md, plain chat uploads) get study.md: SKILL.md
without its frontmatter, followed by every reference file.
Run after editing anything in study/:  python3 tools/build_portable.py
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "study")
ORDER = ["model", "one-shot", "register", "visual", "design", "routes"]

skill = open(os.path.join(SK, "SKILL.md"), encoding="utf-8").read()
body = re.sub(r"\A---\n.*?\n---\n", "", skill, flags=re.S).strip()
head = """> **About this file.** The complete study skill in one file, generated from the
> `study/` folder of https://github.com/sa1emie/study-skill (do not edit by hand).
> It is plain instructions for any AI agent that can read files. If you have no
> file system (a plain chat), follow "Degraded mode". `SKILL_DIR` means the
> `study/` folder of that repo: the scripts and HTML assets live there, so clone
> it if you want videos, the scheduler, or the page template.
"""
parts = [body.replace("# study\n", "# study\n\n" + head, 1)]
for name in ORDER:
    text = open(os.path.join(SK, "references", name + ".md"), encoding="utf-8").read().strip()
    text = re.sub(r"^# ", "# Reference: ", text, count=1)
    parts.append(text)
open(os.path.join(ROOT, "study.md"), "w", encoding="utf-8").write("\n\n---\n\n".join(parts) + "\n")
print("study.md:", sum(p.count("\n") + 1 for p in parts), "lines from SKILL.md +", len(ORDER), "references")
