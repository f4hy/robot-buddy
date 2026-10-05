"""Validates commands from the phone (and later teleop and the brain) and sends
them to the modules.

M3: no motors yet, so `drive` and `stop` are only recorded and logged.
"""

import asyncio
import logging
import math
import subprocess
import time
from collections.abc import Awaitable, Callable
from xml.sax.saxutils import escape

from robot.hardware import audio

log = logging.getLogger(__name__)

MAX_SAY_CHARS = 80
DRIVE_LOG_INTERVAL_S = 1.0  # the joystick sends at 10 Hz; log at most this often


class BadMessage(ValueError):
    """The message is malformed, unknown or out of range."""


def _axis(msg: dict, key: str) -> float:
    value = msg.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise BadMessage(f"{key} must be a number")
    if not -1 <= value <= 1:
        raise BadMessage(f"{key} must be between -1 and 1")
    return float(value)


class Router:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.phrases = audio.phrases(cfg["robot"])
        self.drive_cmd = {"throttle": 0.0, "turn": 0.0}
        self.speaking = False
        self.on_change: Callable[[], Awaitable[None]] | None = None
        self._speech: asyncio.Task | None = None
        self._last_drive_log = 0.0

    def status(self) -> dict:
        return {
            "type": "status",
            "name": self.cfg["robot"]["buddy_name"],
            "phrases": list(self.phrases),
            "drive": self.drive_cmd,
            "motors": False,
            "speaking": self.speaking,
        }

    async def handle(self, msg: object) -> None:
        """Run one command. Raises BadMessage if it is invalid."""
        if not isinstance(msg, dict):
            raise BadMessage("message must be a JSON object")
        kind = msg.get("type")
        if kind == "drive":
            self._drive(_axis(msg, "throttle"), _axis(msg, "turn"))
        elif kind == "stop":
            self.stop()
        elif kind == "say":
            text = msg.get("text")
            if not isinstance(text, str) or not text.strip():
                raise BadMessage("text must be a non-empty string")
            if len(text) > MAX_SAY_CHARS:
                raise BadMessage(f"text is longer than {MAX_SAY_CHARS} characters")
            self._speak(escape(text.strip()))
        elif kind == "phrase":
            name = msg.get("name")
            if name not in self.phrases:
                raise BadMessage(f"unknown phrase {name!r}")
            self._speak(self.phrases[name])
        else:
            raise BadMessage(f"unknown message type {kind!r}")
        await self._changed()

    def stop(self) -> None:
        if self.drive_cmd != {"throttle": 0.0, "turn": 0.0}:
            log.info("stop")
        self.drive_cmd = {"throttle": 0.0, "turn": 0.0}

    def _drive(self, throttle: float, turn: float) -> None:
        self.drive_cmd = {"throttle": throttle, "turn": turn}
        now = time.monotonic()
        if now - self._last_drive_log >= DRIVE_LOG_INTERVAL_S:
            self._last_drive_log = now
            log.info("drive throttle=%+.2f turn=%+.2f (no motors yet)", throttle, turn)

    def _speak(self, text: str) -> None:
        """Start speaking in a worker thread; refuses while already talking."""
        if self.speaking:
            raise BadMessage("still talking, try again in a moment")
        self.speaking = True
        self._speech = asyncio.create_task(self._speak_task(text))

    async def _speak_task(self, text: str) -> None:
        log.info("say: %s", text)
        try:
            await asyncio.to_thread(audio.say, text, self.cfg["audio"])
        except (OSError, subprocess.CalledProcessError) as e:
            log.warning("could not speak: %s", e)
        finally:
            self.speaking = False
            await self._changed()

    async def _changed(self) -> None:
        if self.on_change:
            await self.on_change()
