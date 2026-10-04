from robot import config
from robot.hardware import audio


def test_phrases_use_names_from_config():
    p = audio.phrases({"buddy_name": "updog", "kid_name": "Rowan"})
    assert p["ready"] == "Hello Rowan, I am ready to play. My name is updog."
    assert p["intro"].startswith("I am updog. <break")


def test_phrases_escape_names_for_ssml():
    p = audio.phrases({"buddy_name": "R&D <bot>", "kid_name": "Rowan"})
    assert "R&amp;D &lt;bot&gt;" in p["ready"]


def test_fake_say_logs_instead_of_playing(monkeypatch, caplog):
    monkeypatch.setenv("ROBOT_FAKE_HW", "1")
    caplog.set_level("INFO")
    audio.say("hi", config.load()["audio"])
    assert "fake say" in caplog.text
