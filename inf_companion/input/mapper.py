"""Turns raw controller events into lane key events, using the saved bindings.

Pure logic: no SDL, no clocks. The input thread feeds events and calls `tick` often.
"""

from dataclasses import dataclass

from inf_companion.input.model import Binding, KeyEvent, RawEvent

AXIS_RANGE = 65536


def wrap_delta(new: int, old: int) -> int:
    """Axis change, treating the int16 range as a circle (turntables wrap around)."""
    return ((new - old + 32768) % AXIS_RANGE) - 32768


def _lane_of(target: str) -> tuple[str, str | None]:
    if target == "S_up":
        return "S", "up"
    if target == "S_down":
        return "S", "down"
    return target, None


@dataclass
class _AxisState:
    last: int
    acc: int = 0  # motion not yet counted toward a direction change
    held: int = 0  # +1 / -1 / 0
    last_motion_t: float = 0.0


class InputMapper:
    def __init__(self, bindings: dict[str, Binding], axis_deadband: int = 64, scratch_release_ms: float = 80.0):
        self.axis_deadband = axis_deadband
        self.scratch_release_ms = scratch_release_ms
        self._bindings: dict[str, Binding] = {}
        self._down: dict[tuple[str, str, str | None], str] = {}  # (guid, lane, dir) -> lane key, held
        self._axes: dict[tuple[str, int], _AxisState] = {}
        self.set_bindings(bindings)

    def set_bindings(self, bindings: dict[str, Binding]) -> None:
        self._bindings = dict(bindings)

    # -- helpers ----------------------------------------------------------------
    def _press(self, guid: str, target: str, t: float) -> list[KeyEvent]:
        lane, d = _lane_of(target)
        key = (guid, lane, d)
        if key in self._down:
            return []
        self._down[key] = lane
        return [KeyEvent(lane, True, t, d)]

    def _release(self, guid: str, target: str, t: float) -> list[KeyEvent]:
        lane, d = _lane_of(target)
        key = (guid, lane, d)
        if key not in self._down:
            return []
        del self._down[key]
        return [KeyEvent(lane, False, t, d)]

    # -- public -----------------------------------------------------------------
    def feed(self, ev: RawEvent) -> list[KeyEvent]:
        binding = self._bindings.get(ev.device_guid)
        if binding is None:
            return []
        if ev.kind == "axis":
            return self._feed_axis(binding, ev)
        out: list[KeyEvent] = []
        for target, src in binding.map.items():
            if src.kind != ev.kind or src.index != ev.index:
                continue
            pressed = (ev.value == 1) if ev.kind == "button" else bool(ev.value & src.mask)
            out += self._press(ev.device_guid, target, ev.t) if pressed else self._release(ev.device_guid, target, ev.t)
        return out

    def _feed_axis(self, binding: Binding, ev: RawEvent) -> list[KeyEvent]:
        targets = {src.sign: target for target, src in binding.map.items() if src.kind == "axis" and src.index == ev.index}
        if not targets:
            return []
        key = (ev.device_guid, ev.index)
        st = self._axes.get(key)
        if st is None:
            self._axes[key] = _AxisState(last=ev.value)
            return []
        delta = wrap_delta(ev.value, st.last)
        st.last = ev.value
        if delta == 0:
            return []
        sign = 1 if delta > 0 else -1
        if sign == st.held:
            st.acc = 0
            st.last_motion_t = ev.t
            return []
        st.acc += delta
        if abs(st.acc) <= self.axis_deadband or (st.acc > 0) != (sign > 0):
            return []
        out: list[KeyEvent] = []
        if st.held and st.held in targets:
            out += self._release(ev.device_guid, targets[st.held], ev.t)
        st.held, st.acc, st.last_motion_t = sign, 0, ev.t
        if sign in targets:
            out += self._press(ev.device_guid, targets[sign], ev.t)
        return out

    def tick(self, t: float) -> list[KeyEvent]:
        out: list[KeyEvent] = []
        for (guid, index), st in self._axes.items():
            if st.held and t - st.last_motion_t >= self.scratch_release_ms:
                binding = self._bindings.get(guid)
                if binding:
                    for target, src in binding.map.items():
                        if src.kind == "axis" and src.index == index and src.sign == st.held:
                            out += self._release(guid, target, t)
                st.held, st.acc = 0, 0
        return out

    def release_device(self, guid: str, t: float) -> list[KeyEvent]:
        out = [KeyEvent(lane, False, t, d) for (g, lane, d) in list(self._down) if g == guid]
        for k in [k for k in self._down if k[0] == guid]:
            del self._down[k]
        for k in [k for k in self._axes if k[0] == guid]:
            del self._axes[k]
        return out

    def release_all(self, t: float) -> list[KeyEvent]:
        out = [KeyEvent(lane, False, t, d) for (_, lane, d) in self._down]
        self._down.clear()
        for st in self._axes.values():
            st.held, st.acc = 0, 0
        return out
