"""Turn image crops into lookup keys for the converted inf-notebook tables.

The tables key their entries by packed bit masks. These helpers reproduce the packing the
tables were built with (see the Semantics section of the screen-reading plan); they are our
own implementation of that method.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import numpy as np

# Table lamp names -> the official CSV spelling, which the app uses everywhere.
LAMPS: dict[str, str] = {
    "NO PLAY": "NO PLAY",
    "FAILED": "FAILED",
    "A-CLEAR": "ASSIST CLEAR",
    "E-CLEAR": "EASY CLEAR",
    "CLEAR": "CLEAR",
    "H-CLEAR": "HARD CLEAR",
    "EXH-CLEAR": "EX HARD CLEAR",
    "F-COMBO": "FULLCOMBO CLEAR",
}


def to_index(trim: list) -> tuple:
    """A JSON trim ({"slice": [a, b, c]} items or ints) as a numpy index tuple."""
    return tuple(slice(*t["slice"]) if isinstance(t, dict) else t for t in trim)


def _hex(values: np.ndarray) -> str:
    return "".join(format(int(v), "x") for v in values.flatten())


def nibbles(bits: np.ndarray) -> str:
    """Flatten row-major and pack every 4 bits into one hex digit."""
    b = np.asarray(bits, dtype=np.int64).flatten()
    return _hex(b[0::4] * 8 + b[1::4] * 4 + b[2::4] * 2 + b[3::4])


def nibbles_cols(bits: np.ndarray) -> str:
    """Pack along the columns of a 2-D mask with numpy broadcasting, then flatten.

    When the width isn't a multiple of 4 the narrower column slices broadcast across the
    wider ones; the tables were built that way, so the keys depend on it.
    """
    b = np.asarray(bits, dtype=np.int64)
    return _hex(b[:, 0::4] * 8 + b[:, 1::4] * 4 + b[:, 2::4] * 2 + b[:, 3::4])


def packbits_hex(bits: np.ndarray) -> str:
    return np.packbits(np.asarray(bits, dtype=np.uint8).flatten()).tobytes().hex()


def walk(trie: dict, keys: Iterable[str]) -> str | None:
    """Follow keys through nested dicts until a string (the answer) or a miss."""
    node: Any = trie
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
        if isinstance(node, str):
            return node
    return None


def in_ranges(img: np.ndarray, ranges: list[list[int]]) -> np.ndarray:
    """True where every channel i lies in ranges[i] (inclusive)."""
    mask = np.ones(img.shape[:2], dtype=bool)
    for i, (lo, hi) in enumerate(ranges):
        mask &= (lo <= img[:, :, i]) & (img[:, :, i] <= hi)
    return mask


def dominant(a: np.ndarray) -> int:
    """The most frequent value; ties go to the smallest."""
    values, counts = np.unique(a, return_counts=True)
    return int(values[np.argmax(counts)])


def as_array(obj: dict) -> np.ndarray:
    """A converted array ({"array", "dtype", "shape"}) as numpy."""
    return np.array(obj["array"], dtype=np.dtype(obj["dtype"])).reshape(obj["shape"])


def read_digits(field: np.ndarray, count: int, part_index: tuple, maskvalue: int, table: dict,
                packer: Callable[[np.ndarray], str]) -> int | None:
    """Read a number split into `count` equal parts, right to left, stopping at the first
    part whose key isn't in the table. None when not even one digit matched."""
    parts = np.hsplit(field, count)
    value = None
    for place in range(count):
        bits = (parts[-(place + 1)][part_index] == maskvalue).astype(np.int64)
        key = packer(bits)
        if key not in table:
            # The places left must be blank; anything drawn there is a misread digit.
            if any(np.any(parts[-(p + 1)][part_index] == maskvalue) for p in range(place, count)):
                return None
            break
        value = (value or 0) + 10 ** place * int(table[key])
    return value
