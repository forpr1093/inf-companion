"""HTTP + websocket server: the built page, a small REST API, and the event stream."""

import asyncio
import contextlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

import inf_companion
from inf_companion.events import EventBus, make_event
from inf_companion.input.model import TARGETS, DeviceInfo
from inf_companion.storage.db import BindingsRepo, SettingsRepo

GIF_MAX_BYTES = 20 * 1024 * 1024
GIF_NAME = "loop.gif"


class InputLike(Protocol):
    def devices(self) -> list[DeviceInfo]: ...
    def counts(self) -> dict[str, int]: ...
    def handle_client(self, msg: dict) -> None: ...


@dataclass
class AppContext:
    bus: EventBus
    settings: SettingsRepo
    bindings: BindingsRepo
    data_dir: Path
    static_dir: Path | None
    input: InputLike | None = None
    gif_version: int = field(default=0)


def create_app(ctx: AppContext) -> Starlette:
    gif_path = ctx.data_dir / GIF_NAME

    def hello() -> dict:
        return make_event(
            "hello",
            version=inf_companion.__version__,
            settings=ctx.settings.get_all(),
            devices=[d.to_json() for d in ctx.input.devices()] if ctx.input else [],
            bindings={g: b.to_json() for g, b in ctx.bindings.all().items()},
            has_gif=gif_path.is_file(),
            counts=ctx.input.counts() if ctx.input else {t: 0 for t in TARGETS},
        )

    async def get_settings(request: Request) -> Response:
        return JSONResponse(ctx.settings.get_all())

    async def patch_settings(request: Request) -> Response:
        try:
            patch = json.loads(await request.body())
            settings = ctx.settings.update(patch)
        except (ValueError, TypeError) as e:  # JSONDecodeError is a ValueError
            return JSONResponse({"error": str(e)}, status_code=400)
        ctx.bus.publish(make_event("settings", settings=settings))
        return JSONResponse(settings)

    async def get_bindings(request: Request) -> Response:
        return JSONResponse({g: b.to_json() for g, b in ctx.bindings.all().items()})

    async def put_gif(request: Request) -> Response:
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > GIF_MAX_BYTES:
                return JSONResponse({"error": "GIF is larger than 20 MB"}, status_code=413)
        if not body:
            return JSONResponse({"error": "empty upload"}, status_code=400)
        if not body.startswith((b"GIF87a", b"GIF89a")):
            return JSONResponse({"error": "not a GIF file"}, status_code=415)
        fd, tmp = tempfile.mkstemp(dir=ctx.data_dir, suffix=".gif.tmp")
        with os.fdopen(fd, "wb") as f:
            f.write(body)
        os.replace(tmp, gif_path)
        ctx.gif_version += 1
        ctx.bus.publish(make_event("gif", version=ctx.gif_version))
        return Response(status_code=204)

    async def get_gif(request: Request) -> Response:
        if not gif_path.is_file():
            return JSONResponse({"error": "no GIF uploaded"}, status_code=404)
        return FileResponse(gif_path, media_type="image/gif", headers={"Cache-Control": "no-store"})

    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        sub = ctx.bus.subscribe()
        try:
            await ws.send_json(hello())

            async def pump() -> None:
                async for event in sub:
                    await ws.send_json(event)

            sender = asyncio.create_task(pump())
            try:
                while True:
                    msg = await ws.receive_json()
                    if not isinstance(msg, dict):
                        continue
                    if ctx.input:
                        ctx.input.handle_client(msg)
                    elif msg.get("type") == "counts_reset":
                        # No controller reading (--no-input): counts are always zero.
                        ctx.bus.publish(make_event("counts", counts={t: 0 for t in TARGETS}))
            except (WebSocketDisconnect, json.JSONDecodeError, RuntimeError):
                pass
            finally:
                sender.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await sender
        finally:
            sub.close()

    async def not_built(request: Request) -> Response:
        return PlainTextResponse("inf-companion: web page not built; run npm run build in web/")

    routes = [
        Route("/api/settings", get_settings, methods=["GET"]),
        Route("/api/settings", patch_settings, methods=["PATCH"]),
        Route("/api/bindings", get_bindings, methods=["GET"]),
        Route("/api/gif", get_gif, methods=["GET"]),
        Route("/api/gif", put_gif, methods=["PUT"]),
        WebSocketRoute("/ws", ws_endpoint),
    ]
    if ctx.static_dir is not None and ctx.static_dir.is_dir():
        routes.append(Mount("/", StaticFiles(directory=ctx.static_dir, html=True)))
    else:
        routes.append(Route("/", not_built))

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        ctx.bus.bind_loop(asyncio.get_running_loop())
        yield

    return Starlette(routes=routes, lifespan=lifespan)
