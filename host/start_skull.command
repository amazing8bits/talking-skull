#!/bin/bash
# Double-click to start the talking skull, or add it to
# System Settings > General > Login Items to start it at login.
#
# Settings come from .env next to this file (copy .env.example to .env).
# If the script crashes, it restarts after 5 seconds. Close the Terminal window to stop it.

cd "$(dirname "$0")" || exit 1

if [ ! -f .env ]; then
  echo "No .env file. Copy .env.example to .env and add your ANTHROPIC_API_KEY."
  read -r -p "Press Enter to close."
  exit 1
fi
set -a; source .env; set +a

if [ ! -d .venv ]; then
  echo "No .venv found. Run:  bash setup.sh"
  read -r -p "Press Enter to close."
  exit 1
fi
source .venv/bin/activate

SCRIPT="${SKULL_SCRIPT:-skull.py}"

# Give USB devices (ESP32, mic array) a moment to appear after login
sleep "${SKULL_START_DELAY:-10}"

while true; do
  # If SKULL_PORT is "auto", use the first USB serial device
  ARGS="$SKULL_ARGS"
  if [ "${SKULL_PORT:-}" = "auto" ]; then
    PORT=$(ls /dev/cu.usbmodem* /dev/cu.usbserial* /dev/cu.wchusbserial* 2>/dev/null | head -n 1)
    if [ -z "$PORT" ]; then
      echo "$(date '+%H:%M:%S') ESP32 not found on USB, retrying..."
      sleep 5; continue
    fi
    ARGS="$ARGS --link serial --port $PORT"
  elif [ -n "${SKULL_PORT:-}" ]; then
    ARGS="$ARGS --link serial --port $SKULL_PORT"
  fi

  echo "$(date '+%H:%M:%S') Starting: python $SCRIPT $ARGS"
  # shellcheck disable=SC2086
  python "$SCRIPT" $ARGS
  echo "$(date '+%H:%M:%S') Skull stopped (exit $?). Restarting in 5 s..."
  sleep 5
done
