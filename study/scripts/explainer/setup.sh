#!/usr/bin/env bash
# One-time setup for narrated explainer videos: Manim Community + Kokoro TTS.
# Free, local, no API key. About 1.2 GB on disk (venv ~850 MB, models ~350 MB).
# Usage: bash setup.sh            (installs to ~/.local/share/explainer)
#        EXPLAINER_HOME=/path bash setup.sh
set -euo pipefail
HOME_DIR="${EXPLAINER_HOME:-$HOME/.local/share/explainer}"
mkdir -p "$HOME_DIR/models"

# System libraries Manim needs (cairo, pango) and espeak-ng for TTS phonemes.
if command -v brew >/dev/null; then
  brew install cairo pango pkg-config espeak-ng ffmpeg
elif command -v apt-get >/dev/null; then
  echo "Debian/Ubuntu: run this first if anything below fails:"
  echo "  sudo apt-get install -y libcairo2-dev libpango1.0-dev pkg-config espeak-ng ffmpeg"
fi

if command -v uv >/dev/null; then
  uv venv --python 3.12 "$HOME_DIR/venv"
  VIRTUAL_ENV="$HOME_DIR/venv" uv pip install manim kokoro-onnx soundfile
else
  python3 -m venv "$HOME_DIR/venv"
  "$HOME_DIR/venv/bin/pip" install --upgrade pip manim kokoro-onnx soundfile
fi

R=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -f "$HOME_DIR/models/kokoro-v1.0.onnx" ] || curl -L -o "$HOME_DIR/models/kokoro-v1.0.onnx" "$R/kokoro-v1.0.onnx"
[ -f "$HOME_DIR/models/voices-v1.0.bin" ]  || curl -L -o "$HOME_DIR/models/voices-v1.0.bin"  "$R/voices-v1.0.bin"

"$HOME_DIR/venv/bin/python" -c "import manim, kokoro_onnx; print('manim', manim.__version__, 'ok')"
echo "Explainer python: $HOME_DIR/venv/bin/python"
