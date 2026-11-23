"""Replay capture: plays saved screenshots, so recognition can be developed on macOS."""

import re
from pathlib import Path

import numpy as np
from PIL import Image

from inf_companion.capture.base import normalise

EXTS = {".png", ".jpg", ".jpeg"}


def _natural(p: Path) -> list:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


class ReplaySource:
    def __init__(self, source: Path, loop: bool = False):
        source = Path(source)
        if source.is_file() and source.suffix.lower() in EXTS:
            files = [source]
        elif source.is_dir():
            files = sorted((p for p in source.iterdir() if p.suffix.lower() in EXTS), key=_natural)
        else:
            files = []
        if not files:
            raise FileNotFoundError(f"No replay frames (.png/.jpg) found at {source}")
        self.files, self.loop, self._i = files, loop, 0

    def __len__(self) -> int:
        return len(self.files)

    def grab(self) -> np.ndarray | None:
        if self._i >= len(self.files):
            if not self.loop:
                return None
            self._i = 0
        path = self.files[self._i]
        self._i += 1
        with Image.open(path) as im:
            return normalise(im)

    def close(self) -> None:
        pass
