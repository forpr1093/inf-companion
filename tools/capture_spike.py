"""Capture spike (throwaway, Windows). Design §7.

For each capture method, grab the INFINITAS window for a while at a target rate and at max
rate, and record whether frames are real or black, the fps reached and this process's CPU
use. Saves sample frames for the recognition fixtures. Not imported by the app.

Run (see docs/windows-setup.md, "Capture spike"):
  uv run --with dxcam --with psutil --with pillow --with numpy python tools/capture_spike.py --out D:\\capture-spike
"""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

TITLE = "beatmania IIDX INFINITAS"


# --- pure helpers (tested on any OS) -------------------------------------------------------

@dataclass
class Sample:
    t: float      # seconds since the run started
    ok: bool      # a new frame arrived
    black: bool   # the frame was (nearly) all black
    cpu: float    # this process's CPU %, of one core


def is_black(frame: np.ndarray) -> bool:
    return float(frame.mean()) < 3.0


def summarise(samples: list[Sample]) -> dict:
    if not samples:
        return {"frames": 0, "fps": 0.0, "black_ratio": 0.0, "cpu_avg": 0.0, "cpu_max": 0.0, "status": "no window"}
    good = [s for s in samples if s.ok]
    span = samples[-1].t - samples[0].t
    fps = (len(good) - 1) / span if len(good) > 1 and span > 0 else 0.0
    black_ratio = sum(s.black for s in good) / len(good) if good else 0.0
    cpus = [s.cpu for s in samples]
    if not good:
        status = "no frames"
    elif black_ratio > 0.5:
        status = "black frames"
    else:
        status = "ok"
    return {
        "frames": len(good), "fps": round(fps, 2), "black_ratio": round(black_ratio, 3),
        "cpu_avg": round(sum(cpus) / len(cpus), 2), "cpu_max": max(cpus), "status": status,
    }


def crop_to_client(frame: np.ndarray, client: tuple[int, int, int, int],
                   monitor: tuple[int, int, int, int]) -> np.ndarray | None:
    """Cut the window's client area (screen coords) out of a frame of one monitor (screen coords)."""
    h, w = frame.shape[:2]
    l, t = client[0] - monitor[0], client[1] - monitor[1]
    r, b = client[2] - monitor[0], client[3] - monitor[1]
    l, t, r, b = max(l, 0), max(t, 0), min(r, w), min(b, h)
    if r <= l or b <= t:
        return None
    return frame[t:b, l:r]


def find_window(enum: Callable[[], Iterable[tuple[int, str]]] | None = None, title: str = TITLE) -> int | None:
    for hwnd, text in (enum or _enum_windows)():
        if text.startswith(title):
            return hwnd
    return None


# --- Windows only ------------------------------------------------------------------------------

def _enum_windows() -> list[tuple[int, str]]:
    user32 = ctypes.windll.user32
    found: list[tuple[int, str]] = []
    proc_t = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            found.append((hwnd, buf.value))
        return True

    user32.EnumWindows(proc_t(cb), 0)
    return found


def _client_rect(hwnd: int) -> tuple[int, int, int, int]:
    """Client area in screen coordinates: left, top, right, bottom."""
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    r = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    p = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(p))
    return p.x, p.y, p.x + r.right, p.y + r.bottom


def _dib_to_rgb(gdi32, mem, bmp, w: int, h: int) -> np.ndarray | None:
    """Read a bitmap as a 32-bit top-down DIB and return RGB."""
    from ctypes import wintypes

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

    bi = BITMAPINFOHEADER()
    bi.biSize, bi.biWidth, bi.biHeight = ctypes.sizeof(BITMAPINFOHEADER), w, -h  # negative: top-down
    bi.biPlanes, bi.biBitCount, bi.biCompression = 1, 32, 0
    buf = (ctypes.c_ubyte * (w * h * 4))()
    if not gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0):
        return None
    bgra = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
    return bgra[:, :, 2::-1].copy()  # BGRA -> RGB


class WindowGrabber:
    """PrintWindow(PW_CLIENTONLY | PW_RENDERFULLCONTENT) into a 32-bit top-down DIB."""

    def __init__(self, hwnd: int):
        self.hwnd = hwnd

    def grab(self) -> np.ndarray | None:
        from ctypes import wintypes
        user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
        l, t, r, b = _client_rect(self.hwnd)
        w, h = r - l, b - t
        if w <= 0 or h <= 0:
            return None
        hdc = user32.GetDC(self.hwnd)
        mem = gdi32.CreateCompatibleDC(hdc)
        bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
        old = gdi32.SelectObject(mem, bmp)
        try:
            if not user32.PrintWindow(self.hwnd, mem, 3):
                return None
            return _dib_to_rgb(gdi32, mem, bmp, w, h)
        finally:
            gdi32.SelectObject(mem, old)
            gdi32.DeleteObject(bmp)
            gdi32.DeleteDC(mem)
            user32.ReleaseDC(self.hwnd, hdc)

    def close(self) -> None:
        pass


def _monitor_of(hwnd: int) -> tuple[int, tuple[int, int, int, int]]:
    """(HMONITOR, monitor rect in screen coords) for the monitor the window is on."""
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.MonitorFromWindow.restype = ctypes.c_void_p
    hmon = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(ctypes.c_void_p(hmon), ctypes.byref(mi))
    r = mi.rcMonitor
    return hmon, (r.left, r.top, r.right, r.bottom)


class ScreenGrabber:
    """BitBlt from the whole-desktop DC ("DISPLAY") at the window's client area.

    Works across monitors (the DISPLAY DC covers the virtual screen) and often where
    PrintWindow gives black frames for DirectX games.
    """

    def __init__(self, hwnd: int):
        self.hwnd = hwnd
        gdi32 = ctypes.windll.gdi32
        gdi32.CreateDCW.restype = ctypes.c_void_p
        self.screen = gdi32.CreateDCW("DISPLAY", None, None, None)

    def grab(self) -> np.ndarray | None:
        from ctypes import wintypes
        gdi32 = ctypes.windll.gdi32
        l, t, r, b = _client_rect(self.hwnd)
        w, h = r - l, b - t
        if w <= 0 or h <= 0:
            return None
        mem = gdi32.CreateCompatibleDC(ctypes.c_void_p(self.screen))
        bmp = gdi32.CreateCompatibleBitmap(ctypes.c_void_p(self.screen), w, h)
        old = gdi32.SelectObject(mem, bmp)
        try:
            if not gdi32.BitBlt(mem, 0, 0, w, h, ctypes.c_void_p(self.screen), l, t, 0x00CC0020):  # SRCCOPY
                return None
            return _dib_to_rgb(gdi32, mem, bmp, w, h)
        finally:
            gdi32.SelectObject(mem, old)
            gdi32.DeleteObject(bmp)
            gdi32.DeleteDC(mem)

    def close(self) -> None:
        ctypes.windll.gdi32.DeleteDC(ctypes.c_void_p(self.screen))


class DxcamGrabber:
    """DXGI Desktop Duplication of the output INFINITAS is on, cropped to its client area.

    The adapter and output are matched by monitor handle (like inf-notebook does), unless
    --dxcam-output forces an output on adapter 0.
    """

    def __init__(self, hwnd: int, output: int | None):
        import dxcam
        self.hwnd = hwnd
        hmon, self.monitor = _monitor_of(hwnd)
        device_idx, output_idx = 0, output
        if output is None:
            for i_adapter, p_adapter in enumerate(dxcam.enum_dxgi_adapters()):
                for i_output, p_output in enumerate(dxcam.Device(p_adapter).enum_outputs()):
                    if int(dxcam.Output(p_output).hmonitor or 0) == int(hmon or 0):
                        device_idx, output_idx = i_adapter, i_output
            if output_idx is None:
                raise RuntimeError("no DXGI output matches the INFINITAS monitor")
        self.picked = f"adapter {device_idx}, output {output_idx}"
        print(f"  dxcam: {self.picked}, monitor {self.monitor}")
        self.cam = dxcam.create(device_idx=device_idx, output_idx=output_idx, output_color="RGB")

    def grab(self) -> np.ndarray | None:
        frame = self.cam.grab()  # None when nothing changed since the last grab
        if frame is None:
            return None
        return crop_to_client(frame, _client_rect(self.hwnd), self.monitor)

    def close(self) -> None:
        try:
            self.cam.release()
        except Exception:
            pass
        del self.cam


# --- the run -----------------------------------------------------------------------------------

def run_one(grabber, seconds: float, target_fps: float, save_every: float, frames_dir: Path) -> list[Sample]:
    import psutil
    from PIL import Image
    proc = psutil.Process()
    proc.cpu_percent(None)
    samples: list[Sample] = []
    frames_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    next_save, saved = 0.0, 0
    period = 1.0 / target_fps if target_fps > 0 else 0.0
    while (now := time.perf_counter() - start) < seconds:
        frame = grabber.grab()
        ok = frame is not None
        black = bool(ok and is_black(frame))
        samples.append(Sample(t=now, ok=ok, black=black, cpu=proc.cpu_percent(None)))
        if ok and now >= next_save:
            Image.fromarray(frame).save(frames_dir / f"{saved:04d}.png")
            saved += 1
            next_save = now + save_every
        if period:
            time.sleep(max(0.0, period - (time.perf_counter() - start - now)))
    return samples


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--method", choices=["window", "screen", "dxcam", "all"], default="all")
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--target-fps", type=float, default=4)
    ap.add_argument("--save-every", type=float, default=2.0)
    ap.add_argument("--dxcam-output", type=int, default=None,
                    help="force a dxcam output on adapter 0 (default: match INFINITAS's monitor)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if sys.platform != "win32":
        print("The capture spike runs on Windows only.")
        return 2
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # real pixels, not scaled ones
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    hwnd = find_window()
    results: dict[str, dict] = {}
    methods = ["window", "screen", "dxcam"] if a.method == "all" else [a.method]
    for method in methods:
        for target in (a.target_fps, 0.0):
            key = f"{method} @ {'max' if target == 0 else f'{target:g} fps'}"
            if hwnd is None:
                results[key] = summarise([])
                continue
            print(f"Running {key} for {a.seconds:g} s ...")
            try:
                grabber = {"window": lambda: WindowGrabber(hwnd), "screen": lambda: ScreenGrabber(hwnd),
                           "dxcam": lambda: DxcamGrabber(hwnd, a.dxcam_output)}[method]()
            except Exception as e:  # e.g. dxcam not installed or no such output
                results[key] = {**summarise([]), "status": f"error: {e}"}
                continue
            try:
                samples = run_one(grabber, a.seconds, target, a.save_every, out / "frames" / key.replace(" ", "").replace("@", "_"))
            finally:
                grabber.close()
            results[key] = summarise(samples)
            print(f"  {results[key]}")
    if hwnd is None:
        print(f"No window titled '{TITLE}' was found. Start INFINITAS first.")
    (out / "report.json").write_text(json.dumps(results, indent=2))
    lines = ["| method | status | fps | black | CPU avg % | CPU max % | frames |", "|---|---|---|---|---|---|---|"]
    for key, r in results.items():
        lines.append(f"| {key} | {r['status']} | {r['fps']} | {r['black_ratio']} | {r['cpu_avg']} | {r['cpu_max']} | {r['frames']} |")
    (out / "report.md").write_text("\n".join(lines) + "\n")
    print(f"Report written to {out / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
