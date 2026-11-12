#!/usr/bin/env python3
"""
Talking skull with a normal-sounding British voice.

Runs exactly like skull.py (same options, same ESP32 link, jaw and eyes) and uses all of its code,
so any fix to skull.py applies here too. It only changes the voice:

    python skull_british.py --link serial --port /dev/cu.usbmodemXXXX --in-device ReSpeaker --out-device ReSpeaker
    python skull_british.py --voices      # list the British voices installed on this Mac

Better-sounding voices: System Settings > Accessibility > Spoken Content > System Voice >
Manage Voices > English (United Kingdom), download e.g. "Jamie (Premium)" or "Daniel (Enhanced)",
then put that exact name first in PREFERRED_VOICES below.
"""
import re
import subprocess
import sys

import skull

# Tried in order; the first one installed is used. Daniel ships with every Mac.
PREFERRED_VOICES = ["Jamie (Premium)", "Daniel (Enhanced)", "Serena (Premium)", "Daniel"]
SAY_RATE = 180       # words per minute; normal conversational pace
PITCH_DROP = 1.0     # 1.0 = the voice's natural pitch (no deepening)


def british_voices():
    """Names of the en_GB voices installed, from `say -v '?'`."""
    out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    names = []
    for line in out.splitlines():
        m = re.match(r"^(.+?)\s+(en[_-]GB)\s+#", line)
        if m:
            names.append(m.group(1).strip())
    return names


def pick_voice():
    installed = british_voices()
    for v in PREFERRED_VOICES:
        if v in installed:
            return v
    if installed:
        return installed[0]
    sys.exit("No British English voice found. Add one in System Settings > Accessibility > "
             "Spoken Content > System Voice > Manage Voices > English (United Kingdom).")


if __name__ == "__main__":
    if "--voices" in sys.argv:
        print("British voices on this Mac:")
        for v in british_voices():
            print("  ", v)
        sys.exit()

    skull.SAY_VOICE = pick_voice()
    skull.SAY_RATE = SAY_RATE
    skull.PITCH_DROP = PITCH_DROP
    skull.log(f"Voice: {skull.SAY_VOICE} at {SAY_RATE} wpm")
    skull.main()
