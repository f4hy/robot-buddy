"""Type a line, the robot says it. Empty line or Ctrl-D quits.

On the Pi:     python3 scripts/say.py
On a laptop:   ROBOT_FAKE_HW=1 uv run python scripts/say.py
"""

import logging
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from robot import config  # noqa: E402
from robot.hardware import audio  # noqa: E402


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = config.load()
    name = cfg["robot"]["buddy_name"]
    print(f"Type something for {name} to say. Empty line or Ctrl-D quits.")
    while True:
        try:
            text = input(f"{name}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            break
        try:
            audio.say(escape(text), cfg["audio"])
        except (OSError, subprocess.CalledProcessError) as e:
            print(f"could not say it: {e}")


if __name__ == "__main__":
    main()
