"""Read the result screen: chart, clear lamp, DJ level, score, miss count, judges, timings."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from inf_companion.recog.pack import (LAMPS, as_array, dominant, nibbles, nibbles_cols, packbits_hex,
                                      read_digits, to_index)

INFORMATIONS = (slice(910, 1066), slice(560, 1360))
DETAILS = {"1P": (slice(64, 1016), slice(10, 564)), "2P": (slice(64, 1016), slice(1360, 1914))}
JUDGES = {"1P": (slice(780, 920), slice(293, 503)), "2P": (slice(780, 920), slice(1642, 1852))}
TIMINGS = {"1P": (slice(959, 1015), slice(30, 294)), "2P": (slice(959, 1015), slice(1374, 1638))}
SIDE_INDEX = (5, slice(4, 548, 8), 0)  # in the details view; 150 marks the side's bar
SIDE_KEYS = {"0fffffffffffffffe": "1P", "7fffffffffffffff0": "2P"}
JUDGE_NAMES = ("pgreat", "great", "good", "bad", "poor")


@dataclass(frozen=True)
class ResultRead:
    side: str | None = None
    playmode: str | None = None
    title: str | None = None
    difficulty: str | None = None
    level: int | None = None
    notes: int | None = None
    cleartype: str | None = None
    cleartype_best: str | None = None
    djlevel: str | None = None
    djlevel_best: str | None = None
    score: int | None = None
    score_best: int | None = None
    misscount: int | None = None
    misscount_best: int | None = None
    judges: dict = field(default_factory=dict)
    fast: int | None = None
    slow: int | None = None

    @property
    def complete(self) -> bool:
        """Everything needed for a play record, and the EX score agrees with the judges
        (EX = 2 x PGREAT + GREAT), which catches nearly any misread digit."""
        if None in (self.side, self.playmode, self.difficulty, self.cleartype, self.score):
            return False
        if any(self.judges.get(name) is None for name in JUDGE_NAMES):
            return False
        return self.score == 2 * self.judges["pgreat"] + self.judges["great"]


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _lamp(name: str | None) -> str | None:
    return LAMPS.get(name, name) if name else None


class ResultReader:
    def __init__(self, tables):
        self.info = tables.raw("informations")
        self.details = tables.raw("details")
        self.rr = tables.raw("resultrecognition")
        music = self.info["music"]
        self._music_trim = to_index(music["trim"])
        self._bands = {
            band: (as_array(music["factors"][band]["lower"]).astype(np.int64),
                   as_array(music["factors"][band]["upper"]).astype(np.int64),
                   as_array(music["masks"][band]) == 1,
                   music["tables"][band])
            for band in ("blue", "red", "gray")
        }

    # --- informations (shared by both sides) ---------------------------------------------------

    def read(self, frame: np.ndarray) -> ResultRead:
        info = frame[INFORMATIONS].astype(np.int64)
        difficulty, level = self._difficulty(info)
        base = dict(playmode=self._playmode(info), title=self._title(info), difficulty=difficulty,
                    level=level, notes=self._notes(info))
        side = SIDE_KEYS.get(nibbles(frame[DETAILS["1P"]][SIDE_INDEX] == 150)) or \
            SIDE_KEYS.get(nibbles(frame[DETAILS["2P"]][SIDE_INDEX] == 150))
        if side is None:
            return ResultRead(**base)
        details = frame[DETAILS[side]].astype(np.int64)
        return ResultRead(side=side, **base, **self._details(details),
                          judges=self._judges(frame[JUDGES[side]]), **self._timings(frame[TIMINGS[side]]))

    def _playmode(self, v) -> str | None:
        p = self.info["play_mode"]
        return p["table"].get(nibbles(v[to_index(p["trim"])].flatten() == p["maskvalue"]))

    def _difficulty(self, v) -> tuple[str | None, int | None]:
        d = self.info["difficulty"]
        crop = v[to_index(d["trim"])]
        packed = crop[:, :, 0] * 0x10000 + crop[:, :, 1] * 0x100 + crop[:, :, 2]
        colour = dominant(packed)
        difficulty = d["table"]["difficulty"].get(str(colour))
        if difficulty is None:
            return None, None
        key = nibbles(packed[to_index(d["trimlevel"])] == colour)
        level = d["table"]["level"].get(difficulty, {}).get(key)
        return difficulty, _int(level)

    def _notes(self, v) -> int | None:
        # Read left to right, skipping blank leading places; an unknown part after a digit is a misread.
        n = self.info["notes"]
        parts = np.hsplit(v[to_index(n["trim"])], n["digit"])
        value = 0
        for part in parts:
            key = nibbles(part[to_index(n["trimnumber"])] == n["maskvalue"])
            if key not in n["table"]:
                if value:
                    return None
                continue
            value = value * 10 + int(n["table"][key])
        return value or None

    def _title(self, v) -> str | None:
        crop = v[self._music_trim]
        bands = {}
        for band, (lower, upper, _, _) in self._bands.items():
            kept = [np.where((lower[:, :, i] <= crop[:, :, i]) & (crop[:, :, i] <= upper[:, :, i]), crop[:, :, i], 0)
                    for i in range(3)]
            if band == "gray":
                bands[band] = np.where((kept[0] == kept[1]) & (kept[0] == kept[2]), kept[0], 0)
            else:
                channel = 2 if band == "blue" else 0
                bands[band] = np.where((kept[0] != 0) & (kept[1] != 0) & (kept[2] != 0), crop[:, :, channel], 0)
        counts = {band: int(np.count_nonzero(b)) for band, b in bands.items()}
        best = max(counts.values())
        band = [b for b in ("gray", "blue", "red") if counts[b] == best][-1]  # red > blue > gray on ties
        _, _, mask, node = self._bands[band]
        masked = np.where(mask, bands[band], 0)
        for row_no, row in enumerate(masked):
            values, freq = np.unique(row, return_counts=True)
            if len(values) > 1:
                intensity = values[-int(np.argmax(np.flip(freq[1:]))) - 1]  # most frequent non-zero, last wins
                key = f"{row_no:02d}" + nibbles(row == intensity)
            else:
                key = f"{row_no:02d}"
            if not isinstance(node, dict) or key not in node:
                return None
            node = node[key]
            if isinstance(node, str):
                return node
        return None

    # --- details (one side) --------------------------------------------------------------------

    def _details(self, v) -> dict:
        d, define = self.details, self.details["define"]
        out = {}
        for key, suffix in (("current", ""), ("best", "_best")):
            out["cleartype" + suffix] = _lamp(d["clear_type"].get(str(dominant(v[to_index(define["clear_type"][key])]))))
            dj = define["dj_level"]
            out["djlevel" + suffix] = d["dj_level"].get(str(int(np.count_nonzero(v[to_index(dj[key])] == dj["maskvalue"]))))
            number = define["numberbest" if key == "best" else "numbercurrent"]
            table = d["number_best" if key == "best" else "number_current"]
            for name, field_name in (("score", "score"), ("miss_count", "misscount")):
                f = define[name]
                out[field_name + suffix] = read_digits(v[to_index(f[key])], f["digit"], to_index(number["trim"]),
                                                       number["maskvalue"], table, lambda b: nibbles_cols(b.T))
        return out

    def _counts(self, v, spec: dict, names) -> dict:
        part = to_index(spec["digittrim"])
        return {name: read_digits(v[to_index(spec["trims"][name])], spec["digitcount"], part,
                                  spec["maskvalue"], spec["table"], packbits_hex) for name in names}

    def _judges(self, v) -> dict:
        return self._counts(v, self.rr["judges"], JUDGE_NAMES)

    def _timings(self, v) -> dict:
        return self._counts(v, self.rr["timings"], ("fast", "slow"))
