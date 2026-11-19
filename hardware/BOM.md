# Bill of Materials

| Qty | Part | Role | Notes |
|---|---|---|---|
| 1 | Waveshare ESP32-S3 N16R8 dev kit | Skull controller | 16 MB flash / 8 MB PSRAM; single USB-C port |
| 1 | HLK-LD2450 24 GHz mmWave radar | Presence and position tracking | UART at 256000 baud; mounted in the fixed base/chest so it stays still when the head turns |
| 2 | 1.28" GC9A01 round LCD, 240×240 SPI | Eyes | Pins RST, CS, DC, SDA, SCL, GND, VCC (no backlight pin) |
| 2 | 35 mm acrylic lens | Eyes | One over each display |
| 1 | Hitec HS-65MG micro servo | Jaw | Ball-joint linkage to the jaw lever; two-piece printed bracket |
| 1 | Hitec HS-488HB servo | Neck pan | No mechanical stops: use software limits |
| 1 | Apple Mac mini M4, 16 GB | AI/audio host | Mains-powered, hidden near the skull |
| 1 | Seeed Studio reSpeaker XVF3800 USB Microphone Array, bare board | Microphone | Connected to the Mac over USB; `--in-device ReSpeaker` matches it by name |
| 1 | TPA3116D2 amplifier board | Audio amp | Mains-powered, next to the Mac |
| 1 | Peerless PLS-P830983, 2" 4 Ω full-range | Speaker | Inside the skull |
| 1 | Triad Magnetics WSU060-4000 (6 V, 4 A, 24 W wall adapter) | Servo power | Regulated; 2.1 × 5.5 mm plug, center positive. Not the WSX060-4000, which has a 2.5 mm center-negative plug. Check the output with a meter before connecting the servos |
| 1 | 2.1 × 5.5 mm barrel jack to screw terminal adapter | Servo power | Connects the adapter to the servo rail |
| 1 | ~1000 µF electrolytic capacitor, 10 V or higher | Servo rail | Across the servo rail near the servos, to absorb current spikes |
| — | 20 AWG power wire, 24–26 AWG signal wire | | |

The ESP32 gets its power and serial link from the Mac mini's USB port, so the skull no longer needs a battery or buck converters.

## Mechanical (neck drivetrain)

| Qty | Part | Notes |
|---|---|---|
| 1 | 6061-T6 aluminum tube, 5/8" OD × 3/8" ID | Structural spine, replaces the skeleton's neck post |
| 2 | Flanged oil-lite bronze bushings, 1/4" ID × 3/8" OD | Pressed into the tube ends with Loctite 638 |
| 1 | 1/4" precision-ground steel rod | Carries torque only |
| 1 | Aluminum bridge | Spans the two bosses inside the skull |

<!-- TODO: add links/prices and anything I've missed -->
