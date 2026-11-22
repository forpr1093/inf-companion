"""The "press key 1 … key 7, scratch up, scratch down" binding flow. Pure logic."""

from inf_companion.input.mapper import wrap_delta
from inf_companion.input.model import TARGETS, Binding, RawEvent, Source


class BindingSession:
    def __init__(self, device_names: dict[str, str], axis_trigger: int = 4000):
        self._names = device_names
        self.axis_trigger = axis_trigger
        self.index = 0
        self._guid: str | None = None
        self._map: dict[str, Source] = {}
        self._axis_last: dict[int, int] = {}
        self._axis_sum: dict[int, int] = {}

    @property
    def current_target(self) -> str | None:
        return TARGETS[self.index] if self.index < len(TARGETS) else None

    def _source_for(self, ev: RawEvent) -> Source | None:
        if ev.kind == "button":
            return Source("button", ev.index) if ev.value == 1 else None
        if ev.kind == "hat":
            return Source("hat", ev.index, mask=ev.value) if ev.value != 0 else None
        last = self._axis_last.get(ev.index)
        self._axis_last[ev.index] = ev.value
        if last is None:
            return None
        total = self._axis_sum.get(ev.index, 0) + wrap_delta(ev.value, last)
        self._axis_sum[ev.index] = total
        if abs(total) < self.axis_trigger:
            return None
        self._axis_sum.clear()
        return Source("axis", ev.index, sign=1 if total > 0 else -1)

    def feed(self, ev: RawEvent) -> Binding | None:
        if self.current_target is None:
            return None
        if self._guid is not None and ev.device_guid != self._guid:
            return None
        src = self._source_for(ev)
        if src is None or src in self._map.values():
            return None
        self._guid = ev.device_guid
        self._map[self.current_target] = src
        self.index += 1
        if self.current_target is None:
            return Binding(self._guid, self._names.get(self._guid, self._guid), dict(self._map))
        return None
