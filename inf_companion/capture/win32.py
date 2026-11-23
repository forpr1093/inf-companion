"""Small Windows helpers for finding the INFINITAS window and its monitor.

The pure parts (pick_window, crop_to_client) run anywhere; the rest need Windows and are
only called from the Windows capture backends.
"""

from __future__ import annotations

import ctypes
from collections.abc import Iterable

import numpy as np

TITLE = "beatmania IIDX INFINITAS"
Rect = tuple[int, int, int, int]  # left, top, right, bottom in screen coordinates


def pick_window(windows: Iterable[tuple[int, str]], title: str = TITLE) -> int | None:
    for hwnd, text in windows:
        if text.startswith(title):
            return hwnd
    return None


def crop_to_client(frame: np.ndarray, client: Rect, monitor: Rect) -> np.ndarray | None:
    """Cut the window's client area out of a frame of one monitor (both in screen coords)."""
    h, w = frame.shape[:2]
    l, t = max(client[0] - monitor[0], 0), max(client[1] - monitor[1], 0)
    r, b = min(client[2] - monitor[0], w), min(client[3] - monitor[1], h)
    if r <= l or b <= t:
        return None
    return frame[t:b, l:r]


# --- Windows only ------------------------------------------------------------------------------

def _user32():
    from ctypes import wintypes
    u = ctypes.windll.user32
    u.FindWindowW.argtypes, u.FindWindowW.restype = [wintypes.LPCWSTR, wintypes.LPCWSTR], wintypes.HWND
    u.IsWindowVisible.argtypes = [wintypes.HWND]
    u.IsIconic.argtypes = [wintypes.HWND]
    u.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    u.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    u.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    u.MonitorFromWindow.argtypes, u.MonitorFromWindow.restype = [wintypes.HWND, wintypes.DWORD], wintypes.HMONITOR
    u.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.c_void_p]
    return u


def find_window() -> int | None:
    """The INFINITAS window: an exact title match first, then any title starting with it."""
    u = _user32()
    hwnd = u.FindWindowW(None, TITLE)
    if hwnd:
        return int(hwnd)
    found: list[tuple[int, str]] = []
    proc_t = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(h, _):
        if u.IsWindowVisible(h):
            n = u.GetWindowTextLengthW(h)
            buf = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, buf, n + 1)
            found.append((int(h), buf.value))
        return True

    ctypes.windll.user32.EnumWindows(proc_t(cb), 0)
    return pick_window(found)


def client_rect(hwnd: int) -> Rect:
    """The window's client area in screen coordinates; empty when minimised."""
    from ctypes import wintypes
    u = _user32()
    if u.IsIconic(hwnd):
        return (0, 0, 0, 0)
    r = wintypes.RECT()
    u.GetClientRect(hwnd, ctypes.byref(r))
    p = wintypes.POINT(0, 0)
    u.ClientToScreen(hwnd, ctypes.byref(p))
    return p.x, p.y, p.x + r.right, p.y + r.bottom


def monitor_of(hwnd: int) -> tuple[int, Rect]:
    """(HMONITOR, monitor rect) for the monitor the window is on."""
    from ctypes import wintypes

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    u = _user32()
    hmon = u.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    u.GetMonitorInfoW(hmon, ctypes.byref(mi))
    r = mi.rcMonitor
    return int(hmon or 0), (r.left, r.top, r.right, r.bottom)


def set_dpi_aware() -> None:
    """Report real pixels, not scaled ones, on high-DPI displays."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
