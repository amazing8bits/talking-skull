# ESP32-S3 firmware

Runs on the Waveshare ESP32-S3-DEV-KIT-N16R8:

- **LD2450 radar:** detects visitors and sends `PRESENCE 1` / `PRESENCE 0` to the Mac
- **Neck (HS-488HB):** turns toward the closest visitor
- **Jaw (HS-65MG):** follows the `JAW n` messages from `skull.py`
- **Eyes (2× GC9A01):** look at the visitor, blink, and react to LISTEN / THINK / SPEAK. They render on core 0 so they never hold up the servos or radar.

## Arduino IDE settings

- Board: **ESP32S3 Dev Module**
- Flash size: **16 MB**
- PSRAM: **OPI PSRAM** (the eyes need it)
- USB CDC On Boot: **Disabled**
- Libraries (Library Manager): **ESP32Servo**, **LovyanGFX**

## Files

| File | |
|---|---|
| `skull_esp32.ino` | Main sketch: radar, servos, serial commands, eye behavior |
| `eye_art.h` | Eye renderer: sclera, polar-mapped iris with live pupil size, pupil color ramp (for the glow), curved lids, lid shadow, foreshortening, glints |
| `eye_sets.h` | The eye looks built into the firmware. The Mac picks one with `LOOK <name>`; the first is the look at power-on |
| `eye_set_glow.h` | Glowing red pupils on a black sclera (skull mode), **generated** by [`tools/eyegen`](../../tools/eyegen/). Don't edit by hand |
| `eye_set_hazel.h` | Natural hazel eyes on a white sclera (presenter mode), also generated |

The two looks were made with:
```bash
cd tools/eyegen
python3 eyegen.py --color smolder --sclera black --pupil glow --seed 7 --header ../../firmware/skull_esp32/eye_set_glow.h
python3 eyegen.py --color hazel --sclera white --pupil dark --seed 7 --header ../../firmware/skull_esp32/eye_set_hazel.h
```
To change a look, regenerate its file with other options and re-upload. To add a look, generate `eye_set_<name>.h`, add it to `eye_sets.h`, and send `LOOK <name>`. Each set takes about 150 KB of flash.

## Display orientation

The eye displays are installed upside down so they fit in the skull, and `setupEyes()` rotates both panels 180° with `tft.setRotation(2)`. If yours are mounted right side up, use `setRotation(0)`.

## Serial Monitor commands (115200)

`JAWUS 1500`, `NECKUS 1500`, `NECK -20`, `TRACK` for servo calibration. `EYES 1`, `STATE THINK`, `BLINK`, `GAZE x y` (−100..100) for eye testing. `LOOK GLOW` / `LOOK HAZEL` to switch the eye artwork (it blinks over the change).

## Safety

The HS-488HB has **no mechanical stops**. Neck travel is limited in software by `NECK_MAX_DEG` (40°), so keep that limit when you change the neck code.

## Radar note

LD2450 coordinates use sign-magnitude encoding: bit 15 set means positive, and the low 15 bits are the magnitude.
