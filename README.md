# Talking Skull 💀

An animatronic talking skull that notices people walking up, turns to look at them, and talks with them. The skull hears you, thinks with Claude, and answers back with a moving jaw and animated LCD eyes.

Built for Halloween 2026 trick-or-treaters. Next stop: Maker Faire Philadelphia.

<!-- Add a photo or GIF here: docs/images/skull.jpg -->

## How it works

```
 LD2450 radar ──UART──▶ ESP32-S3 ◀──USB serial──▶ Mac mini (M4)
                          │                            │
        jaw servo ◀───────┤                            ├── USB mic array ──▶ Whisper (MLX, on-device STT)
        neck servo ◀──────┤                            ├── Claude API (Haiku) — skull persona
        2× GC9A01 eyes ◀──┘                            └── macOS `say` TTS ──▶ amp ──▶ 2" speaker
```

1. The **LD2450 mmWave radar** spots a visitor and reports their position.
2. The **ESP32-S3** wakes the eyes, turns the neck to track the visitor, and tells the Mac someone is there.
3. The **Mac mini** greets the visitor, listens through the reSpeaker XVF3800 mic array, transcribes with Whisper, gets a reply from Claude, and speaks it.
4. While the skull speaks, the Mac streams jaw positions to the ESP32 over USB serial. Jaw sync uses per-syllable peak/valley detection with a little servo lead time, so syllables don't blur together.
5. The eyes change behavior with the conversation (idle, listening, thinking, speaking): gaze tracking, saccades, blinks and pupil size. The eye artwork is original and generated procedurally by [`tools/eyegen`](tools/eyegen/).

The ESP32 handles real-time work: servos, eyes, radar. The Mac handles AI and audio.

## Repository layout

| Path | What's in it |
|---|---|
| [`host/`](host/) | Mac mini software: the conversation loop, setup script, login launcher |
| [`firmware/skull_esp32/`](firmware/skull_esp32/) | ESP32-S3 Arduino sketch: servos, radar, eyes, USB serial link to the Mac |
| [`hardware/`](hardware/) | Bill of materials, wiring and pinout, power |
| [`hardware/cad/`](hardware/cad/) | 3D-printable parts (jaw servo bracket and others) |
| [`tools/eyegen/`](tools/eyegen/) | Generator for the original eye artwork |
| [`docs/`](docs/) | Build notes, lessons learned, roadmap |

## Quick start

**Mac mini**
```bash
cd host
bash setup.sh                 # one-time install
cp .env.example .env          # add your ANTHROPIC_API_KEY
source .venv/bin/activate && export ANTHROPIC_API_KEY=sk-ant-...
python skull.py --text        # test without the mic or ESP32
```
Then double-click `start_skull.command`, or add it to Login Items. See [`host/README.md`](host/README.md).

**ESP32-S3**
1. Open `firmware/skull_esp32/skull_esp32.ino` in the Arduino IDE (board *ESP32S3 Dev Module*, PSRAM *OPI PSRAM*, USB CDC On Boot *Disabled*).
2. Install **ESP32Servo** and **LovyanGFX**, then upload. See the [firmware README](firmware/skull_esp32/README.md).

> ⚠️ The HS-488HB neck servo has no mechanical stops. The firmware limits it to ±40° (`NECK_MAX_DEG`), so don't remove that limit.

## Hardware at a glance

- Waveshare ESP32-S3 N16R8 dev kit (16 MB flash / 8 MB PSRAM)
- HLK-LD2450 24 GHz mmWave radar
- 2× 1.28" GC9A01 round 240×240 LCDs (eyes)
- Hitec HS-65MG (jaw) and HS-488HB (neck)
- M4 Mac mini, Seeed Studio reSpeaker XVF3800 USB mic array (bare board), TPA3116D2 amp, Peerless PLS-P830983 2" 4 Ω driver
- Triad WSU060-4000 6 V 4 A adapter for the servos; the ESP32 is powered over USB from the Mac

Full details are in [`hardware/BOM.md`](hardware/BOM.md) and [`hardware/wiring.md`](hardware/wiring.md).

## Roadmap

See [`docs/roadmap.md`](docs/roadmap.md). Highlights: a camera to recognize costumes (night vision is the hard part), a Zoom guest appearance through Zoom RTMS, and the Maker Faire Philly exhibit.

## License

MIT. See [LICENSE](LICENSE).
