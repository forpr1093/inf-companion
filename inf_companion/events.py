"""Event bus: any thread publishes, websocket handlers on the asyncio loop subscribe.

`publish` never blocks the caller. That matters most for the input thread: a slow or
stalled browser tab must never delay controller input. Each subscriber has a bounded
queue, and when it's full the oldest event is dropped.
"""

import asyncio
import threading
import time
from typing import Any


def make_event(type: str, **fields: Any) -> dict:
    """Build a wire event. `at` is epoch ms, used by the page's latency overlay."""
    return {"type": type, "at": time.time() * 1000, **fields}


class Subscription:
    def __init__(self, bus: "EventBus", maxsize: int):
        self._bus = bus
        self._queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=maxsize)
        self.closed = False

    def _offer(self, event: dict) -> None:
        if self.closed:
            return
        if self._queue.full():
            self._queue.get_nowait()
        self._queue.put_nowait(event)

    def pending(self) -> int:
        return self._queue.qsize()

    def close(self) -> None:
        self.closed = True
        self._bus._remove(self)

    def __aiter__(self) -> "Subscription":
        return self

    async def __anext__(self) -> dict:
        return await self._queue.get()


class EventBus:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subs: list[Subscription] = []
        self._lock = threading.Lock()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, maxsize: int = 256) -> Subscription:
        sub = Subscription(self, maxsize)
        with self._lock:
            self._subs.append(sub)
        return sub

    def _remove(self, sub: Subscription) -> None:
        with self._lock:
            if sub in self._subs:
                self._subs.remove(sub)

    def publish(self, event: dict) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(self._fanout, event)
        except RuntimeError:  # loop shut down between the check and the call
            pass

    def _fanout(self, event: dict) -> None:
        with self._lock:
            subs = list(self._subs)
        for sub in subs:
            sub._offer(event)
