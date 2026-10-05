import pytest

from robot import config
from robot.router import Router
from robot.web.server import ROUTER, make_app


@pytest.fixture
async def client(aiohttp_client, monkeypatch):
    monkeypatch.setenv("ROBOT_FAKE_HW", "1")
    router = Router(config.load())
    return await aiohttp_client(make_app(router))


async def test_index_serves_the_page(client):
    resp = await client.get("/")
    assert resp.status == 200
    assert "<title>Robot Buddy</title>" in await resp.text()


async def test_ws_sends_status_on_connect(client):
    async with client.ws_connect("/ws") as ws:
        status = await ws.receive_json()
        assert status["type"] == "status"
        assert status["name"] == config.load()["robot"]["buddy_name"]
        assert "ready" in status["phrases"]


async def test_drive_is_echoed_in_status(client):
    async with client.ws_connect("/ws") as ws:
        await ws.receive_json()
        await ws.send_json({"type": "drive", "throttle": 0.3, "turn": -0.4})
        status = await ws.receive_json()
        assert status["drive"] == {"throttle": 0.3, "turn": -0.4}


async def test_status_goes_to_every_page(client):
    async with client.ws_connect("/ws") as a, client.ws_connect("/ws") as b:
        await a.receive_json()
        await b.receive_json()
        await a.send_json({"type": "drive", "throttle": 1, "turn": 0})
        assert (await b.receive_json())["drive"]["throttle"] == 1


async def test_bad_message_gets_an_error(client):
    async with client.ws_connect("/ws") as ws:
        await ws.receive_json()
        await ws.send_str("not json")
        assert (await ws.receive_json())["type"] == "error"
        await ws.send_json({"type": "drive", "throttle": 9, "turn": 0})
        assert "between -1 and 1" in (await ws.receive_json())["error"]


async def test_disconnect_stops(client):
    router = client.app[ROUTER]
    async with client.ws_connect("/ws") as ws:
        await ws.receive_json()
        await ws.send_json({"type": "drive", "throttle": 0.5, "turn": 0})
        await ws.receive_json()
    async with client.ws_connect("/ws") as ws:
        assert (await ws.receive_json())["drive"] == {"throttle": 0.0, "turn": 0.0}
    assert router.drive_cmd == {"throttle": 0.0, "turn": 0.0}
