"""Per-button press counts for the counter panel. In memory only: resets on app start."""

from inf_companion.input.model import TARGETS, KeyEvent


def counter_target(ev: KeyEvent) -> str:
    if ev.lane == "S":
        return "S_down" if ev.dir == "down" else "S_up"
    return ev.lane


class PressCounter:
    def __init__(self) -> None:
        self._counts = {t: 0 for t in TARGETS}

    def add(self, ev: KeyEvent) -> None:
        if ev.down:
            target = counter_target(ev)
            if target in self._counts:
                self._counts[target] += 1

    def snapshot(self) -> dict[str, int]:
        return dict(self._counts)

    def reset(self) -> None:
        self._counts = {t: 0 for t in TARGETS}
