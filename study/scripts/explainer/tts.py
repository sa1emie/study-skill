#!/usr/bin/env python3
"""Narrate beats with local Kokoro TTS.

usage: tts.py beats.json OUTDIR [--voice am_michael] [--speed 1.0]
beats.json: {"title": "...", "beats": [{"id": "intro", "say": "..."}, ...]}
Writes OUTDIR/beat_XX.wav, OUTDIR/narration.wav and OUTDIR/timing.json
(seconds per beat, plus 0.35 s pause after each beat).
"""
import json, os, sys, warnings
warnings.filterwarnings("ignore")
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

M = os.path.join(os.path.expanduser(os.environ.get("EXPLAINER_HOME", "~/.local/share/explainer")), "models")
PAUSE = 0.35

def main():
    a = sys.argv[1:]
    voice = a[a.index("--voice") + 1] if "--voice" in a else "am_michael"
    speed = float(a[a.index("--speed") + 1]) if "--speed" in a else 1.0
    spec, out = json.load(open(a[0])), a[1]
    os.makedirs(out, exist_ok=True)
    k = Kokoro(f"{M}/kokoro-v1.0.onnx", f"{M}/voices-v1.0.bin")
    allaudio, timing, sr = [], [], 24000
    for i, b in enumerate(spec["beats"]):
        samples, sr = k.create(b["say"], voice=voice, speed=speed, lang="en-us")
        samples = np.concatenate([samples, np.zeros(int(PAUSE * sr), dtype=samples.dtype)])
        sf.write(f"{out}/beat_{i:02d}.wav", samples, sr)
        allaudio.append(samples)
        timing.append({"id": b.get("id", str(i)), "seconds": round(len(samples) / sr, 3)})
        print(f"beat {i:02d} {timing[-1]['seconds']:6.2f}s  {b['say'][:60]}")
    sf.write(f"{out}/narration.wav", np.concatenate(allaudio), sr)
    json.dump(timing, open(f"{out}/timing.json", "w"), indent=1)
    print(f"total {sum(t['seconds'] for t in timing):.1f}s -> {out}/narration.wav")

if __name__ == "__main__":
    main()
