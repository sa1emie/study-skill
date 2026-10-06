#!/usr/bin/env python3
"""Build a narrated explainer: TTS -> Manim -> mux -> contact sheet.

usage: make.py SCENE.py SceneClass BEATS.json OUTDIR [--draft] [--voice am_michael]
Run with the explainer venv python (setup.sh prints the path).
Install location: $EXPLAINER_HOME, default ~/.local/share/explainer.
Outputs OUTDIR/<SceneClass>.mp4, OUTDIR/<SceneClass>.html (video + retrieval
questions from beats.json "questions"; required, 3 or more), OUTDIR/frames.png (one frame per beat, at the
beat midpoint) and OUTDIR/warnings.json (timing overruns, off-frame objects).
LOOK at frames.png before calling the video done.
"""
import glob, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOME_DIR = os.path.expanduser(os.environ.get("EXPLAINER_HOME", "~/.local/share/explainer"))
PY = os.path.join(HOME_DIR, "venv", "bin", "python")
if not os.path.exists(PY):
    sys.exit(f"No explainer venv at {PY}. Run {HERE}/setup.sh first.")


def run(cmd, **kw):
    print("+", " ".join(cmd)[:160])
    subprocess.run(cmd, check=True, **kw)


def main():
    a = sys.argv[1:]
    scene, cls, beats, out = [os.path.abspath(x) if i != 1 else x for i, x in enumerate(a[:4])]
    draft = "--draft" in a
    voice = a[a.index("--voice") + 1] if "--voice" in a else "am_michael"
    os.makedirs(out, exist_ok=True)
    if len(json.load(open(beats)).get("questions") or []) < 3:
        sys.exit("make.py: add 3+ questions to beats.json first (every video ends in questions)")
    audio = f"{out}/audio"
    run([PY, f"{HERE}/tts.py", beats, audio, "--voice", voice])
    env = dict(os.environ, EXPLAINER_TIMING=f"{audio}/timing.json", EXPLAINER_WARN=f"{out}/warnings.json",
               PYTHONPATH=HERE + os.pathsep + os.environ.get("PYTHONPATH", ""))
    media = f"{out}/media"
    run([PY, "-m", "manim", "render", "-ql" if draft else "-qh", "--media_dir", media,
         "--disable_caching", "-o", cls, scene, cls], env=env, cwd=out)
    vid = max((p for p in glob.glob(f"{media}/videos/**/{cls}.mp4", recursive=True) if "partial" not in p), key=os.path.getmtime)
    final = f"{out}/{cls}.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid, "-i", f"{audio}/narration.wav", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "160k", "-shortest", final])
    timing = json.load(open(f"{audio}/timing.json"))
    t, mids = 0, []
    for b in timing:
        mids.append(t + b["seconds"] * 0.8)
        t += b["seconds"]
    frames = []
    for i, m in enumerate(mids):
        f = f"{out}/frame_{i:02d}.png"
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{m:.2f}", "-i", final, "-frames:v", "1", "-vf", "scale=640:-2", f])
        frames.append(f)
    cols, rows = 3, -(-len(frames) // 3)
    run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "1", "-i", f"{out}/frame_%02d.png",
         "-vf", f"pad=iw+8:ih+8:4:4:black,tile={cols}x{rows}", "-frames:v", "1", f"{out}/frames.png"])
    for f in frames:
        os.remove(f)
    warns = json.load(open(f"{out}/warnings.json")) if os.path.exists(f"{out}/warnings.json") else []
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", final],
                         capture_output=True, text=True).stdout.strip()
    print(f"\nvideo {final} ({float(dur):.1f}s), narration {t:.1f}s, warnings {len(warns)}")
    for w in warns:
        print("  WARN", w)
    print(f"contact sheet: {out}/frames.png  <- look at it")
    run([PY, f"{HERE}/page.py", beats, final, f"{out}/{cls}.html"])


if __name__ == "__main__":
    main()
