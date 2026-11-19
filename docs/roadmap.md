# Roadmap

## Done
- [x] Halloween 2026: radar wake-up and neck tracking, Claude conversation, on-device speech-to-text, syllable-synced jaw, animated eyes
- [x] Original procedurally generated eye artwork ([`tools/eyegen`](../tools/eyegen/))
- [x] Mains power throughout: dropped the battery and buck converters

## Next
- [ ] **Maker Faire Philadelphia** exhibit
- [ ] **Turn toward whoever is speaking.** The XVF3800 reports the direction speech comes from. While listening, the Mac would match that direction to the nearest radar target, hold the match for about half a second so the head doesn't flip between people, and tell the ESP32 who to look at. Needs a new serial command and a short calibration between the radar and mic angles.
- [ ] **Camera** to see visitors' costumes and comment on them. The challenge is seeing color at night: a low-light color sensor plus warm lighting on the walkway, rather than infrared. Any vision processing should keep nothing: no stored faces or images.
- [ ] **Arms and hands** that gesture while the skull talks, starting with a shoulder actuator built into the skeleton's shoulder joint
- [ ] **Video calls:** appear in a Zoom meeting (using Zoom RTMS to tell who is talking) and on FaceTime
