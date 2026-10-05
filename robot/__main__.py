"""Entry point: python3 -m robot.

Starts the phone control page, then says hello through the speaker.
"""

import asyncio
import logging
import os
import signal
import socket

from aiohttp import web

from robot import config
from robot.router import Router
from robot.web.server import make_app


def lan_ip() -> str:
    """The address the phone should use; sends no packets."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.0.2.1", 9))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


async def run() -> None:
    cfg = config.load()
    router = Router(cfg)
    runner = web.AppRunner(make_app(router), access_log=None)
    await runner.setup()
    port = int(os.environ.get("ROBOT_PORT", cfg["robot"]["port"]))
    await web.TCPSite(runner, None, port).start()  # all interfaces, IPv4 and IPv6
    logging.info("hello from %s on %s", cfg["robot"]["name"], socket.gethostname())
    suffix = "" if port == 80 else f":{port}"
    logging.info(
        "phone page: http://%s%s or http://%s%s", socket.gethostname(), suffix, lan_ip(), suffix
    )
    await router.handle({"type": "phrase", "name": "ready"})

    done = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, done.set)
    await done.wait()
    logging.info("shutting down")
    router.stop()
    await runner.cleanup()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run())


if __name__ == "__main__":
    main()
