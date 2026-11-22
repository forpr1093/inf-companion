"""Reads joysticks with SDL2 on a background thread.

Uses the joystick API, not the game-controller API: IIDX controllers are rarely
standard gamepads. Background events are allowed so input keeps arriving while
INFINITAS has focus. SDL is initialised and pumped on this same thread.
"""

import ctypes
import logging
import threading
import time
from collections.abc import Callable

from inf_companion.input.model import RawEvent

log = logging.getLogger(__name__)


class SdlInputThread:
    def __init__(
        self,
        on_raw: Callable[[RawEvent], None],
        on_devices: Callable[[list[tuple[str, str]]], None],
        on_idle: Callable[[float], None],
    ):
        self._on_raw = on_raw
        self._on_devices = on_devices
        self._on_idle = on_idle
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.ready = threading.Event()
        self.error: str | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="sdl-input", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        import sdl2

        sdl2.SDL_SetHint(sdl2.SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, b"1")
        if sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK) != 0:
            self.error = sdl2.SDL_GetError().decode(errors="replace")
            log.error("SDL joystick init failed: %s", self.error)
            self.ready.set()
            return
        sdl2.SDL_JoystickEventState(sdl2.SDL_ENABLE)
        joysticks: dict[int, tuple[object, str, str]] = {}  # instance id -> (handle, guid, name)
        self.ready.set()
        event = sdl2.SDL_Event()

        def report() -> None:
            self._on_devices([(g, n) for _, g, n in joysticks.values()])

        def handle() -> None:
            now = time.perf_counter() * 1000
            et = event.type
            if et == sdl2.SDL_JOYDEVICEADDED:
                joy = sdl2.SDL_JoystickOpen(event.jdevice.which)
                if joy:
                    buf = ctypes.create_string_buffer(33)
                    sdl2.SDL_JoystickGetGUIDString(sdl2.SDL_JoystickGetGUID(joy), buf, 33)
                    name = (sdl2.SDL_JoystickName(joy) or b"").decode(errors="replace")
                    joysticks[sdl2.SDL_JoystickInstanceID(joy)] = (joy, buf.value.decode(), name)
                    report()
            elif et == sdl2.SDL_JOYDEVICEREMOVED:
                entry = joysticks.pop(event.jdevice.which, None)
                if entry:
                    sdl2.SDL_JoystickClose(entry[0])
                    report()
            elif et == sdl2.SDL_JOYAXISMOTION:
                if event.jaxis.which in joysticks:
                    guid = joysticks[event.jaxis.which][1]
                    self._on_raw(RawEvent(guid, "axis", event.jaxis.axis, event.jaxis.value, now))
            elif et in (sdl2.SDL_JOYBUTTONDOWN, sdl2.SDL_JOYBUTTONUP):
                if event.jbutton.which in joysticks:
                    guid = joysticks[event.jbutton.which][1]
                    self._on_raw(RawEvent(guid, "button", event.jbutton.button, 1 if et == sdl2.SDL_JOYBUTTONDOWN else 0, now))
            elif et == sdl2.SDL_JOYHATMOTION:
                if event.jhat.which in joysticks:
                    guid = joysticks[event.jhat.which][1]
                    self._on_raw(RawEvent(guid, "hat", event.jhat.hat, event.jhat.value, now))

        try:
            report()
            while not self._stop.is_set():
                if sdl2.SDL_WaitEventTimeout(ctypes.byref(event), 5):
                    handle()
                    while sdl2.SDL_PollEvent(ctypes.byref(event)):
                        handle()
                self._on_idle(time.perf_counter() * 1000)
        except Exception:  # never let a bad event kill input silently
            log.exception("SDL input thread crashed")
            self.error = "input thread crashed"
        finally:
            for joy, _, _ in joysticks.values():
                sdl2.SDL_JoystickClose(joy)
            sdl2.SDL_QuitSubSystem(sdl2.SDL_INIT_JOYSTICK)
