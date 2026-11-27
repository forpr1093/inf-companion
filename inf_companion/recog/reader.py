"""Turn per-frame screen reads into the events the page needs.

A read only counts after it has been seen twice in a row, so frames caught mid-scroll or
while the result is still animating in never reach the page. The one exception: when song
select is left, the last song read there (with a known title) is sent even if it was seen
once, because scrolling fast and picking a song can leave it on screen for a single frame.
SP only: DP reads send nothing.
"""

from __future__ import annotations

from dataclasses import asdict

import numpy as np


def _off(what: str, error: Exception) -> dict:
    return {"type": "capture_status", "state": "running",
            "message": f"Reading {what} is off: the tables don't match ({type(error).__name__}: {error})"}


class Reader:
    def __init__(self, select, result, notesradar: dict, side: str):
        self.select, self.result = select, result
        self.notesradar = notesradar or {}
        self.side = side
        self._prev = None          # the previous frame's read on this screen
        self._chart_key = None     # what was last sent as the chart
        self._result_sent = False  # one result per visit to the result screen
        self._screen = None
        self._last_select = None   # the last SP read with a known title and difficulty

    def on_frame(self, frame: np.ndarray, screen: str | None) -> list[dict]:
        out: list[dict] = []
        if screen != self._screen:
            if self._screen == "music_select" and self._last_select is not None:
                out = self._send_chart(self._last_select)
            self._screen, self._prev, self._last_select = screen, None, None
            if screen != "result":
                self._result_sent = False
        if screen == "music_select" and self.select is not None:
            try:
                read = self.select.read(frame)
            except Exception as e:  # a table that doesn't match: turn this reading off, keep capturing
                self.select = None
                return out + [_off("song select", e)]
            return out + self._on_select(read)
        if screen == "result" and self.result is not None and not self._result_sent:
            try:
                read = self.result.read(frame)
            except Exception as e:
                self.result = None
                return out + [_off("result", e)]
            return out + self._on_result(read)
        return out

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
        if read.playmode == "SP" and read.difficulty is not None and read.title is not None:
            self._last_select = read
        if not self._stable(read) or read.playmode != "SP" or read.difficulty is None:
            return []
        return self._send_chart(read)

    def _send_chart(self, read) -> list[dict]:
        if read == self._chart_key:
            return []
        self._chart_key = read
        notes = self._notes(read.title, read.difficulty)
        chart = {"title": read.title, "artist": None, "difficulty": read.difficulty, "level": read.level,
                 "bpm": None, "notes": notes}
        unplayed = read.score is None or (read.score == 0 and read.cleartype in (None, "NO PLAY"))
        best = None if unplayed else {
            "score": read.score, "notes": notes, "lamp": read.cleartype, "miss_count": read.misscount,
            "last_played": None, "source": "official"}
        return [{"type": "chart", "chart": chart}, {"type": "personal_best", "best": best}]

    def _on_result(self, read) -> list[dict]:
        if not self._stable(read) or not read.complete or read.playmode != "SP":
            return []
        self._result_sent = True
        return [{"type": "result", "result": asdict(read)}]
