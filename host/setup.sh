#!/bin/bash
# One-time setup for the talking skull on an Apple Silicon Mac.
# Run from the folder that holds skull.py:   bash setup.sh
set -e

if ! command -v brew >/dev/null; then
  echo "Homebrew not found. Install it from https://brew.sh then re-run this script."; exit 1
fi

brew install python@3.12 portaudio
PY="$(brew --prefix)/bin/python3.12"

"$PY" -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install numpy sounddevice webrtcvad-wheels mlx-whisper anthropic pyserial scipy

echo "Downloading the Whisper model (about 1.6 GB, one time)..."
python -c "import mlx_whisper, numpy as np; mlx_whisper.transcribe(np.zeros(16000, dtype=np.float32), path_or_hf_repo='mlx-community/whisper-large-v3-turbo')"

echo
echo "Done. Next:"
echo "  source .venv/bin/activate"
echo "  export ANTHROPIC_API_KEY=sk-ant-...     # from console.anthropic.com"
echo "  python skull.py --list-devices"
echo "  python skull.py --text                  # test Claude + voice without the mic"
