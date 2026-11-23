"""Read the song-select screen: play mode, title, difficulty, level and the shown best."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from inf_companion.recog.pack import (LAMPS, dominant, in_ranges, nibbles, nibbles_cols, read_digits,
                                      to_index, walk)

# Every musicselect trim is relative to this part of the 1920x1080 frame.
VIEW = (slice(135, 952), slice(48, 1188))


@dataclass(frozen=True)
class SelectRead:
    playmode: str | None
    title: str | None
    difficulty: str | None
    level: int | None
    cleartype: str | None
    djlevel: str | None
    score: int | None
    misscount: int | None


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


class SelectReader:
    def __init__(self, tables):
        t = tables.raw("musicselect")
        self._playmode = (to_index(t["playmode"]["trim"]), t["playmode"]["maskvalue"], t["playmode"]["table"])
        names = t["musicname"]
        self._titles = [(to_index(names[k]["trim"]), names[k]["thresholds"], names[k]["table"])
                        for k in ("infinitas", "leggendaria")]
        self._arcade = (to_index(names["arcade"]["trim"]), names["arcade"]["thresholds"], names["arcade"]["table"])
        self._levels = [(d.upper(), to_index(r["trim"]), r["thresholds"], r["table"])
                        for d, r in t["levels"]["select"].items()]
        self._clear = (to_index(t["cleartype"]["trim"]), t["cleartype"]["table"])
        self._dj = (to_index(t["djlevel"]["trim"]), t["djlevel"]["maskvalue"], t["djlevel"]["table"])
        num = t["number"]
        self._number = (to_index(num["trim"]), num["maskvalue"], num["table"])
        self._score = (to_index(t["score"]["trim"]), t["score"]["digit"])
        self._miss = (to_index(t["misscount"]["trim"]), t["misscount"]["digit"])

    def read(self, frame: np.ndarray) -> SelectRead:
        v = frame[VIEW].astype(np.int64)
        difficulty, level = self._difficulty(v)
        return SelectRead(
            playmode=self._read_playmode(v),
            title=self._title(v),
            difficulty=difficulty,
            level=level,
            cleartype=self._cleartype(v),
            djlevel=self._dj[2].get(str(int(np.count_nonzero(v[self._dj[0]] == self._dj[1])))),
            score=self._digits(v, self._score),
            misscount=self._digits(v, self._miss),
        )

    def _read_playmode(self, v) -> str | None:
        index, mask, table = self._playmode
        return table.get(nibbles(v[index].flatten() == mask))

    def _title(self, v) -> str | None:
        for index, thresholds, table in self._titles:
            bits = in_ranges(v[index], thresholds)
            found = walk(table, (nibbles(row) for row in bits))
            if found:
                return found
        index, thresholds, table = self._arcade
        crop = v[index]
        gray = np.where((crop[:, :, 0] == crop[:, :, 1]) & (crop[:, :, 0] == crop[:, :, 2]), crop[:, :, 0], 0)

        def rows():
            for i, (lo, hi) in enumerate(thresholds):
                bits = ((lo <= gray[i]) & (gray[i] <= hi)).astype(np.int64)
                yield nibbles(bits[0::2] & bits[1::2])

        return walk(table, rows())

    def _difficulty(self, v) -> tuple[str | None, int | None]:
        for name, index, thresholds, table in self._levels:
            key = nibbles_cols(in_ranges(v[index], thresholds))
            if key in table:
                return name, _int(table[key])
        return None, None

    def _cleartype(self, v) -> str | None:
        index, table = self._clear
        name = table.get(str(dominant(v[index])))
        return LAMPS.get(name, name) if name else None

    def _digits(self, v, field) -> int | None:
        index, count = field
        part, mask, table = self._number
        return read_digits(v[index], count, part, mask, table, lambda b: nibbles_cols(b.T))
