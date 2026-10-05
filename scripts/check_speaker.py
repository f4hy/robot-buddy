"""M2 bench test: play a two-tone beep, then the robot introduces itself.

On the Pi:     python3 scripts/check_speaker.py
On a laptop:   ROBOT_FAKE_HW=1 uv run python scripts/check_speaker.py
"""

import io
import math
import os
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from robot import config  # noqa: E402
from robot.hardware import audio  # noqa: E402

RATE = 48000
CARD = "sndrpihifiberry"


def beep_wav(volume: float, tones=((440, 0.4), (880, 0.4))) -> bytes:
    """A mono 16-bit WAV of the given (frequency, seconds) tones, with short fades."""
    frames = bytearray()
    fade = int(RATE * 0.01)
    for freq, seconds in tones:
        n = int(RATE * seconds)
        for i in range(n):
            ramp = min(1.0, i / fade, (n - i) / fade)
            sample = volume * ramp * math.sin(2 * math.pi * freq * i / RATE)
            frames += struct.pack("<h", int(sample * 32767))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def main() -> None:
    cfg = config.load()
    device, volume = cfg["audio"]["device"], cfg["audio"]["volume"]
    wav = beep_wav(volume)
    phrase = audio.phrases(cfg["robot"])["intro"]

    if os.environ.get("ROBOT_FAKE_HW"):
        print(f"fake: would play a {len(wav)}-byte beep on {device}")
        print(f"fake: would say {phrase!r} at espeak-ng volume {int(volume * 200)}")
        return

    if not shutil.which("aplay"):
        sys.exit("aplay not found: run  bash ~/robot_buddy/scripts/provision.sh speaker")
    cards = subprocess.run(["aplay", "-l"], capture_output=True, text=True).stdout
    if CARD not in cards:
        sys.exit(
            f"No {CARD} sound card. Run  bash ~/robot_buddy/scripts/provision.sh speaker"
            "  then  sudo reboot.\naplay -l says:\n" + (cards or "(no cards)")
        )

    print("beep (low, then high)")
    subprocess.run(["aplay", "-q", "-D", device, "-"], input=wav, check=True)

    if shutil.which("espeak-ng"):
        print(f"say: {phrase}")
        audio.say(phrase, cfg["audio"])
    else:
        print("espeak-ng not installed; skipping speech")

    print("Heard a beep and the sentence? Change audio.volume in config/robot.yaml if needed.")


if __name__ == "__main__":
    main()
