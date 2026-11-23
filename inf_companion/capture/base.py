"""Capture sources and frame normalisation. A frame is (1080, 1920, 3) uint8 RGB."""

from typing import Protocol

import numpy as np
from PIL import Image

WIDTH, HEIGHT = 1920, 1080


class CaptureSource(Protocol):
    def grab(self) -> np.ndarray | None:
        """The current frame, or None when there's nothing to capture right now."""
        ...

    def close(self) -> None: ...


def normalise(img: "np.ndarray | Image.Image", *, bgr: bool = False) -> np.ndarray:
    """Any RGB/RGBA/BGR image of any size -> (1080, 1920, 3) uint8 RGB."""
    if isinstance(img, np.ndarray):
        arr = img[..., :3]
        if bgr:
            arr = arr[..., ::-1]
        img = Image.fromarray(np.ascontiguousarray(arr).astype(np.uint8, copy=False))
    img = img.convert("RGB")
    if img.size != (WIDTH, HEIGHT):
        img = img.resize((WIDTH, HEIGHT), Image.BILINEAR)
    return np.asarray(img, dtype=np.uint8)
