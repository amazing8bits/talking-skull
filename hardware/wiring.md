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

The eyes run at 20 MHz SPI over jumper wires. With short wires you can try 40 MHz (`SPI_HZ`). Both panels are installed upside down so they fit behind the eye sockets; the firmware rotates them 180° (`tft.setRotation(2)`).

The Mac link is **USB serial** (115200 baud) through the dev kit's USB-C port.

## Power

```
Mains ──▶ Triad WSU060-4000 (6 V 4 A) ──▶ barrel jack (screw terminal) ──┬──▶ jaw servo power  ── 1000 µF cap across +/−
                                                                         └──▶ neck servo power
Mac mini USB ──▶ ESP32-S3 USB-C (power + serial) ──▶ radar 5 V, eyes 3.3 V
Mains ──▶ Mac mini ──USB──▶ reSpeaker XVF3800 ──3.5 mm out──▶ TPA3116D2 amp input ──▶ speaker in the skull
Mains ──▶ MEAN WELL GSM36U12-P1J (12 V 3 A) ──[3 A fuse]──▶ TPA3116D2 amp power
```

- **Servo power:** the adapter plugs into a barrel-jack-to-screw-terminal adapter. The wire from its terminals is spliced into a separate power lead for each servo.
- **Servos never run from the ESP32 or USB.** At 6 V the HS-488HB alone can draw 1.2 A when it stalls or starts moving.
- **Connect the grounds once:** run one wire from the servo rail ground to an ESP32 GND pin so the servo signals have a reference, and connect it nowhere else. In this build it's spliced to a DuPont connector on a GND pin. Servo current should return to the adapter through its own wire, not through the ESP32 and the USB cable to the Mac.
- The LD2450 needs **5 V power** but uses **3.3 V UART**, so it connects straight to the ESP32 pins.
- **Audio path:** the Mac plays through the mic array over USB, and the array's 3.5 mm jack feeds the amp. This gives the array's echo cancellation the skull's voice as its reference, so it doesn't hear itself. The link is a right-angle 3.5 mm stereo plug to bare-wire cable: the plug goes into the array's jack and the bare ends into the amp's input terminals.
- **Connectors:** the eyes and servos connect to the ESP32 with DuPont jumper connectors. The neck servo's leads are extended with two DuPont jumpers joined end to end. **Every DuPont connection is hot-glued** so the servo vibration and head movement can't shake it loose.
- **Cable entry:** the neck servo wires, the radar wires, the ESP32's USB cable and the jaw servo's power cable enter the skull through holes drilled in the back.
- **Radar:** four wires soldered to its pads (5 V, GND, TX, RX), spliced to DuPont connectors at the ESP32 end.
- **Wire:** 2-conductor 20 AWG for power (servo supply to the servos, 12 V supply to the amp), 2-conductor 22 AWG from the amp to the speaker, and DuPont jumpers for signals.
- **Ground-loop buzz:** this build avoids it by giving the servos and the amp **separate power supplies** (the 6 V Triad for the servos, the 12 V MEAN WELL for the amp), so servo current never shares a path with the audio. No ground-loop isolator was needed. If you still hear a buzz, check that servo current isn't flowing through the USB ground (see above); a 3.5 mm ground-loop isolator between the mic array and the amp is the fallback.
