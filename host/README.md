# Host software (Mac mini)

The conversation loop runs on an Apple Silicon Mac (an M4 Mac mini here).

| File | Purpose |
|---|---|
| `skull.py` | Main loop: radar presence → greeting → mic + VAD → Whisper (MLX, on-device) → Claude (streamed) → macOS `say` → speaker, with jaw sync sent to the ESP32 |
| `skull_british.py` | The same loop with a natural-pitch British voice; it imports `skull.py`, so fixes apply to both |
| `setup.sh` | One-time setup: Homebrew Python, PortAudio, a `.venv`, and the Whisper model download |
| `start_skull.command` | Double-click or Login Item launcher; reads `.env` and restarts the skull if it crashes |
| `requirements.txt` | Python dependencies (also installed by `setup.sh`) |
| `.env.example` | Template for your API key, serial port and audio devices |

## Setup

```bash
bash setup.sh
cp .env.example .env        # add your ANTHROPIC_API_KEY, check the device names
source .venv/bin/activate
export ANTHROPIC_API_KEY=sk-ant-...
python skull.py --list-devices
python skull.py --text      # test Claude + voice + jaw without the mic
python skull.py --link serial --port /dev/cu.usbmodem1101 --in-device ReSpeaker --out-device ReSpeaker
```

To start at login, add `start_skull.command` under System Settings → General → Login Items. It reads the key and options from `.env`.

## Talking to the ESP32

The ESP32 firmware talks to the Mac over **USB serial** at 115200 baud with one plain-text message per line:

| Direction | Message | Meaning |
|---|---|---|
| ESP32 → Mac | `PRESENCE 1` / `PRESENCE 0` | Someone in range / nobody. Repeated every 2 s |
| Mac → ESP32 | `EYES 1` / `EYES 0` | Eyes on / off |
| Mac → ESP32 | `STATE IDLE\|LISTEN\|THINK\|SPEAK` | Changes how the eyes behave |
| Mac → ESP32 | `JAW n` | 0 = closed … 255 = wide open, about 50 times a second |

`skull.py` also has a `--link udp` mode, but the current firmware only uses USB serial.

## Tuning

The settings at the top of `skull.py` cover the voice (`SAY_VOICE`, `SAY_RATE`, `PITCH_DROP`), listening (`END_SILENCE`, `SPEECH_OVER_NOISE`), and jaw sync (`JAW_LEAD_MS`, `JAW_SYLLABLE_DB`, `JAW_MIN_OPEN`). The skull's personality is in `SYSTEM_PROMPT`.

Better voices: System Settings → Accessibility → Spoken Content → System Voice → Manage Voices.
