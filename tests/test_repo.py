"""Repo hygiene: the portable build stays in sync, refs are wired, no em dashes."""
import os
import re
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PY, REPO, SKILL

TEXT_EXT = (".md", ".py", ".js", ".css", ".html", ".json", ".yml", ".mdc", ".sh", ".txt")


def walk_text(root, skip=(".git", "node_modules", "__pycache__")):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.endswith(TEXT_EXT):
                yield os.path.join(base, f)


class Portable(unittest.TestCase):
    def test_build_is_deterministic_and_current(self):
        path = os.path.join(REPO, "study.md")
        with open(path, encoding="utf-8") as f:
            before = f.read()
        p = subprocess.run([PY, os.path.join(REPO, "tools", "build_portable.py")],
                           capture_output=True, text=True, cwd=REPO)
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(path, encoding="utf-8") as f:
            after = f.read()
        self.assertEqual(before, after,
                         "study.md is stale. Run: python3 tools/build_portable.py")

    def test_every_reference_is_in_the_order(self):
        with open(os.path.join(REPO, "tools", "build_portable.py"), encoding="utf-8") as f:
            src = f.read()
        order = re.search(r"ORDER\s*=\s*\[(.*?)\]", src, re.S).group(1)
        wired = set(re.findall(r'"([\w-]+)"', order))
        on_disk = {f[:-3] for f in os.listdir(os.path.join(SKILL, "references")) if f.endswith(".md")}
        self.assertEqual(wired, on_disk,
                         "ORDER and study/references/ disagree: %s" % (on_disk ^ wired))

    def test_skill_lists_every_reference(self):
        with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as f:
            skill = f.read()
        for f in os.listdir(os.path.join(SKILL, "references")):
            self.assertIn("references/" + f, skill,
                          "%s exists but SKILL.md never points at it" % f)

    def test_script_paths_in_docs_exist(self):
        text = open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8").read()
        for ref in os.listdir(os.path.join(SKILL, "references")):
            with open(os.path.join(SKILL, "references", ref), encoding="utf-8") as f:
                text += f.read()
        for rel in set(re.findall(r"scripts/[\w./-]+?\.(?:py|js|sh|html)", text)):
            self.assertTrue(os.path.exists(os.path.join(SKILL, rel)),
                            "docs mention %s but it does not exist" % rel)

    def test_frontmatter(self):
        with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as f:
            head = f.read(4000)
        self.assertTrue(head.startswith("---\nname: study\n"), head[:40])
        self.assertIn("description:", head)
        description = head.split("description:", 1)[1]
        self.assertGreater(len(description), 200, "description is the trigger surface; keep it rich")


class HouseStyle(unittest.TestCase):
    def test_no_em_dashes_in_text(self):
        offenders = []
        for path in walk_text(REPO):
            with open(path, encoding="utf-8", errors="ignore") as f:
                if u"\u2014" in f.read():
                    offenders.append(os.path.relpath(path, REPO))
        self.assertEqual(offenders, [], "em dashes found: %s" % offenders)


class ExampleUnit(unittest.TestCase):
    def test_example_check_is_clean(self):
        p = subprocess.run([PY, os.path.join(SKILL, "scripts", "schedule.py"),
                            os.path.join(REPO, "examples", "example-unit"), "check",
                            "--date", "2026-10-15"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_example_due_json(self):
        p = subprocess.run([PY, os.path.join(SKILL, "scripts", "schedule.py"),
                            os.path.join(REPO, "examples", "example-unit"), "due",
                            "--date", "2026-10-15", "--json"],
                           capture_output=True, text=True)
        import json
        data = json.loads(p.stdout)
        self.assertGreater(data["due"], 0)
        self.assertEqual(data["deadline"], "2026-10-17")


if __name__ == "__main__":
    unittest.main()
