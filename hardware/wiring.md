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
TalentCell 12 V ──[3 A slow-blow]──── XL4016 buck ──▶ servo rail (jaw + neck) ── bulk cap
Mac mini USB ──▶ ESP32-S3 USB-C (power + serial) ──▶ radar 5 V, eyes 3.3 V
Mains ──▶ Mac mini ──▶ audio out / amp ──▶ speaker in the skull
```

- **Common ground:** the servo rail ground must connect to the ESP32 ground, or the servo signals won't have a reference.
- The LD2450 needs **5 V power** but uses **3.3 V UART**, so it connects straight to the ESP32 pins.
- Wire gauge: 20 AWG for power runs, 24–26 AWG for signals.
- **Ground-loop buzz:** the amp and the Mac share mains while the skull runs on battery. If you hear a buzz, check the audio ground path first. <!-- TODO: note the fix used -->
