"""Entry point: python3 -m robot.

M1: log a hello line so we can see the service run at boot.
"""

import logging
import socket

from robot import config


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = config.load()
    logging.info("hello from %s on %s", cfg["robot"]["name"], socket.gethostname())


if __name__ == "__main__":
    main()
