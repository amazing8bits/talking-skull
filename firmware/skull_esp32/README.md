# ESP32-S3 firmware

Runs on the Waveshare ESP32-S3 N16R8 and controls the jaw and neck servos, the LD2450 radar tracking, the two GC9A01 eyes, and the UDP link to the Mac mini.

## Arduino IDE settings

- Board: **ESP32S3 Dev Module**
- Flash size: **16 MB**
- PSRAM: **OPI PSRAM**

## Libraries

- LovyanGFX (eyes; works better on the S3 than TFT_eSPI)
- ESP32Servo
<!-- TODO: confirm against the sketch's #includes -->

## Setup

Copy `secrets.example.h` to `secrets.h` and fill it in. `secrets.h` is gitignored.

## Safety

The HS-488HB neck servo has **no mechanical stops**. The neck limits are set in firmware (±70°), so check them before changing any neck code.

## Radar note

LD2450 coordinates use sign-magnitude encoding, not two's complement:
`v & 0x8000 ? (v & 0x7FFF) : -(v & 0x7FFF)`
