"""Screen classification.

Known screens come from inf-notebook's screenrecognition table: each entry is a tiny area
whose summed channel values identify the screen. The play screen has no entry, so it is
recognised by a 16x16 average hash of a side-specific crop (refs/play.json), made by
tools/calibrate_screens.py from the user's own screenshots.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image

Orientation = Literal["as_is", "flipped"]

REFS = Path(__file__).parent / "refs"

# Calibrated 2026-11-23 against the user's dxcam captures (1920x1080): keys match exactly
# as captured (not flipped). The tolerance only matters for frames rescaled to 1080p
# (1600x900 drifts by up to 89, 1440p by 72); the closest wrong entry was 1017 away.
SCREEN_ORIENTATION: Orientation = "as_is"
SCREEN_TOLERANCE = 150


def area_key(frame: np.ndarray, area: dict, orientation: Orientation = SCREEN_ORIENTATION) -> int:
    """Sum of every channel value in the area. 'flipped' reads the area from a vertically
    flipped image (channel order doesn't change a sum)."""
    if orientation == "flipped":
        frame = frame[::-1]
    top, left = area["top"], area["left"]
    crop = frame[top:top + area["height"], left:left + area["width"]]
    return int(crop.sum(dtype=np.int64))


def average_hash(img: np.ndarray, size: int = 16) -> str:
    """size x size average hash as hex: one bit per cell, set when brighter than the mean."""
    small = np.asarray(Image.fromarray(np.ascontiguousarray(img)).convert("L").resize((size, size), Image.BOX),
                       dtype=np.float64)
    bits = (small > small.mean()).flatten()
    value = 0
    for b in bits:
        value = (value << 1) | int(b)
    return f"{value:0{size * size // 4}x}"


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


@lru_cache(maxsize=1)
def _play_refs() -> dict:
    path = REFS / "play.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def play_reference_notice(side: str) -> str | None:
    """A message for the user when play can't be detected on their side, else None."""
    if _play_refs().get(side):
        return None
    return (f"No play reference for {side}: play detection is off. Add {side} play screenshots to "
            f"tests/fixtures/screens/play_{side.lower()}/ and run tools/calibrate_screens.py --write-play.")


def is_play(frame: np.ndarray, side: str) -> bool:
    refs = _play_refs()
    ref = refs.get(side)
    if not ref:
        return False
    a = ref["area"]
    crop = frame[a["top"]:a["top"] + a["height"], a["left"]:a["left"] + a["width"]]
    return hamming(average_hash(crop), ref["hash"]) <= refs.get("max_distance", 10)


def classify(frame: np.ndarray, tables, side: str) -> str:
    for name, entry in tables.screen["get_screen"].items():
        if abs(area_key(frame, entry["area"]) - entry["value"]) <= SCREEN_TOLERANCE:
            return name
    if is_play(frame, side):
        return "play"
    return "unknown"
