# Build guide

How the talking skull was put together, in roughly the order it was built. Part numbers are in [`hardware/BOM.md`](../hardware/BOM.md) and pin assignments in [`hardware/wiring.md`](../hardware/wiring.md).

All the printed parts (neck bracket, jaw servo bracket, speaker bracket) were printed in **PLA** on an **Elegoo Neptune 4 Max**.

The prop is built into an off-the-shelf plastic anatomical skeleton. The skull splits into screwed front and back halves, and the head sits on a neck post. Your skeleton will differ, so measure before cutting anything.

**Starting skeleton and mods.** This skeleton came with LED eyes, which were removed to make room for the LCDs. Their openings were already the right place and size for the displays, so the eye sockets needed no cutting. The rest of the changes:

- **Skull:** opened along its front/back seam; the battery holder in the back half cut out to make room for a larger speaker; the skull post's hole drilled out to 3/8" for the neck rod.
- **Wrench holes:** two small holes drilled in the back of the skull so an Allen key can reach the neck bracket screws.
- **Cable holes:** holes drilled in the back of the skull for the neck servo's wires, the ESP32's USB cable, and the power cable to the jaw servo.
- **Neck lock:** the locking nubs in the neck, which kept the head from turning, ground off with a Dremel so the head rotates freely.
- **Neck and spine:** the original neck post and blocking screw posts removed, and plastic ground out of the inside of the neck and spine with a Dremel to make room for the drivetrain and servo. The servo is larger than the space in the spine, so a cutout was made in the back of the spine for it.
- **Jaw:** a screw that locked the jaw shut removed. The skeleton was molded with a jaw lever and mounting points for a talking speaker that was never installed; that original lever is kept and wrapped in aluminum to take the ball link.

![The finished skull on the bench](images/skull-assembled.jpg)

*The finished build on the bench: eye displays behind acrylic lenses, and the reSpeaker XVF3800 mic array resting on the chest.*

![The two skull halves opened up and cleared out](images/skull-halves-prepped.jpg)

*The skull halves opened up. In the back half (top), the battery holder has been cut out to make room for the speaker; the front half keeps the original jaw lever and pivot.*

**Build order:** eyes first (wired to the ESP32 and tested), then the jaw servo and bracket, then the speaker, then the neck drivetrain, then the mic array, and the radar last. The sections below follow that order.

## 1. Know your plastic

The skull and jaw plastic floats in water and has a firm, glossy surface, which means it's a polyolefin (polypropylene or polyethylene). Most glues won't stick to it, so:

- **Hot glue plus screws** holds everything in this build. The screws carry the load and the glue fills gaps and stops rattles.
- Use **high-temp glue sticks**, flame-treat the plastic briefly before gluing, and preheat any metal parts so the glue doesn't skin over before it wets the surface.
- Hot glue softens around 60 °C, so keep the finished prop out of direct afternoon sun and hot cars or attics.
- If you want a stronger, permanent bond, 3M DP8005/DP8010 is made for polyolefins, but it's expensive.

## 2. Eyes

- Two 1.28" round GC9A01 displays sit behind the eye sockets, in the openings left by the skeleton's original LED eyes, each covered by a **35 mm acrylic lens**. The lens magnifies the image slightly and gives it a wet, rounded look.
- **Lenses:** each lens is stuck to the face of its display with a few **small strips of double-sided tape** around the edge, keeping the tape off the visible part of the screen. The displays are then hot-glued in behind the sockets.
- Both displays share SPI clock, data, DC and reset; each has its own chip select. The pins are in [`wiring.md`](../hardware/wiring.md).
- They're mounted upside down, so the sketch rotates them 180°. They run at 20 MHz SPI on jumper wires; short wires may handle 40 MHz.
- The eye artwork is generated procedurally by [`tools/eyegen`](../tools/eyegen/), so it's original and free to share. The renderer runs on core 0 of the ESP32 so it never delays the servos or radar.
- If the eyes look away from visitors, flip `EYE_INVERT_X` in the sketch.
- **Connect and test right away.** Wire both displays to the ESP32 with DuPont jumper connectors (pins in [`wiring.md`](../hardware/wiring.md)), upload the sketch, and send `EYES 1` and `GAZE 50 -20` from the Serial Monitor. It's much easier to fix a display or wiring problem now than with everything else in the skull.

![Both eye displays hot-glued behind the sockets](images/eyes-mounted.jpg)

*The two GC9A01 displays hot-glued directly behind the eye sockets.*

![Eye display wiring with connectors](images/eye-wiring.jpg)

*Each display's wiring ends in a connector, so the front half of the skull can be unplugged and separated.*

## 3. Jaw

The HS-65MG micro servo opens the jaw through a short pushrod.

- **Bracket:** a one-piece bracket designed in Fusion 360 and printed in PLA, with a pocket the servo sits in. The bracket is hot-glued to the inside of the skull and also held by **two M2.6 × 10 mm self-tapping screws**, driven from the roof of the skull's mouth up into the bracket. The screws carry the load; the glue fills gaps and stops rattles.
![HS-65MG seated in its 3D-printed bracket](images/jaw-servo-bracket.jpg)

*The HS-65MG seated in its 3D-printed bracket, with the ball stud on the servo horn that the jaw's ball link snaps onto.*

- **Servo screws:** the servo is fastened to the bracket with **M2 screws into M2 heat-set inserts** in the print. The HS-65MG's ear holes are too small for M2, so **drill out one hole in each ear** to fit.
- **Servo horn:** the hole in the HS-65MG's horn was too small for the ball link's ball stud, so it was drilled out slightly. Go up in small steps until the stud threads in snugly, since a loose stud adds play to the jaw.
- **Jaw lever:** the skeleton's plastic jaw lever is wrapped in thin aluminum to give the linkage a solid mounting point. The wrap is hot-glued and clamped with small screws.
- **Linkage:** two Du-Bro 2-56 threaded ball links on a short 2-56 rod (cut from a 2-56 × 1" screw). Ball links have no free play, so the jaw starts moving on each syllable instead of rattling first, and the rod threads in and out to adjust the closed position.
- Aim for the pushrod to sit roughly perpendicular to both the servo horn and the jaw lever at mid-travel, so the motion stays even across the sweep.

![Jaw with the aluminum-wrapped lever and ball-link pushrod](images/jaw-linkage.jpg)

*The jaw on the bench: aluminum wrap on the plastic lever, a Du-Bro ball link on 2-56 rod, and the HS-65MG.*

![Jaw lever and ball link installed next to the right eye](images/eye-and-jaw-lever.jpg)

*Installed: the ball link on the wrapped jaw lever, next to the hot-glued eye display.*

**Connect** the servo's signal wire to GPIO 4 on the ESP32 with a DuPont jumper. Its power comes from the servo supply, not the ESP32, through a cable that enters through a hole in the back of the skull (see [Power](#8-power)). Then **calibrate** with the Serial Monitor (115200 baud): send `JAWUS 1400`, `JAWUS 2000` and values in between to find where the jaw is just closed and fully open, then set `JAW_CLOSED_US` and `JAW_OPEN_US` in the sketch. Set "closed" just before the jaw touches, so the servo never pushes against it. A stalled servo buzzes, which you'll hear on a prop whose job is talking.

## 4. Speaker

- **Speaker:** a Peerless PLS-P830983 2" full-range driver inside the skull, driven by a TPA3116D2 amp next to the Mac. The amp's speaker outputs are bridged, so never connect either speaker wire to ground.
- **Speaker mounting:** the driver is screwed into a 3D-printed bracket with **M4 screws** into **M4 heat-set inserts**, pressed into the print with a soldering iron. A layer of **car-speaker sealing tape** (foam gasket) between the speaker and the bracket decouples it from the skull, so the plastic doesn't buzz or rattle along with it.

![Speaker in its bracket and the TPA3116D2 amp](images/speaker-and-amp.jpg)

*The 2" driver in its 3D-printed bracket, fitted where the battery holder was cut out of the back of the skull, with the TPA3116D2 amp board.*

- **Gain:** set the Mac's output volume high and the amp's gain low. The voice stays loud and any background noise stays quiet.
- **Buzz:** if the speaker buzzes, unplug things one at a time to find the source (the audio cable, then the ESP32's USB). A **ground-loop isolator** on the 3.5 mm cable from the mic array to the amp fixes most cases. Also keep servo current out of the USB ground (see [power](../hardware/wiring.md#power)) and keep audio wires away from servo wires.

## 5. Neck pan drivetrain

The HS-488HB sits in the upper spine and turns the head through a 1/4" rod that runs up the neck inside a fixed aluminum tube.

![Neck drivetrain cross-section](images/neck_drivetrain.svg)

![The drivetrain installed in the cut-open spine](images/neck-drivetrain-installed.jpg)

*The finished drivetrain with the spine cut open: HS-488HB at the bottom, flexible coupler, aluminum tube, then the collar, hub and square beam in the black 3D-printed bracket at the base of the skull. The speaker in its bracket is in the back half on the left.*

**Prepare the skeleton**
1. Remove the skeleton's original neck post and any screw posts that block the tube. The upper neck halves on this skeleton are screwed together, not glued, so they come apart.
2. Drill the skull post's square display-stand hole out to **3/8" round**. It's a clearance hole only: the rod passes through it without touching.
3. Grind out the inside of the neck and upper spine with a Dremel until the tube, coupler and servo fit. The HS-488HB is larger than the space in the spine, so cut an opening in the back of the spine for it.
4. **Mount the servo:** it sits sandwiched between the spine and the back of the skeleton. Pack it in with plenty of hot glue so it's held tightly and can't shift or twist. Any movement of the servo body is lost head motion and puts side load on the coupler.

**Build the drivetrain**
1. Cut the 5/8" OD aluminum tube to length and deburr both ends inside and out.
2. Fit a flanged ball bearing into each end of the tube, flange facing out, and secure them with Loctite.
3. Cut the 1/4" stainless rod to length. File a small flat where each set screw lands (coupler, hub) so the screws grip and the rod can't slip.
4. At the bottom: 25T servo shaft into the HS-488HB, flexible coupler joining it to the rod. Leave a **~1 mm gap** between the coupler and the bottom bearing so the coupler never pushes up on it.
5. At the top: slide the **clamping collar** onto the rod where it comes out of the tube, rest it on the top bearing, and tighten it. The collar carries the head's weight, so the servo and coupler never do.
6. **Spin test:** turn the rod by hand. If it spins freely, the collar is only touching the bearing's inner race and you're done. If it drags, the collar is rubbing the bearing's outer race or flange, and you need a thin spacer that only touches the inner race (a 3D-printed ring works). On this build it spun freely with no spacer.
7. Inside the skull, fix the **set-screw hub** to the rod above the skull post, leaving a clear gap above the post. Bolt the 5-hole **square beam** to the hub with **two M4 screws through holes 2 and 4** of the beam.
8. The beam is sandwiched in a **two-piece 3D-printed neck bracket** in the base of the skull. One bracket half has **two M4 heat-set inserts**. Two M4 screws pass through the other half, through **holes 1 and 5** of the beam, and into those inserts, clamping the beam between the halves. The bracket is shaped to fit tightly around the plastic bosses inside the skull, so it's **held by friction alone**, with no glue or screws into the skull.
   The chain runs servo hub → square beam → bracket → skull, so the skull turns with the rod.
9. **Wrench access:** with the skull closed you can't reach those two bracket screws, so **drill two holes in the back of the skull**, lined up with the screws, big enough for an Allen key. Then you can tighten or loosen the bracket without opening the head.

**Before you tighten the hub for good:** power the servo at center (1500 µs, `NECKUS 1500` from the Serial Monitor) and set the beam's orientation so the skull faces straight ahead. Then check the full pan range for anything that touches: the collar's pinch bolt, the hub and the wires.

![Test-fitting the head on the drivetrain](images/drivetrain-test-fit.jpg)

*Test-fitting the head on the drivetrain before closing up the spine.*

**Wiring the neck servo:** its leads don't reach the ESP32 in the skull, so they're extended with **two DuPont jumpers joined end to end**, and they enter the skull through a hole drilled in the back. Leave some slack so the wires don't pull as the head turns.

> ⚠️ The HS-488HB has no mechanical stops. Neck travel is limited in firmware by `NECK_MAX_DEG` (40°). Never remove that limit.

## 6. Mic array

- **Mic:** the Seeed reSpeaker XVF3800 bare board is hot-glued to the front of the ribcage and connects to the Mac over USB. It ships with I2S firmware, so flash the **USB firmware** first, or it won't show up on the Mac. The mic openings are on the back (logo) side, so that side has to face the visitors.
- **Not hearing itself:** the Mac plays the skull's voice *through the mic array* over USB (`--out-device ReSpeaker`), and the array's **3.5 mm output jack feeds the amp's input**. Because the array plays the voice itself, its echo cancellation has the exact reference signal and filters the skull's own voice out of what the mics pick up. As a second safeguard, `skull.py` also only listens while the skull isn't talking.
- **Never** connect the amp's speaker outputs to the array. They're a bridged power output, not line level, and could damage it.

## 7. Radar

- The HLK-LD2450 reports up to three people's X/Y positions about 10 times a second, across roughly ±60°.
- It's hot-glued to the **ribcage**, not the turning head, so its coordinates don't move when the neck turns. Keep it level, facing forward and centered below the neck's pivot.
- Radar passes through plastic but not metal. Keep metallic paint, foil and wiring out of the area in front of it.
- It needs **5 V power** but uses **3.3 V UART**, so it wires straight to the ESP32. If the Serial Monitor shows `# radar: NO DATA`, swap the RX and TX pins.
- Tune the trigger zone with `ZONE_MAX_Y` (how far out) and `ZONE_MAX_X` (how wide). If the head turns away from people, flip `NECK_INVERT`.

## 8. Power

Everything runs from mains; there's no battery.

- **Servos:** Triad WSU060-4000, 6 V 4 A, with a 1000 µF capacitor across the servo rail. Measure its output with a meter before connecting the servos.
- **Amp:** MEAN WELL GSM36U12-P1J, 12 V 3 A, through a 3 A fuse.
- **ESP32, radar and eyes:** USB from the Mac mini, which is also the serial link.
- Connect the servo ground to the ESP32 ground **in one place only**.

## 9. Software

![Bench bring-up with the skull open](images/wiring-bringup.jpg)

*Bench bring-up: the ESP32-S3 wired to the eyes and servos, with the Mac mini running the host software.*

![Skull halves with the ESP32-S3 wired in](images/skull-halves-wired.jpg)

*The ESP32-S3 sitting in the front half of the skull, with its USB-C cable to the Mac.*

Follow the [host README](../host/README.md) and [firmware README](../firmware/skull_esp32/README.md). Useful tests along the way:

| Test | Command |
|---|---|
| Claude, voice and jaw without the mic | `python skull.py --text` |
| Fake a visitor | press **Enter** in the `skull.py` window |
| List audio devices | `python skull.py --list-devices` |
| Eyes on, thinking look | `EYES 1`, then `STATE THINK` in the Serial Monitor |
| Point the eyes | `GAZE 50 -20` |
| Neck by hand / back to tracking | `NECK -20`, then `TRACK` |

The ESP32 prints a status line every 2 seconds (radar frames, whether someone is in the zone, eye frame rate) and repeats its `PRESENCE` state, so the Mac recovers if it starts late.

## Tuning the performance

All in the settings block at the top of `skull.py`:

- **Voice:** `SAY_VOICE`, `SAY_RATE`, and `PITCH_DROP` (below 1.0 makes it deeper). `skull_british.py` uses a natural-pitch British voice instead.
- **Personality:** `SYSTEM_PROMPT`, `GREETINGS` and `GOODBYES`. The skull is a theatrical, boastful villain who is secretly delighted by visitors, keeps it family friendly, compliments costumes and never asks for personal details.
- **Listening:** `END_SILENCE` (pause that ends a question) and `SPEECH_OVER_NOISE` (raise it on a noisy street).
- **Jaw sync:** `JAW_LEAD_MS` (raise it if the jaw lags the voice), `JAW_SYLLABLE_DB` (lower it to catch more syllables) and `JAW_MIN_OPEN` (raise it if quiet syllables barely move the jaw).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Stuck at "waiting for visitor" | Check the ESP32 lines in the `skull.py` log. No `PRESENCE` lines means a wrong `--port` or the Serial Monitor is still open. Press Enter to test the rest of the chain. |
| `# radar: NO DATA` | Radar power, or RX and TX swapped |
| `eye sprite allocation failed` | Set Tools → PSRAM to **OPI PSRAM** |
| Only one eye updates | Check that each eye has its own CS pin and the shared pins go to both |
| Head turns away from people | Flip `NECK_INVERT` |
| Jaw buzzes when closed | `JAW_CLOSED_US` drives it into its stop; back it off |
| ESP32 resets when servos move | Servos are drawing from USB; give them their own supply |
| Speaker buzz or hum | See [Speaker](#4-speaker) |
| Whisper hears words in silence | Common phantom phrases are already filtered in `HALLUCINATIONS`; add any new ones there |
