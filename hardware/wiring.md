# Wiring

## ESP32-S3 pin map

| Signal | GPIO | Notes |
|---|---|---|
| Jaw servo (HS-65MG) | 4 | |
| Neck servo (HS-488HB) | 5 | Direction is inverted in firmware so the skull tracks visitors |
| LD2450 TX → ESP32 RX | 16 | The radar UART uses 3.3 V logic |
| LD2450 RX ← ESP32 TX | 17 | |
| Eye SCL (SPI clock) | 12 | Shared by both eyes |
| Eye SDA (SPI data) | 11 | Shared |
| Eye DC | 8 | Shared |
| Eye RST | 18 | Shared |
| Left eye CS | 10 | |
| Right eye CS | 9 | |

The eyes run at 20 MHz SPI over jumper wires. With short wires you can try 40 MHz (`SPI_HZ`). Both panels are mounted upside down, so the sketch rotates them 180°.

The Mac link is **USB serial** (115200 baud) through the dev kit's USB-C port.

## Power

```
Mains ──▶ Triad WSU060-4000 (6 V 4 A) ──▶ servo rail (jaw + neck) ── 1000 µF cap
Mac mini USB ──▶ ESP32-S3 USB-C (power + serial) ──▶ radar 5 V, eyes 3.3 V
Mains ──▶ Mac mini ──USB──▶ reSpeaker XVF3800 ──3.5 mm out──▶ TPA3116D2 amp input ──▶ speaker in the skull
Mains ──▶ MEAN WELL GSM36U12-P1J (12 V 3 A) ──[3 A fuse]──▶ TPA3116D2 amp power
```

- **Servos never run from the ESP32 or USB.** At 6 V the HS-488HB alone can draw 1.2 A when it stalls or starts moving.
- **Connect the grounds once:** run one wire from the servo rail ground to an ESP32 GND pin so the servo signals have a reference, and connect it nowhere else. Servo current should return to the adapter through its own wire, not through the ESP32 and the USB cable to the Mac.
- The LD2450 needs **5 V power** but uses **3.3 V UART**, so it connects straight to the ESP32 pins.
- **Audio path:** the Mac plays through the mic array over USB, and the array's 3.5 mm jack feeds the amp. This gives the array's echo cancellation the skull's voice as its reference, so it doesn't hear itself.
- **Connectors:** the eyes and servos connect to the ESP32 with DuPont jumper connectors. The neck servo's leads are extended with two DuPont jumpers joined end to end. **Every DuPont connection is hot-glued** so the servo vibration and head movement can't shake it loose.
- **Cable entry:** the neck servo wires, the ESP32's USB cable and the jaw servo's power cable enter the skull through holes drilled in the back.
- Wire gauge: 20 AWG for power runs, 24–26 AWG for signals.
- **Ground-loop buzz:** if you hear a buzz from the speaker, check that servo current is not flowing through the USB ground (see above), then check the audio ground path. <!-- TODO: note the fix used -->
