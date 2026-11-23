"""Capture + recognition in a child process, so it never competes with the server or input.

The child grabs frames at an adaptive low rate, classifies the screen, and sends changes
back over a queue; a thread in the parent publishes them on the EventBus.
"""

from __future__ import annotations

import multiprocessing as mp
import queue as queue_mod
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from inf_companion.events import make_event
from inf_companion.tables.load import TablesError, load_tables

RATE_FPS = {"play": 2.0, "default": 4.0, "idle": 0.0}
NO_FRAMES_POLL_S = 1.0


class StableScreen:
    """Only report a screen after it has been seen `n` times in a row (no flicker)."""

    def __init__(self, n: int = 3):
        self.n, self.current, self._candidate, self._count = n, None, None, 0

    def feed(self, label: str) -> str | None:
        if label == self._candidate:
            self._count += 1
        else:
            self._candidate, self._count = label, 1
        if self._count >= self.n and label != self.current:
            self.current = label
            return label
        return None


def capture_loop(source, classify_fn: Callable[[np.ndarray], str], emit: Callable[[dict], None], stop,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
                 fixed_fps: float | None = None, notice: str | None = None,
                 on_frame: Callable[[np.ndarray, str | None], list[dict]] | None = None) -> None:
    stable = StableScreen()
    status = None
    while not stop.is_set():
        started = clock()
        frame = source.grab()
        if frame is None:
            if status != "no frames":
                status = "no frames"
                emit({"type": "capture_status", "state": status})
            sleep(NO_FRAMES_POLL_S)
            continue
        if status != "running":
            status = "running"
            emit({"type": "capture_status", "state": status} | ({"message": notice} if notice else {}))
        changed = stable.feed(classify_fn(frame))
        if changed is not None:
            emit({"type": "screen", "screen": changed})
        if on_frame is not None:
            for msg in on_frame(frame, stable.current):
                emit(msg)
        fps = fixed_fps or RATE_FPS["play" if stable.current == "play" else "default"]
        sleep(max(0.0, 1.0 / fps - (clock() - started)))


def _child(kind: str, source_path: str, tables_dir: str, side: str, q, stop, fixed_fps: float | None,
           record_dir: str | None = None) -> None:
    try:
        _run_child(kind, source_path, tables_dir, side, q, stop, fixed_fps, record_dir)
    except Exception as e:  # tell the app instead of dying with only a traceback
        q.put({"type": "capture_status", "state": "off", "message": f"Capture stopped: {type(e).__name__}: {e}"})
        raise


def _run_child(kind: str, source_path: str, tables_dir: str, side: str, q, stop, fixed_fps: float | None,
               record_dir: str | None = None) -> None:
    from inf_companion.recog.screen import classify, play_reference_notice

    tables = load_tables(Path(tables_dir))
    if kind == "replay":
        from inf_companion.capture.replay import ReplaySource
        source = ReplaySource(Path(source_path))
    elif kind == "dxcam":
        from inf_companion.capture.dxcam_source import open_dxcam
        source = open_dxcam()
    else:
        raise ValueError(f"unknown capture backend {kind!r}")
    reader, reading_notice = _make_reader(tables, side)
    notice = "; ".join(n for n in (play_reference_notice(side), reading_notice) if n) or None
    on_frame = reader.on_frame
    if record_dir:
        from inf_companion.capture.recorder import FrameRecorder
        recorder = FrameRecorder(Path(record_dir))

        def on_frame(frame, screen):
            message = recorder.offer(frame, screen)
            status = [{"type": "capture_status", "state": "running", "message": message}] if message else []
            return status + reader.on_frame(frame, screen)
    try:
        capture_loop(source, lambda f: classify(f, tables, side), q.put, stop, fixed_fps=fixed_fps,
                     notice=notice, on_frame=on_frame)
    finally:
        source.close()


def _make_reader(tables, side: str):
    """The screen reader, with whichever tables are present; a message says what's off."""
    from inf_companion.recog.reader import Reader
    from inf_companion.recog.result import ResultReader
    from inf_companion.recog.select import SelectReader

    # Any table that's missing or shaped differently turns that reading off; capture carries on.
    unusable = (TablesError, KeyError, IndexError, TypeError, ValueError, AttributeError)
    off = []
    try:
        select = SelectReader(tables)
    except unusable:
        select = None
        off.append("song select")
    try:
        result = ResultReader(tables)
    except unusable:
        result = None
        off.append("result")
    notice = (f"Reading {' and '.join(off)} is off: tables missing or unusable "
              "(run tools/convert_tables.py)") if off else None
    return Reader(select, result, tables.notesradar, side), notice


def exit_status(exitcode: int | None, last: dict) -> dict | None:
    """The status to report when the child has exited, unless it already reported one."""
    if exitcode in (0, None) or last.get("state") == "off":
        return None
    return {"state": "off", "message": f"capture process exited (code {exitcode})"}


@dataclass
class CaptureHandle:
    process: Any = None
    screen: str | None = None
    status: dict = field(default_factory=lambda: {"state": "off"})
    chart: dict | None = None
    personal_best: dict | None = None
    result: dict | None = None
    _stop: Any = None
    _relay: threading.Thread | None = None

    def state(self) -> dict:
        return {"screen": self.screen, "capture_status": self.status, "chart": self.chart,
                "personal_best": self.personal_best}

    def remember(self, msg: dict) -> None:
        """Keep the latest of each message, for pages that connect later (hello)."""
        kind = msg["type"]
        if kind == "screen":
            self.screen = msg["screen"]
        elif kind == "capture_status":
            self.status = {k: v for k, v in msg.items() if k != "type"}
        elif kind == "chart":
            self.chart = msg["chart"]
        elif kind == "personal_best":
            self.personal_best = msg["best"]
        elif kind == "result":
            self.result = msg["result"]

    def stop(self) -> None:
        if self._stop is not None:
            self._stop.set()
        if self.process is not None:
            self.process.join(timeout=3)
            if self.process.is_alive():
                self.process.terminate()


def start_capture(kind: str, source_path, tables_dir, side: str, bus, fixed_fps: float | None = None,
                  record_dir: str | None = None) -> CaptureHandle:
    handle = CaptureHandle()

    def publish(msg: dict) -> None:
        handle.remember(msg)
        bus.publish(make_event(**msg))

    try:
        load_tables(Path(tables_dir))  # fail fast, in the parent, with a clear message
    except TablesError as e:
        publish({"type": "capture_status", "state": "off", "message": str(e)})
        return handle

    ctx = mp.get_context("spawn")
    q, stop = ctx.Queue(), ctx.Event()
    proc = ctx.Process(target=_child, args=(kind, str(source_path), str(tables_dir), side, q, stop, fixed_fps, record_dir),
                       name="inf-companion-capture", daemon=True)
    proc.start()

    def relay() -> None:
        while proc.is_alive() or not q.empty():
            try:
                publish(q.get(timeout=0.5))
            except queue_mod.Empty:
                continue
            except (EOFError, OSError):
                break
        final = exit_status(proc.exitcode, handle.status)
        if final is not None:
            publish({"type": "capture_status", **final})

    t = threading.Thread(target=relay, name="capture-relay", daemon=True)
    t.start()
    handle.process, handle._stop, handle._relay = proc, stop, t
    return handle
