#!/usr/bin/env python3
"""
Talking skull with a normal-sounding British voice.

Runs exactly like skull.py (same options, same ESP32 link, jaw, eyes and modes) and uses all of its code,
so any fix to skull.py applies here too. It only changes the skull mode's voice:

    python skull_british.py --link serial --port /dev/cu.usbmodemXXXX --in-device ReSpeaker --out-device ReSpeaker
    python skull_british.py --voices      # list the British voices installed on this Mac

Better-sounding voices: System Settings > Accessibility > Spoken Content > System Voice >
Manage Voices > English (United Kingdom), download e.g. "Jamie (Premium)" or "Daniel (Enhanced)",
then put that exact name first in PREFERRED_VOICES below.
"""
import sys

import skull

# Tried in order; the first one installed is used. Daniel ships with every Mac.
PREFERRED_VOICES = ["Jamie (Premium)", "Daniel (Enhanced)", "Serena (Premium)", "Daniel"]
SAY_RATE = 180       # words per minute; normal conversational pace
PITCH_DROP = 1.0     # 1.0 = the voice's natural pitch (no deepening)


if __name__ == "__main__":
    if "--voices" in sys.argv:
        print("British voices on this Mac:")
        for v in skull.british_voices():
            print("  ", v)
        sys.exit()

    voice = skull.pick_british_voice(PREFERRED_VOICES)
    if voice is None:
        sys.exit("No British English voice found. Add one in System Settings > Accessibility > "
                 "Spoken Content > System Voice > Manage Voices > English (United Kingdom).")
    skull.SKULL.voice, skull.SKULL.rate, skull.SKULL.pitch = voice, SAY_RATE, PITCH_DROP
    skull.log(f"Voice: {voice} at {SAY_RATE} wpm")
    skull.main()
