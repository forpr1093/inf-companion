"""Save labelled frames while you play, for calibrating recognition later (--record DIR).

Frames go to DIR/<screen>/<timestamp>.png. A frame is saved only when it looks different
from the last one saved for that screen, at most once a second, and never more than
`max_files` in one run. Any write error turns recording off with one message; capture
itself carries on.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from inf_companion.recog.screen import average_hash, hamming


def png_writer(img: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img).save(path, compress_level=1)


class FrameRecorder:
    def __init__(self, root: Path, min_interval_s: float = 1.0, min_distance: int = 12, max_files: int = 3000,
                 clock: Callable[[], float] = time.monotonic,
                 save: Callable[[np.ndarray, Path], None] = png_writer):
        self.root, self.min_interval_s, self.min_distance = Path(root), min_interval_s, min_distance
        self.max_files, self._clock, self._save = max_files, clock, save
        self._last_hash: dict[str, str] = {}
        self._last_time: float | None = None
        self._count = 0
        self._seq = 0
        self.active = True

    def offer(self, frame: np.ndarray, screen: str | None) -> str | None:
        """Maybe save the frame. Returns a message once, when recording turns itself off."""
        if not self.active:
            return None
        now = self._clock()
        if self._last_time is not None and now - self._last_time < self.min_interval_s:
            return None
        label = screen or "unknown"
        h = average_hash(frame)
        last = self._last_hash.get(label)
        if last is not None and hamming(h, last) < self.min_distance:
            return None
        if self._count >= self.max_files:
            self.active = False
            return f"Recording stopped after {self.max_files} screenshots in {self.root}"
        self._seq += 1
        path = self.root / label / f"{datetime.now():%Y%m%d-%H%M%S-%f}"[:-3]
        path = path.with_name(f"{path.name}-{self._seq:04d}.png")
        try:
            self._save(frame, path)
        except OSError as e:
            self.active = False
            return f"Recording stopped: can't write to {self.root} ({e})"
        self._last_hash[label], self._last_time = h, now
        self._count += 1
        return None
