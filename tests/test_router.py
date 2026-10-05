import asyncio
import threading

import pytest

from robot import config
from robot.hardware import audio
from robot.router import BadMessage, Router


@pytest.fixture
def spoken(monkeypatch):
    """Replace audio.say with a recorder; returns the list of spoken texts."""
    said = []
    monkeypatch.setattr(audio, "say", lambda text, cfg: said.append(text))
    return said


@pytest.fixture
def router():
    return Router(config.load())


async def finish_speech(router):
    while router.speaking:
        await asyncio.sleep(0.01)


async def test_drive_is_recorded(router):
    await router.handle({"type": "drive", "throttle": 0.5, "turn": -1})
    assert router.status()["drive"] == {"throttle": 0.5, "turn": -1.0}
    assert router.status()["motors"] is False


async def test_stop_zeroes_drive(router):
    await router.handle({"type": "drive", "throttle": 0.5, "turn": 0.2})
    await router.handle({"type": "stop"})
    assert router.drive_cmd == {"throttle": 0.0, "turn": 0.0}


@pytest.mark.parametrize(
    "msg",
    [
        {"type": "drive", "throttle": 1.5, "turn": 0},
        {"type": "drive", "throttle": 0, "turn": -2},
        {"type": "drive", "throttle": "1", "turn": 0},
        {"type": "drive", "throttle": True, "turn": 0},
        {"type": "drive", "throttle": float("nan"), "turn": 0},
        {"type": "drive", "turn": 0},
        {"type": "fly"},
        {"type": "say", "text": ""},
        {"type": "say", "text": "x" * 81},
        {"type": "say", "text": 5},
        {"type": "phrase", "name": "nope"},
        ["drive"],
    ],
)
async def test_rejects_bad_messages(router, msg):
    with pytest.raises(BadMessage):
        await router.handle(msg)
    assert router.drive_cmd == {"throttle": 0.0, "turn": 0.0}
    assert not router.speaking


async def test_say_escapes_text_for_ssml(router, spoken):
    await router.handle({"type": "say", "text": "  fish & <chips>  "})
    await finish_speech(router)
    assert spoken == ["fish &amp; &lt;chips&gt;"]


async def test_phrase_speaks_set_phrase(router, spoken):
    await router.handle({"type": "phrase", "name": "intro"})
    await finish_speech(router)
    assert spoken == [router.phrases["intro"]]


async def test_refuses_to_talk_over_itself(router, monkeypatch):
    release = threading.Event()
    monkeypatch.setattr(audio, "say", lambda text, cfg: release.wait(5))
    await router.handle({"type": "say", "text": "first"})
    assert router.status()["speaking"] is True
    with pytest.raises(BadMessage, match="still talking"):
        await router.handle({"type": "say", "text": "second"})
    release.set()
    await finish_speech(router)
    await router.handle({"type": "say", "text": "third"})
    await finish_speech(router)


async def test_speech_failure_is_logged_not_raised(router, monkeypatch, caplog):
    def broken(text, cfg):
        raise OSError("no sound card")

    monkeypatch.setattr(audio, "say", broken)
    await router.handle({"type": "say", "text": "hi"})
    await finish_speech(router)
    assert "no sound card" in caplog.text


async def test_on_change_runs_after_each_command(router, spoken):
    calls = []

    async def changed():
        calls.append(router.status()["speaking"])

    router.on_change = changed
    await router.handle({"type": "drive", "throttle": 0.1, "turn": 0})
    await router.handle({"type": "say", "text": "hi"})
    await finish_speech(router)
    assert calls == [False, True, False]
