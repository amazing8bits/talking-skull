#!/usr/bin/env python3
"""
Talking skull brain for the M4 Mac mini.

Loop:  radar presence -> greet -> listen (mic + VAD) -> Whisper (MLX, on-device)
       -> Claude (streamed) -> macOS `say` TTS, sentence by sentence -> speaker
       -> jaw values sent to the ESP32 in sync with the audio.

Quick tests:
    python skull.py --list-devices          # find your mic / amp output numbers
    python skull.py --text                  # type instead of talk (tests Claude + TTS + jaw)
    python skull.py --link none             # press Enter to fake the radar trigger
    python skull.py --link serial --port /dev/cu.usbmodem1101
    python skull.py --link udp --esp-ip 192.168.1.50

Modes (say it to the skull, or pick one at startup with --mode):
    "switch to presenter mode"   Bob, a friendly teacher who explains how the skull was built:
                                 British voice, hazel eyes on a white sclera
    "switch to skull mode"       the Halloween villain: deep voice, glowing red pupils

ESP32 line protocol (plain text, one message per line, \n terminated):
    ESP32 -> Mac:  PRESENCE 1      someone in range      PRESENCE 0   nobody
    Mac -> ESP32:  EYES 1 / EYES 0                       eyes on / off
                   STATE IDLE|LISTEN|THINK|SPEAK         lets the eyes act alive
                   JAW n                                 n = 0 (closed) .. 255 (wide open), ~30x per second
                   LOOK name                             eye artwork: glow (skull mode) or hazel (presenter)
"""

import argparse
import os
import queue
import random
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import wave
from collections import deque
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

# ----------------------------------------------------------------------------
# Settings you will most likely want to change
# ----------------------------------------------------------------------------
CLAUDE_MODEL = "claude-haiku-5-5"        # fastest; try "claude-sonnet-5-5" for wittier answers
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"   # "mlx-community/whisper-tiny" if you want it even faster
SAY_VOICE = "Ralph"                      # run `say -v '?'` to list voices. Ralph/Fred/Daniel all work
SAY_RATE = 165                           # words per minute
PITCH_DROP = 0.92                        # 1.0 = normal; <1 makes the voice deeper (and a little slower).
                                         # Deeper than ~0.9 gets muddy and hard to understand on the small speaker
CLARITY = True                           # clean up the skull voice for the 2" speaker (see clarify())
CLARITY_HIGHPASS_HZ = 180                # cut bass below this: the speaker can't play it, it only eats amp power
CLARITY_PRESENCE_DB = 6.0                # boost around 3 kHz, where consonants (t, s, k) carry the words
MAX_TURNS = 20                           # safety cap; normally a chat ends when they stop talking or walk away
REWAKE_SECS = 12                         # if the same person is still standing there after goodbye, wake again after this
LISTEN_TIMEOUT = 8.0                     # seconds to wait for someone to start talking
MAX_UTTERANCE = 7.0                      # seconds, hard cap on a single question
END_SILENCE = 0.6                        # seconds of quiet that ends a question
VAD_AGGRESSIVENESS = 3                   # 0-3; 3 is strictest about what counts as speech
SPEECH_OVER_NOISE = 2.5                  # a frame must be this many times louder than the background to count as speech
JAW_FPS = 50                             # jaw updates per second (matches the servo's 50 Hz refresh)
JAW_LEAD_MS = 70                         # start each jaw move this early to cover servo travel time; raise if the jaw lags the voice
JAW_SYLLABLE_DB = 3.5                    # loudness dip (dB) that separates two syllables; lower = catches more syllables
JAW_MIN_OPEN = 0.45                      # how far the softest syllable opens (0-1); raise if quiet syllables barely move
JAW_MAX_OPEN = 1.0                       # how far the loudest syllable opens (0-1)
JAW_GATE_DB = -30                        # sound this far below the loud parts keeps the jaw shut

SYSTEM_PROMPT = """You are a talking skull — the ancient, theatrical overlord of this house's Halloween display, \
in the spirit of a cartoon villain sorcerer: grand, boastful, sneering at "fools", but secretly delighted by visitors.
You are speaking out loud to trick-or-treaters, many of them young children, and their parents.

Rules:
- Reply in 1 to 3 short sentences. This is spoken aloud, so no lists, no emoji, no stage directions, no asterisks.
- Spooky-fun, never truly frightening, gory, or mean. Keep everything family friendly.
- Compliment costumes extravagantly when someone mentions theirs.
- Never ask for anyone's name, address, school, or any personal details, and never encourage a child to go anywhere.
- If you can't understand someone, say so in character and ask them to speak up.
- You are a prop on a porch: you cannot move, and you are fond of telling people to take some candy."""

GREETINGS = [
    "Who dares approach my lair? Speak, mortal!",
    "Ahh, fresh visitors! Tell me, what manner of creature are you?",
    "Halt! None pass without speaking to the master of this house. What say you?",
    "Welcome, fools! I mean, friends. What brings you to my doorstep?",
]
GOODBYES = [
    "Enough! Take your candy and begone!",
    "Go now, before I change my mind. And take some candy!",
    "Farewell, mortals. Happy Halloween!",
]

# ----------------------------------------------------------------------------
# Presenter mode: say "switch to presenter mode" (or start with --mode presenter).
# Bob, a friendly teacher, explains what the skull is and how it was built, in a British voice
# with natural hazel eyes. "Switch to skull mode" goes back. Keep PRESENTER_PROMPT short:
# it is sent with every question, so a longer prompt means slower answers.
# ----------------------------------------------------------------------------
PRESENTER_VOICES = ["Jamie (Premium)", "Daniel (Enhanced)", "Serena (Premium)", "Daniel"]  # first installed wins
PRESENTER_RATE = 180                     # words per minute
PRESENTER_PITCH = 1.0                    # natural pitch

PRESENTER_PROMPT = """You are Bob, a friendly, enthusiastic teacher who is also a talking animatronic skull. \
You are presenting yourself at a maker event: explain what you are and answer questions about how you were built. \
You are speaking out loud to visitors of all ages, including kids.

Rules:
- Reply in 1 to 3 short sentences (up to 4 when explaining how something works). This is spoken aloud: no lists, \
no emoji, no stage directions, no asterisks.
- Explain like a good teacher: simple words for kids, more technical detail when an adult asks for it.
- Only use the facts below. If you don't know a detail, say so and point people to the build guide on GitHub. \
Never invent part numbers, specs or prices.
- Never ask for anyone's name, address, school, or any personal details. Be playful about being a skull, never scary.

Facts about you:
- You were built into a 5 foot poseable plastic Halloween skeleton and talked with trick-or-treaters on Halloween 2026. \
Next stop: Maker Faire Philadelphia. Normally you are a theatrical villain skull; "presenter mode" makes you Bob.
- How a conversation works: a 24 gigahertz mmWave radar (HLK-LD2450) on the spine notices someone walking up and tracks \
up to three people. Your eyes wake up, your head turns toward them, and you greet them. A far-field microphone array \
listens, Whisper turns the speech into text right on the Mac (no audio leaves the building), Claude from Anthropic \
writes the reply, and the Mac's built-in text-to-speech says it, starting as soon as the first sentence is ready.
- The brain is an M4 Mac mini running Python, hidden nearby (not inside the skull). Inside, an ESP32-S3 microcontroller handles the real-time \
jobs: radar, neck, jaw and eyes. They talk over a USB cable with simple text messages, like "JAW 200", 50 times a second.
- Jaw: a Hitec HS-65MG micro servo with a ball-link rod. It opens once per syllable, wider for louder ones, and moves \
slightly ahead of the sound to make up for the servo's travel time.
- Neck: a Hitec HS-488HB servo in the spine turns a steel rod inside an aluminum tube. That servo has no end stops, \
so software limits the turn to 40 degrees each way.
- Eyes: two 1.28 inch round GC9A01 screens behind acrylic lenses. The artwork is original, generated by a Python script. \
The pupils grow and shrink, the eyes blink, and they glance up and away while thinking. Red glowing pupils in skull \
mode, hazel eyes as Bob.
- Sound: a reSpeaker XVF3800 mic array, whose headphone jack feeds a TPA3116D2 amplifier and a 2 inch Peerless speaker \
inside the skull.
- Power: wall adapters only, 6 volts for the servos and 12 volts for the amp, with the ESP32 powered over USB.
- It's open source under the MIT license: code, wiring, parts list and a step-by-step build guide are on GitHub at \
amazing8bits slash talking-skull. A build video is coming to YouTube."""

PRESENTER_GREETINGS = [
    "Hello there! I'm Bob, a talking skull. Ask me anything about how I was built!",
    "Hi! I'm Bob. Ever wondered how a skeleton learns to talk? Ask away!",
    "Welcome! I'm Bob, your bony tour guide. What would you like to know about me?",
]
PRESENTER_GOODBYES = [
    "Thanks for stopping by! Go build something amazing.",
    "It was lovely chatting with you. Happy making!",
    "Cheerio! The whole project is on GitHub if you'd like to build one.",
]

# Spoken commands that change modes (matched on the Whisper transcript, case and punctuation ignored)
SWITCH_VERB = r"\b(switch|change|go|turn|put|flip)\w*\b.{0,20}?"
MODE_COMMANDS = {
    "presenter": re.compile(SWITCH_VERB + r"\b(present|presenter|presentation|presenting|teacher)\s+mode\b"),
    "skull": re.compile(SWITCH_VERB + r"\b(skull|halloween|spooky|scary|villain)\s+mode\b"),
}

# Whisper sometimes "hears" these in noise. Treat them as silence.
HALLUCINATIONS = {"", "you", "thank you.", "thank you", "thanks for watching!", "thanks for watching.",
                  "bye.", ".", "okay.", "uh", "um", "hmm"}

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ----------------------------------------------------------------------------
# Modes: who the skull is, how it sounds and which eyes it shows
# ----------------------------------------------------------------------------
@dataclass
class Mode:
    name: str
    prompt: str
    greetings: list
    goodbyes: list
    switch_line: str          # said when switching into this mode
    didnt_hear: str
    error_line: str           # said when Claude can't be reached
    voice: str
    rate: int
    pitch: float              # 1.0 = natural; <1 deeper
    look: str                 # eye set on the ESP32 (firmware/skull_esp32/eye_sets.h)
    clarity: bool = False     # run the voice through clarify() before playing it


SKULL = Mode("skull", SYSTEM_PROMPT, GREETINGS, GOODBYES,
             switch_line="Bwahaha! The master of this house has returned!",
             didnt_hear="Speak up, mortal! I cannot hear you over the screams.",
             error_line="My powers falter! Ask me again, mortal.",
             voice=SAY_VOICE, rate=SAY_RATE, pitch=PITCH_DROP, look="glow", clarity=CLARITY)
PRESENTER = Mode("presenter", PRESENTER_PROMPT, PRESENTER_GREETINGS, PRESENTER_GOODBYES,
                 switch_line="Presenter mode! Hello, I'm Bob. I'm a talking skull, "
                             "and I'd love to tell you how I was built. What would you like to know?",
                 didnt_hear="Sorry, I didn't catch that. Could you say it again a little louder?",
                 error_line="Oops, I've lost my train of thought. Could you ask me that again?",
                 voice=None, rate=PRESENTER_RATE, pitch=PRESENTER_PITCH, look="hazel")  # voice picked at startup
MODES = {m.name: m for m in (SKULL, PRESENTER)}


def mode_command(text):
    """The mode a spoken command asks for ("switch to presenter mode"), or None."""
    t = re.sub(r"[^a-z' ]+", " ", text.lower())
    for name, rx in MODE_COMMANDS.items():
        if rx.search(t):
            return name
    return None


def british_voices():
    """Names of the en_GB voices installed, from `say -v '?'`."""
    out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    names = []
    for line in out.splitlines():
        m = re.match(r"^(.+?)\s+(en[_-]GB)\s+#", line)
        if m:
            names.append(m.group(1).strip())
    return names


def pick_british_voice(preferred):
    """The first installed voice from `preferred`, else any British voice, else None."""
    installed = british_voices()
    for v in preferred:
        if v in installed:
            return v
    return installed[0] if installed else None


# ----------------------------------------------------------------------------
# Link to the ESP32 (serial, UDP, or nothing)
# ----------------------------------------------------------------------------
class Link:
    def __init__(self, mode, port=None, baud=115200, esp_ip=None, udp_port=4210):
        self.mode = mode
        self.presence = threading.Event()
        self.manual = False            # True when the last trigger came from the keyboard
        self._serial = None
        self._sock = None
        self._esp_addr = (esp_ip, udp_port) if esp_ip else None
        self.udp_port = udp_port
        self._last_jaw = None
        if mode == "serial":
            import serial  # pyserial
            self._serial = serial.Serial(port, baud, timeout=0.1)
            log(f"Serial link open on {port}")
            threading.Thread(target=self._read_serial, daemon=True).start()
        elif mode == "udp":
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.bind(("0.0.0.0", udp_port))   # ESP32 sends PRESENCE to this port
            threading.Thread(target=self._read_udp, daemon=True).start()
        if mode != "off":   # Enter always fakes a visitor, handy for testing even with the ESP32 connected
            threading.Thread(target=self._read_keyboard, daemon=True).start()
        # mode "off": no link at all (used by --text, which reads the keyboard itself)

    def send(self, msg):
        data = (msg + "\n").encode()
        try:
            if self._serial:
                self._serial.write(data)
            elif self._sock and self._esp_addr:
                self._sock.sendto(data, self._esp_addr)
        except Exception as e:
            log("link send failed:", e)

    def jaw(self, value):
        value = int(max(0, min(255, value)))
        if value != self._last_jaw:
            self._last_jaw = value
            self.send(f"JAW {value}")

    def _handle(self, line):
        line = line.strip().upper()
        if line:
            log("ESP32:", line)
        if line == "PRESENCE 1":
            self.presence.set()
        elif line == "PRESENCE 0":
            self.presence.clear()

    def _read_serial(self):
        buf = b""
        start = time.time()
        got_any = warned = False
        while True:
            if not got_any and not warned and time.time() - start > 5:
                warned = True
                log("WARNING: nothing received from the ESP32 in 5 s. Wrong --port, Serial Monitor still open, "
                    "or USB CDC On Boot disabled?")
            try:
                chunk = self._serial.read(64)
                got_any = got_any or bool(chunk)
                buf += chunk
            except Exception as e:
                log("serial read failed:", e)
                time.sleep(1)
                continue
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                self._handle(line.decode(errors="ignore"))

    def _read_udp(self):
        while True:
            data, addr = self._sock.recvfrom(256)
            if self._esp_addr is None:         # no --esp-ip given: reply to whoever talks to us
                self._esp_addr = (addr[0], self.udp_port)
            for line in data.decode(errors="ignore").splitlines():
                self._handle(line)

    def _read_keyboard(self):
        print("Press Enter to fake someone walking up.", flush=True)
        for _ in sys.stdin:
            self.manual = True
            self.presence.set()


# ----------------------------------------------------------------------------
# Speech to text: mic + WebRTC VAD + Whisper on MLX
# ----------------------------------------------------------------------------
class Ears:
    def __init__(self, device=None):
        import webrtcvad
        import mlx_whisper
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self.whisper = mlx_whisper
        self.device = device
        log("Loading Whisper model (first run downloads it)...")
        self.whisper.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), path_or_hf_repo=WHISPER_MODEL)
        log("Whisper ready.")

    def record(self, timeout=LISTEN_TIMEOUT):
        """Wait up to `timeout` s for speech, then record until END_SILENCE of quiet. Returns float32 audio or None.

        A frame counts as speech only if the VAD says so AND it is clearly louder than the background
        (tracked continuously), so crowd noise, music or wind doesn't keep the recording going."""
        q = queue.Queue()

        def cb(indata, frames, t, status):
            q.put(bytes(indata))

        pre_roll = deque(maxlen=10)          # keep ~300 ms before speech starts
        voiced_run = 0
        silence_run = 0
        speaking = False
        frames = []
        start = time.time()
        speech_start = None
        noise = getattr(self, "_noise", 300.0)   # background RMS, carried between turns
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=FRAME_SAMPLES, channels=1,
                               dtype="int16", device=self.device, callback=cb):
            while True:
                try:
                    frame = q.get(timeout=0.5)
                except queue.Empty:
                    continue
                if len(frame) != FRAME_SAMPLES * 2:
                    continue
                rms = float(np.sqrt(np.mean(np.frombuffer(frame, dtype=np.int16).astype(np.float32) ** 2)))
                loud = rms > max(noise * SPEECH_OVER_NOISE, 150.0)
                is_speech = loud and self.vad.is_speech(frame, SAMPLE_RATE)
                if not is_speech:                    # learn the background from non-speech frames
                    noise = 0.95 * noise + 0.05 * rms if rms < noise * 3 else noise
                if not speaking:
                    pre_roll.append(frame)
                    voiced_run = voiced_run + 1 if is_speech else 0
                    if voiced_run >= 5:          # ~150 ms of speech starts a recording
                        speaking = True
                        speech_start = time.time()
                        frames.extend(pre_roll)
                    elif time.time() - start > timeout:
                        self._noise = noise
                        return None
                else:
                    frames.append(frame)
                    silence_run = 0 if is_speech else silence_run + 1
                    if silence_run * FRAME_MS / 1000 >= END_SILENCE:
                        why = "pause"
                        break
                    if len(frames) * FRAME_MS / 1000 >= MAX_UTTERANCE:
                        why = "max length - background noise may be too loud"
                        break
        self._noise = noise
        log(f"recorded {time.time() - speech_start:.1f}s, ended by {why} (background level {noise:.0f})")
        audio = np.frombuffer(b"".join(frames), dtype=np.int16).astype(np.float32) / 32768.0
        return audio

    def transcribe(self, audio):
        result = self.whisper.transcribe(audio, path_or_hf_repo=WHISPER_MODEL, language="en",
                                         condition_on_previous_text=False, temperature=0.0)
        text = result.get("text", "").strip()
        return None if text.lower() in HALLUCINATIONS else text


# ----------------------------------------------------------------------------
# Text to speech: macOS `say`, deepened, played with jaw sync
# ----------------------------------------------------------------------------
class Mouth:
    def __init__(self, link, device=None, mode=SKULL):
        self.link = link
        self.device = device
        self.mode = mode           # voice, rate and pitch come from the current mode
        self.tmpdir = tempfile.mkdtemp(prefix="skull_")
        self._n = 0

    def synth(self, text):
        """Render text to (samples to play, sample_rate, samples for the jaw), all float32."""
        self._n += 1
        path = os.path.join(self.tmpdir, f"s{self._n}.wav")
        m = self.mode
        subprocess.run(["say", "-v", m.voice, "-r", str(m.rate), "-o", path,
                        "--data-format=LEI16@22050", text], check=True)
        with wave.open(path, "rb") as w:
            sr = w.getframerate()
            raw = w.readframes(w.getnframes())
        os.remove(path)
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        speech = deepen(audio, m.pitch)
        # play the cleaned-up audio, but drive the jaw from the original: compression flattens the
        # loudness dips between syllables that the jaw sync looks for
        return (clarify(speech, sr) if m.clarity else speech), sr, speech

    def play(self, audio, sr, jaw_audio=None):
        env = jaw_envelope(audio if jaw_audio is None else jaw_audio, sr, JAW_FPS)
        audio, sr = self._fit_device(audio, sr)
        stop = threading.Event()
        t0 = [None]
        offset = [0.0]       # seconds to add to the clock: the lead, minus the time the sound spends in the output buffer

        def jaw_loop():
            while t0[0] is None and not stop.is_set():
                time.sleep(0.002)
            while not stop.is_set():
                i = int((time.time() - t0[0] + offset[0]) * JAW_FPS)
                if i >= len(env):
                    break
                if i >= 0:
                    self.link.jaw(env[i])
                time.sleep(1 / JAW_FPS / 2)
            self.link.jaw(0)

        th = threading.Thread(target=jaw_loop, daemon=True)
        th.start()
        sd.play(audio, sr, device=self.device, latency="low")
        try:
            out_latency = float(sd.get_stream().latency)
        except Exception:
            out_latency = 0.0
        if not hasattr(self, "_latency_logged"):
            self._latency_logged = True
            log(f"Audio output latency {out_latency * 1000:.0f} ms, jaw lead {JAW_LEAD_MS} ms")
        offset[0] = JAW_LEAD_MS / 1000 - out_latency
        t0[0] = time.time()
        sd.wait()
        stop.set()
        th.join()


    def _fit_device(self, audio, sr):
        """Resample to the output device's own rate (USB mic arrays are often 16 kHz only)."""
        if not hasattr(self, "_dev_sr"):
            info = sd.query_devices(self.device, "output")
            self._dev_sr = int(info["default_samplerate"])
            self._dev_ch = max(1, min(2, info["max_output_channels"]))
            log(f"Audio out: {info['name']} @ {self._dev_sr} Hz, {self._dev_ch} ch")
        if sr != self._dev_sr:
            n_out = int(len(audio) * self._dev_sr / sr)
            audio = np.interp(np.linspace(0, len(audio) - 1, n_out), np.arange(len(audio)), audio).astype(np.float32)
        if self._dev_ch == 2:
            audio = np.column_stack([audio, audio])      # same sound on left and right
        return audio, self._dev_sr


def deepen(audio, factor):
    """Cheap pitch drop by resampling: stretches the clip so it plays lower and slower."""
    if factor >= 0.999:
        return audio
    n_out = int(len(audio) / factor)
    x_old = np.arange(len(audio))
    x_new = np.linspace(0, len(audio) - 1, n_out)
    return np.interp(x_new, x_old, audio).astype(np.float32)


def clarify(audio, sr, presence_hz=3000.0, q=0.8, thresh_db=-24.0, ratio=3.0, peak=0.89):
    """Make speech carry on a small speaker: cut the bass it can't play, lift the consonant band,
    even out the level with a gentle compressor, then play the loudest part just under full scale.
    About 20 ms per sentence."""
    from scipy.signal import butter, lfilter, sosfilt

    def smooth(x, seconds):
        n = max(1, int(sr * seconds))
        return np.convolve(x, np.ones(n) / n, mode="same")

    x = sosfilt(butter(2, CLARITY_HIGHPASS_HZ, "highpass", fs=sr, output="sos"), audio)
    # peaking EQ (RBJ audio EQ cookbook) centered on the consonant band
    a_ = 10 ** (CLARITY_PRESENCE_DB / 40)
    w0 = 2 * np.pi * presence_hz / sr
    alpha = np.sin(w0) / (2 * q)
    b = np.array([1 + alpha * a_, -2 * np.cos(w0), 1 - alpha * a_])
    a = np.array([1 + alpha / a_, -2 * np.cos(w0), 1 - alpha / a_])
    x = lfilter(b / a[0], a / a[0], x)
    # compressor: 10 ms RMS envelope, anything more than thresh_db below the peak passes untouched
    env_db = 10 * np.log10(smooth(x * x, 0.010) + 1e-10)
    over = np.maximum(0.0, env_db - (20 * np.log10(np.abs(x).max() + 1e-9) + thresh_db))
    x = x * smooth(10 ** (-over * (1 - 1 / ratio) / 20), 0.025)
    return (x * (peak / (np.abs(x).max() + 1e-9))).astype(np.float32)


def speech_band(audio, sr, lo=250.0, hi=3500.0):
    """Keep only the voice band, so hiss and low rumble don't move the jaw.
    Zero-padded so the FFT filter can't wrap the start of the clip around into the end."""
    pad = int(sr * 0.2)
    x = np.concatenate([np.zeros(pad, np.float32), audio, np.zeros(pad, np.float32)])
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1.0 / sr)
    spec[(freqs < lo) | (freqs > hi)] = 0
    return np.fft.irfft(spec, n=len(x))[pad:pad + len(audio)].astype(np.float32)


def find_syllables(db, delta):
    """Peak/valley finder with hysteresis (Billauer's peakdet): a peak counts only once the level
    drops `delta` dB below it, a valley only once it rises `delta` dB above it.
    Returns lists of peak and valley indices, alternating."""
    peaks, valleys = [], []
    mx, mn = -np.inf, np.inf
    mx_i = mn_i = 0
    looking_for_peak = True
    for i, v in enumerate(db):
        if v > mx:
            mx, mx_i = v, i
        if v < mn:
            mn, mn_i = v, i
        if looking_for_peak and v < mx - delta:
            peaks.append(mx_i)
            mn, mn_i = v, i
            looking_for_peak = False
        elif not looking_for_peak and v > mn + delta:
            valleys.append(mn_i)
            mx, mx_i = v, i
            looking_for_peak = True
    if looking_for_peak and mx > -np.inf and (not valleys or mx_i > valleys[-1]):
        peaks.append(mx_i)                         # last syllable, still rising at the end
    return peaks, valleys


def jaw_envelope(audio, sr, fps):
    """Jaw positions (0-255, one per 1/fps s) with one open-close per syllable.

    Loudness alone merges fast syllables into one long "open", so instead this finds each
    syllable's loudness peak and the dip between syllables, then opens the jaw at every peak
    (wider for louder syllables) and closes it at every dip and in pauses."""
    hop = max(1, sr // 100)                        # analyse at 100 frames/s
    voice = speech_band(audio, sr)
    n = int(np.ceil(len(voice) / hop))
    padded = np.zeros(n * hop, dtype=np.float32)
    padded[:len(voice)] = voice
    rms = np.sqrt(np.mean(padded.reshape(n, hop) ** 2, axis=1))
    rms = np.convolve(rms, np.ones(3) / 3, mode="same")         # 30 ms smoothing
    out_n = int(np.ceil(len(audio) / sr * fps))
    if rms.max() <= 0:
        return np.zeros(out_n, dtype=np.int32)

    db = 20 * np.log10(rms + 1e-9)
    db -= np.percentile(db[rms > 0], 95)                        # 0 dB = the loud parts of this clip
    db = np.maximum(db, JAW_GATE_DB - 10)
    loud = db > JAW_GATE_DB

    peaks, valleys = find_syllables(db, JAW_SYLLABLE_DB)
    peaks = [p for p in peaks if loud[p]]

    # key points: closed at valleys and silences, open at peaks
    t_key, v_key = [0.0], [0.0]
    for p in peaks:
        before = [v for v in valleys if v < p]
        after = [v for v in valleys if v > p]
        start = before[-1] if before else max(0, p - 12)
        end = after[0] if after else min(n - 1, p + 12)
        # don't hold the jaw open through silence on either side of the syllable
        while start < p and not loud[start]:
            start += 1
        while end > p and not loud[end]:
            end -= 1
        start, end = max(start - 2, 0), min(end + 2, n - 1)
        strength = np.clip((db[p] - JAW_GATE_DB) / -JAW_GATE_DB, 0, 1)
        opening = JAW_MIN_OPEN + (JAW_MAX_OPEN - JAW_MIN_OPEN) * strength
        t_key += [start, p, end]
        v_key += [0.0, opening, 0.0]
    t_key.append(n)
    v_key.append(0.0)
    order = np.argsort(t_key, kind="stable")
    t_key = np.asarray(t_key, dtype=float)[order] / 100.0      # analysis frames -> seconds
    v_key = np.asarray(v_key)[order]

    t_out = np.arange(out_n) / fps
    jaw = np.interp(t_out, t_key, v_key)
    return np.clip(jaw * 255, 0, 255).astype(np.int32)


# ----------------------------------------------------------------------------
# Claude, streamed and spoken sentence by sentence
# ----------------------------------------------------------------------------
SENTENCE_END = re.compile(r"[.!?…]+[\"')\]]*\s+")


def split_sentences(buffer):
    """Pull finished sentences (end punctuation + whitespace) off the front of `buffer`.
    Returns (sentences, remainder). The last sentence stays in the remainder until more text arrives."""
    out = []
    while (m := SENTENCE_END.search(buffer)):
        s = buffer[:m.end()].strip()
        buffer = buffer[m.end():]
        if s:
            out.append(s)
    return out, buffer


def clean_for_speech(text):
    text = re.sub(r"\*[^*]*\*", "", text)        # drop *stage directions*
    text = re.sub(r"[_#`~]", "", text)
    return re.sub(r"\s{2,}", " ", text).strip()


class Brain:
    def __init__(self, mode=SKULL):
        import anthropic
        self.client = anthropic.Anthropic()       # reads ANTHROPIC_API_KEY
        self.mode = mode                          # persona (system prompt) comes from the current mode
        self.history = []

    def reset(self):
        self.history = []

    def reply_stream(self, user_text):
        """Yields sentences as Claude writes them."""
        self.history.append({"role": "user", "content": user_text})
        full = ""
        buf = ""
        try:
            with self.client.messages.stream(model=CLAUDE_MODEL, max_tokens=200, system=self.mode.prompt,
                                             messages=self.history) as stream:
                for chunk in stream.text_stream:
                    full += chunk
                    buf += chunk
                    sentences, buf = split_sentences(buf)
                    for s in sentences:
                        s = clean_for_speech(s)
                        if s:
                            yield s
        except Exception as e:
            log("Claude error:", e)
            self.history.pop()
            yield self.mode.error_line
            return
        tail = clean_for_speech(buf)
        if tail:
            yield tail
        self.history.append({"role": "assistant", "content": full.strip() or "..."})


# ----------------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------------
def speak_stream(sentences, mouth, link):
    """Synthesize the next sentence while the current one plays, so there are no gaps."""
    link.send("STATE SPEAK")
    q = queue.Queue(maxsize=2)

    def producer():
        for s in sentences:
            log("SKULL:", s)
            q.put(mouth.synth(s))
        q.put(None)

    threading.Thread(target=producer, daemon=True).start()
    while (item := q.get()) is not None:
        mouth.play(*item)


def set_mode(mode, mouth, brain, link):
    """Switch persona, voice and eyes together. Returns the new mode."""
    mouth.mode = brain.mode = mode
    brain.reset()                        # a new persona starts a fresh conversation
    link.send(f"LOOK {mode.look}")
    log(f"Mode: {mode.name} (voice {mode.voice}, eyes {mode.look})")
    return mode


def run(args):
    if PRESENTER.voice is None:
        PRESENTER.voice = pick_british_voice(PRESENTER_VOICES)
        if PRESENTER.voice is None:
            log("WARNING: no British voice installed, presenter mode will use", SKULL.voice)
            PRESENTER.voice = SKULL.voice
    link = Link("off" if args.text else args.link, port=args.port, esp_ip=args.esp_ip, udp_port=args.udp_port)
    mouth = Mouth(link, device=args.out_device)
    brain = Brain()
    ears = None if args.text else Ears(device=args.in_device)

    link.send("EYES 0")
    link.send("STATE IDLE")
    mode = set_mode(MODES[args.mode], mouth, brain, link)
    log(f"Link mode: {'off (text mode)' if args.text else args.link}")
    log('Say "switch to presenter mode" or "switch to skull mode" to change modes.')
    log("Ready. Waiting for a visitor.")
    while True:
        if args.text:
            input("\n[Enter] = someone walks up ")
        else:
            link.presence.wait()
            if link.manual:
                link.presence.clear()     # keyboard trigger is one-shot
        log("Visitor!")
        brain.reset()
        link.send(f"LOOK {mode.look}")   # again, in case the ESP32 restarted since
        link.send("EYES 1")
        speak_stream([random.choice(mode.greetings)], mouth, link)

        misses = 0
        for turn in range(MAX_TURNS):
            if not args.text and not link.manual and not link.presence.is_set():
                log("(visitor walked away)")
                break
            link.send("STATE LISTEN")
            if args.text:
                heard = input("you> ").strip() or None
            else:
                audio = ears.record()
                if audio is None:
                    log("(no speech)")
                    break
                link.send("STATE THINK")
                t = time.time()
                heard = ears.transcribe(audio)
                log(f"HEARD ({time.time() - t:.1f}s):", heard)
            if not heard:
                misses += 1
                if misses <= 2:
                    speak_stream([mode.didnt_hear], mouth, link)
                    continue
                break
            misses = 0
            wanted = mode_command(heard)
            if wanted:                       # "switch to presenter mode" etc. never goes to Claude
                if wanted == mode.name:
                    speak_stream([f"I'm already in {wanted} mode."], mouth, link)
                else:
                    mode = set_mode(MODES[wanted], mouth, brain, link)
                    speak_stream([mode.switch_line], mouth, link)
                continue
            link.send("STATE THINK")
            speak_stream(brain.reply_stream(heard), mouth, link)

        speak_stream([random.choice(mode.goodbyes)], mouth, link)
        link.send("STATE IDLE")
        link.send("EYES 0")
        # wait for the group to leave so the same people don't retrigger it right away
        cooldown = time.time() + args.cooldown
        if link.manual:
            link.manual = False
            link.presence.clear()
        while time.time() < cooldown or link.presence.is_set():
            time.sleep(0.25)
            if time.time() > cooldown + REWAKE_SECS:   # same person still there: greet them again
                break
        log("Waiting for the next visitor.")


def device_arg(v):
    return int(v) if v.isdigit() else v     # sounddevice matches names by substring


def main():
    p = argparse.ArgumentParser(description="Talking skull: STT -> Claude -> TTS with jaw sync")
    p.add_argument("--list-devices", action="store_true", help="print audio devices and exit")
    p.add_argument("--in-device", type=device_arg, default=None,
                   help="mic: device number or part of its name, e.g. ReSpeaker (see --list-devices)")
    p.add_argument("--out-device", type=device_arg, default=None,
                   help="speaker: device number or part of its name, e.g. ReSpeaker")
    p.add_argument("--link", choices=["none", "serial", "udp"], default="none")
    p.add_argument("--port", help="serial port, e.g. /dev/cu.usbmodem1101 (ls /dev/cu.*)")
    p.add_argument("--esp-ip", help="ESP32 IP address for UDP mode")
    p.add_argument("--udp-port", type=int, default=4210)
    p.add_argument("--text", action="store_true", help="type instead of using the mic")
    p.add_argument("--cooldown", type=float, default=5.0, help="seconds before the next visitor can trigger it")
    p.add_argument("--mode", choices=list(MODES), default="skull",
                   help='mode at startup; say "switch to presenter mode" / "switch to skull mode" to change it')
    args = p.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY first:  export ANTHROPIC_API_KEY=sk-ant-...")
    if args.link == "serial" and not args.port:
        sys.exit("--link serial needs --port (try: ls /dev/cu.*)")
    try:
        run(args)
    except KeyboardInterrupt:
        print("\nBye.")


if __name__ == "__main__":
    main()
