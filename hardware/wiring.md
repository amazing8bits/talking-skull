# Wiring

## ESP32-S3 pin map

| Signal | GPIO | Notes |
|---|---|---|
| Jaw servo (HS-65MG) | 4 | |
| Neck servo (HS-488HB) | 5 | Direction is inverted in firmware so the skull tracks visitors |
| LD2450 TX → ESP32 RX | 16 | The radar UART uses 3.3 V logic |
| LD2450 RX ← ESP32 TX | 17 | |
| Eye SPI SCL / SDA | TBD | Shared between both eyes |
| Eye DC / RST | TBD | Shared |
| Left eye CS | TBD | |
| Right eye CS | TBD | |

<!-- TODO: fill in the eye pins from the sketch -->

## Power

```
TalentCell 12 V ──[3 A slow-blow]──┬── XL4016 buck ──▶ servo rail (jaw + neck) ── bulk cap
                                   └── 5 V USB buck ──▶ ESP32-S3 USB-C ──▶ radar 5 V, eyes 3.3 V
Mains ──▶ Mac mini, TPA3116D2 amp ──▶ speaker in the skull
```

- **Common ground:** the servo rail ground must connect to the ESP32 ground, or the servo signals won't have a reference.
- The LD2450 needs **5 V power** but uses **3.3 V UART**, so it connects straight to the ESP32 pins.
- Wire gauge: 20 AWG for power runs, 24–26 AWG for signals.
- **Ground-loop buzz:** the amp and the Mac share mains while the skull runs on battery. If you hear a buzz, check the audio ground path first. <!-- TODO: note the fix used -->
