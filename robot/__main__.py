"""Entry point: python3 -m robot.

Logs a hello line, then says hello through the speaker once ready.
"""

import logging
import socket
import subprocess

from robot import config
from robot.hardware import audio


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = config.load()
    logging.info("hello from %s on %s", cfg["robot"]["name"], socket.gethostname())
    try:
        audio.say(audio.phrases(cfg["robot"])["ready"], cfg["audio"])
    except (OSError, subprocess.CalledProcessError) as e:
        logging.warning("could not say hello: %s", e)


if __name__ == "__main__":
    main()
