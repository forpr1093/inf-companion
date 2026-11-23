"""dxcam capture: DXGI Desktop Duplication of the monitor INFINITAS is on.

Chosen as the default Windows backend from the capture spike (58 fps at 11% CPU flat out,
about 7% at the 4 fps the app uses; PrintWindow is black in fullscreen). dxcam is asked
for raw BGRA with its numpy processor, so OpenCV is never needed.

The window and its monitor are looked up again as INFINITAS starts, moves, minimises or
closes; the Windows calls are injected so this logic is tested on any platform.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import numpy as np

from inf_companion.capture.base import normalise
from inf_companion.capture.win32 import Rect, crop_to_client

WINDOW_RETRY_S = 2.0  # how often to look for INFINITAS while it isn't running


class DxcamSource:
    def __init__(self, find: Callable[[], int | None], client_rect: Callable[[int], Rect],
                 monitor_of: Callable[[int], tuple[int, Rect]], make_camera: Callable[[int], Any],
                 clock: Callable[[], float] = time.monotonic):
        self._find, self._client_rect, self._monitor_of = find, client_rect, monitor_of
        self._make_camera, self._clock = make_camera, clock
        self._cam: Any = None
        self._hmon: int | None = None
        self._last: np.ndarray | None = None
        self._next_lookup = 0.0
        self._had_window = False

    def grab(self) -> np.ndarray | None:
        hwnd = self._window()
        if hwnd is None:
            self._last = None
            return None
        hmon, monitor = self._monitor_of(hwnd)
        if self._cam is None or hmon != self._hmon:
            self._release()
            self._cam, self._hmon = self._make_camera(hmon), hmon
        try:
            raw = self._cam.grab()  # None when nothing changed since the last grab
        except Exception:  # e.g. access lost on a mode switch: start over next time
            self._release()
            return None
        rect = self._client_rect(hwnd)
        if raw is not None:
            rgb = np.ascontiguousarray(raw[:, :, 2::-1])  # BGRA -> RGB
            crop = crop_to_client(rgb, rect, monitor)
            self._last = None if crop is None else normalise(crop)
        elif rect[2] <= rect[0] or rect[3] <= rect[1]:
            self._last = None  # minimised: nothing to show even if the monitor is unchanged
        return self._last

    def _window(self) -> int | None:
        if not self._had_window and self._clock() < self._next_lookup:
            return None
        hwnd = self._find()
        self._had_window = hwnd is not None
        if hwnd is None:
            self._next_lookup = self._clock() + WINDOW_RETRY_S
            self._release()
        return hwnd

    def _release(self) -> None:
        if self._cam is not None:
            try:
                self._cam.release()
            except Exception:
                pass
        self._cam, self._hmon = None, None

    def close(self) -> None:
        self._release()


def _handle(h: Any) -> int:
    """A monitor handle as an int, whether ctypes gave an int, None or a c_void_p."""
    return int(getattr(h, "value", h) or 0)


def make_dxcam_camera(hmon: int) -> Any:
    """A dxcam camera on the adapter/output whose monitor handle is hmon."""
    import dxcam

    for i_adapter, p_adapter in enumerate(dxcam.enum_dxgi_adapters()):
        for i_output, p_output in enumerate(dxcam.Device(p_adapter).enum_outputs()):
            if _handle(dxcam.Output(p_output).hmonitor) == _handle(hmon):
                try:
                    return dxcam.create(device_idx=i_adapter, output_idx=i_output,
                                        output_color="BGRA", processor_backend="numpy")
                except TypeError:  # older dxcam without processor_backend
                    return dxcam.create(device_idx=i_adapter, output_idx=i_output, output_color="BGRA")
    raise RuntimeError("no DXGI output matches the monitor INFINITAS is on")


def open_dxcam() -> DxcamSource:
    from inf_companion.capture import win32

    win32.set_dpi_aware()
    return DxcamSource(find=win32.find_window, client_rect=win32.client_rect,
                       monitor_of=win32.monitor_of, make_camera=make_dxcam_camera)
