"""Glue between the controller thread, the mapper, the binding flow and the event bus.

`handle_raw`, `handle_devices` and `handle_idle` run on the input thread. `handle_client`
runs on the server's event loop. One short lock keeps them consistent; nothing in here
waits on I/O except saving a finished binding.
"""

import threading
import time
from collections.abc import Callable
from typing import Protocol

from inf_companion.events import make_event
from inf_companion.input.binder import BindingSession
from inf_companion.input.counter import PressCounter
from inf_companion.input.mapper import InputMapper
from inf_companion.input.model import TARGETS, DeviceInfo, KeyEvent, RawEvent
from inf_companion.storage.db import BindingsRepo


class Publisher(Protocol):
    def publish(self, event: dict) -> None: ...


class Source(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...


SourceFactory = Callable[..., Source]


def _default_source_factory(**callbacks) -> Source:
    from inf_companion.input.sdl_source import SdlInputThread

    return SdlInputThread(**callbacks)


class InputService:
    def __init__(self, bus: Publisher, bindings: BindingsRepo, source_factory: SourceFactory | None = None):
        self._bus = bus
        self._repo = bindings
        self._lock = threading.Lock()
        self._mapper = InputMapper(bindings.all())
        self._counter = PressCounter()
        self._session: BindingSession | None = None
        self._devices: list[tuple[str, str]] = []
        factory = source_factory or _default_source_factory
        self._source = factory(on_raw=self.handle_raw, on_devices=self.handle_devices, on_idle=self.handle_idle)

    def start(self) -> None:
        self._source.start()

    def stop(self) -> None:
        self._source.stop()

    # -- queries ------------------------------------------------------------------
    def devices(self) -> list[DeviceInfo]:
        with self._lock:
            return self._device_infos()

    def counts(self) -> dict[str, int]:
        with self._lock:
            return self._counter.snapshot()

    def _device_infos(self) -> list[DeviceInfo]:
        bound = self._repo.all()
        return [DeviceInfo(g, n, g in bound) for g, n in self._devices]

    # -- publishing -----------------------------------------------------------------
    def _emit_keys(self, keys: list[KeyEvent]) -> None:
        for k in keys:
            self._counter.add(k)
            self._bus.publish(make_event("key_down" if k.down else "key_up", lane=k.lane, dir=k.dir, t=k.t))

    def _emit_step(self) -> None:
        s = self._session
        if s is not None and s.current_target is not None:
            self._bus.publish(make_event("bind_step", target=s.current_target, index=s.index, total=len(TARGETS)))

    # -- input thread ------------------------------------------------------------------
    def handle_raw(self, ev: RawEvent) -> None:
        with self._lock:
            if self._session is not None:
                before = self._session.index
                binding = self._session.feed(ev)
                if binding is not None:
                    self._session = None
                    self._repo.put(binding)
                    self._mapper.set_bindings(self._repo.all())
                    self._bus.publish(make_event("bind_done", binding=binding.to_json()))
                    self._bus.publish(make_event("devices", devices=[d.to_json() for d in self._device_infos()]))
                elif self._session.index != before:
                    self._emit_step()
                return
            self._emit_keys(self._mapper.feed(ev))

    def handle_devices(self, pairs: list[tuple[str, str]]) -> None:
        with self._lock:
            now = time.perf_counter() * 1000
            present = {g for g, _ in pairs}
            for guid, _ in self._devices:
                if guid not in present:
                    self._emit_keys(self._mapper.release_device(guid, now))
            self._devices = list(pairs)
            self._bus.publish(make_event("devices", devices=[d.to_json() for d in self._device_infos()]))

    def handle_idle(self, t: float) -> None:
        with self._lock:
            if self._session is None:
                self._emit_keys(self._mapper.tick(t))

    # -- page messages -------------------------------------------------------------------
    def handle_client(self, msg: dict) -> None:
        kind = msg.get("type") if isinstance(msg, dict) else None
        with self._lock:
            if kind == "bind_start":
                self._emit_keys(self._mapper.release_all(time.perf_counter() * 1000))
                self._session = BindingSession(dict(self._devices))
                self._emit_step()
            elif kind == "bind_cancel":
                if self._session is not None:
                    self._session = None
                    self._bus.publish(make_event("bind_cancelled"))
            elif kind == "counts_reset":
                self._counter.reset()
                self._bus.publish(make_event("counts", counts=self._counter.snapshot()))
