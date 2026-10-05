"""aiohttp server: the control page at / and the WebSocket at /ws.

Every message from the phone goes through the router. The robot sends a
`status` message on connect and after every change, to every open page.
"""

import json
import logging
from pathlib import Path

from aiohttp import WSMsgType, web

from robot.router import BadMessage, Router

log = logging.getLogger(__name__)

STATIC = Path(__file__).resolve().parent / "static"
ROUTER = web.AppKey("router", Router)
CLIENTS = web.AppKey("clients", set)


async def index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


async def websocket(request: web.Request) -> web.WebSocketResponse:
    router, clients = request.app[ROUTER], request.app[CLIENTS]
    ws = web.WebSocketResponse(heartbeat=5)
    await ws.prepare(request)
    clients.add(ws)
    log.info("phone connected from %s (%d open)", request.remote, len(clients))
    await ws.send_json(router.status())
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            try:
                await router.handle(json.loads(msg.data))
            except (BadMessage, json.JSONDecodeError) as e:
                await ws.send_json({"type": "error", "error": str(e)})
    finally:
        clients.discard(ws)
        log.info("phone disconnected from %s (%d open)", request.remote, len(clients))
        router.stop()
        await broadcast(request.app)
    return ws


async def broadcast(app: web.Application) -> None:
    status = app[ROUTER].status()
    for ws in list(app[CLIENTS]):
        try:
            await ws.send_json(status)
        except (ConnectionResetError, RuntimeError):
            pass  # closing; its handler cleans up


def make_app(router: Router) -> web.Application:
    app = web.Application()
    app[ROUTER] = router
    app[CLIENTS] = set()
    router.on_change = lambda: broadcast(app)
    app.router.add_get("/", index)
    app.router.add_get("/ws", websocket)
    return app
