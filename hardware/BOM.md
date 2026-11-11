# Bill of Materials

| Qty | Part | Role | Notes |
|---|---|---|---|
| 1 | Waveshare ESP32-S3 N16R8 dev kit | Skull controller | 16 MB flash / 8 MB PSRAM; single USB-C port |
| 1 | HLK-LD2450 24 GHz mmWave radar | Presence and position tracking | UART at 256000 baud; mounted in the fixed base/chest so it stays still when the head turns |
| 2 | 1.28" GC9A01 round LCD, 240×240 SPI | Eyes | Pins RST, CS, DC, SDA, SCL, GND, VCC (no backlight pin) |
| 1 | Hitec HS-65MG micro servo | Jaw | Ball-joint linkage to the jaw lever; two-piece printed bracket |
| 1 | Hitec HS-488HB servo | Neck pan | No mechanical stops: use software limits |
| 1 | Apple Mac mini M4, 16 GB | AI/audio host | Mains-powered, hidden near the skull |
| 1 | USB 2-mic array (ReSpeaker Lite) | Microphone | Connected to the Mac |
| 1 | TPA3116D2 amplifier board | Audio amp | Mains-powered, next to the Mac |
| 1 | Peerless PLS-P830983, 2" 4 Ω full-range | Speaker | Inside the skull |
| 1 | TalentCell 12 V 7000 mAh battery | Skull power | Feeds both bucks |
| 1 | XL4016 adjustable buck (8 A) | Servo rail | Set to servo voltage |
| 1 | 5 V buck with USB output | Logic rail | Powers the ESP32 over USB-C |
| 1 | 3 A slow-blow fuse and holder | 12 V protection | On the battery output |
| — | Bulk capacitor on the servo rail, 20 AWG power wire, 24–26 AWG signal wire | | |

## Mechanical (neck drivetrain)

| Qty | Part | Notes |
|---|---|---|
| 1 | 6061-T6 aluminum tube, 5/8" OD × 3/8" ID | Structural spine, replaces the skeleton's neck post |
| 2 | Flanged oil-lite bronze bushings, 1/4" ID × 3/8" OD | Pressed into the tube ends with Loctite 638 |
| 1 | 1/4" precision-ground steel rod | Carries torque only |
| 1 | Aluminum bridge | Spans the two bosses inside the skull |

<!-- TODO: add links/prices and anything I've missed -->
