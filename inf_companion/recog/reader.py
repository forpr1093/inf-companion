"""Turn per-frame screen reads into the events the page needs.

A read only counts after it has been seen twice in a row, so frames caught mid-scroll or
while the result is still animating in never reach the page. SP only: DP reads send nothing.
"""

from __future__ import annotations

from dataclasses import asdict

import numpy as np


class Reader:
    def __init__(self, select, result, notesradar: dict, side: str):
        self.select, self.result = select, result
        self.notesradar = notesradar or {}
        self.side = side
        self._prev = None          # the previous frame's read on this screen
        self._chart_key = None     # what was last sent as the chart
        self._result_sent = False  # one result per visit to the result screen
        self._screen = None

    def on_frame(self, frame: np.ndarray, screen: str | None) -> list[dict]:
        if screen != self._screen:
            self._screen, self._prev = screen, None
            if screen != "result":
                self._result_sent = False
        if screen == "music_select" and self.select is not None:
            return self._on_select(self.select.read(frame))
        if screen == "result" and self.result is not None and not self._result_sent:
            return self._on_result(self.result.read(frame))
        return []

    def _stable(self, read) -> bool:
        same = read == self._prev
        self._prev = read
        return same

    def _notes(self, title, difficulty) -> int | None:
        try:
            return int(self.notesradar["SP"]["musics"][title][difficulty]["notes"])
        except (KeyError, TypeError, ValueError):
            return None

    def _on_select(self, read) -> list[dict]:
        if not self._stable(read) or read.playmode != "SP" or read.difficulty is None:
            return []
        if read == self._chart_key:
            return []
        self._chart_key = read
        notes = self._notes(read.title, read.difficulty)
        chart = {"title": read.title, "artist": None, "difficulty": read.difficulty, "level": read.level,
                 "bpm": None, "notes": notes}
        best = None if read.score is None else {
            "score": read.score, "notes": notes, "lamp": read.cleartype, "miss_count": read.misscount,
            "last_played": None, "source": "official"}
        return [{"type": "chart", "chart": chart}, {"type": "personal_best", "best": best}]

    def _on_result(self, read) -> list[dict]:
        if not self._stable(read) or not read.complete or read.playmode != "SP":
            return []
        self._result_sent = True
        return [{"type": "result", "result": asdict(read)}]
