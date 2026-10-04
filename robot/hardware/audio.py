"""Speech through the I2S amp: espeak-ng renders a WAV, aplay plays it.

Text may contain SSML breaks, e.g. '<break time="700ms"/>' for a pause.
With ROBOT_FAKE_HW=1 nothing is played; the text is logged instead.
"""

import logging
import os
import subprocess
from xml.sax.saxutils import escape

log = logging.getLogger(__name__)

PAUSE = '<break time="700ms"/>'


def phrases(robot_cfg: dict) -> dict[str, str]:
    """The robot's set phrases, filled in with its name and its kid's name."""
    name, kid = escape(robot_cfg["buddy_name"]), escape(robot_cfg["kid_name"])
    return {
        "ready": f"Hello {kid}, I am ready to play. My name is {name}.",
        "intro": f"I am {name}. {PAUSE} What's up with you?",
    }


def say(text: str, audio_cfg: dict) -> None:
    """Speak text on audio_cfg["device"]; blocks until done."""
    volume = int(audio_cfg["volume"] * 200)  # espeak-ng amplitude, 0-200
    if os.environ.get("ROBOT_FAKE_HW"):
        log.info("fake say (volume %d): %s", volume, text)
        return
    speech = subprocess.run(
        ["espeak-ng", "-m", "-a", str(volume), "--stdout", text],
        capture_output=True,
        check=True,
    ).stdout
    subprocess.run(["aplay", "-q", "-D", audio_cfg["device"], "-"], input=speech, check=True)
