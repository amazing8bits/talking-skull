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

# Print the first serial port that carries the firmware's "PRESENCE" heartbeat (sent every 2 s).
# Boards like the Waveshare ESP32-S3 show up as two ports (USB-UART and native USB/JTAG),
# and only one of them carries Serial, so listening is more reliable than guessing by name.
find_esp32_port() {
  python - "$@" <<'EOF'
import sys, time, serial
for port in sys.argv[1:]:
    try:
        with serial.Serial(port, 115200, timeout=0.2) as s:
            buf, end = b"", time.time() + 4
            while time.time() < end:
                buf += s.read(256)
                if b"PRESENCE" in buf:
                    print(port)
                    sys.exit(0)
    except (serial.SerialException, OSError):
        pass
sys.exit(1)
EOF
}

# Give USB devices (ESP32, mic array) a moment to appear after login
sleep "${SKULL_START_DELAY:-10}"

while true; do
  # If SKULL_PORT is "auto", use the USB serial port the ESP32 firmware is talking on
  ARGS="$SKULL_ARGS"
  if [ "${SKULL_PORT:-}" = "auto" ]; then
    CANDIDATES=$(ls /dev/cu.usbmodem* /dev/cu.usbserial* /dev/cu.wchusbserial* 2>/dev/null)
    if [ -z "$CANDIDATES" ]; then
      echo "$(date '+%H:%M:%S') ESP32 not found on USB, retrying..."
      sleep 5; continue
    fi
    # shellcheck disable=SC2086
    PORT=$(find_esp32_port $CANDIDATES)
    if [ -z "$PORT" ]; then
      echo "$(date '+%H:%M:%S') No PRESENCE heartbeat on:" $CANDIDATES "(is the firmware flashed?) Retrying..."
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
