"""canvas-lookup: offline checks only. Nothing here talks to a real Canvas."""
import os
import subprocess
import tempfile
import unittest

from common import REPO, PY

CANVAS = os.path.join(REPO, "canvas-lookup", "scripts", "canvas.py")


def run(*args, env_file=None, **env):
    e = {k: v for k, v in os.environ.items() if not k.startswith("CANVAS_")}
    e["CANVAS_ENV_FILE"] = env_file or os.path.join(tempfile.gettempdir(), "no-such-canvas.env")
    e.update(env)
    return subprocess.run([PY, CANVAS] + list(args), capture_output=True, text=True, env=e, timeout=30)


class CanvasLookup(unittest.TestCase):
    def test_help_needs_no_config(self):
        for args in ((), ("help",), ("planner", "2026-01-01")):
            r = run(*args)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("canvas.py whoami", r.stdout)

    def test_missing_url_and_token_fail_cleanly(self):
        r = run("whoami")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("CANVAS_API_URL", r.stderr)
        r = run("whoami", CANVAS_API_URL="http://127.0.0.1:9")
        self.assertIn("CANVAS_API_TOKEN", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_env_file_is_read_and_token_never_printed(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, ".env")
            with open(path, "w") as f:
                f.write('CANVAS_API_URL="http://127.0.0.1:9"\nCANVAS_API_TOKEN=s3cret-token\n')
            r = run("whoami", env_file=path)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Could not reach Canvas", r.stderr)
        self.assertNotIn("s3cret-token", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_skill_frontmatter(self):
        with open(os.path.join(REPO, "canvas-lookup", "SKILL.md"), encoding="utf-8") as f:
            head = f.read().split("---")[1]
        self.assertIn("name: canvas-lookup", head)
        self.assertIn("description:", head)


if __name__ == "__main__":
    unittest.main()
