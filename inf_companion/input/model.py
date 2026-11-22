"""Plain data types shared by the input code, storage and server."""

from dataclasses import dataclass, field
from typing import Literal

Kind = Literal["button", "axis", "hat"]

# Binding targets, in the order the binding session asks for them.
TARGETS: tuple[str, ...] = ("1", "2", "3", "4", "5", "6", "7", "S_up", "S_down")


@dataclass(frozen=True)
class Source:
    kind: Kind
    index: int
    sign: int = 0  # axis: +1 or -1
    mask: int = 0  # hat: SDL hat bitmask

    def to_json(self) -> dict:
        return {"kind": self.kind, "index": self.index, "sign": self.sign, "mask": self.mask}

    @classmethod
    def from_json(cls, d: dict) -> "Source":
        return cls(d["kind"], int(d["index"]), int(d.get("sign", 0)), int(d.get("mask", 0)))


@dataclass(frozen=True)
class Binding:
    device_guid: str
    name: str
    map: dict[str, Source] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"device_guid": self.device_guid, "name": self.name, "map": {k: v.to_json() for k, v in self.map.items()}}

    @classmethod
    def from_json(cls, d: dict) -> "Binding":
        return cls(d["device_guid"], d["name"], {k: Source.from_json(v) for k, v in d["map"].items()})


@dataclass(frozen=True)
class RawEvent:
    device_guid: str
    kind: Kind
    index: int
    value: int
    t: float  # ms, time.perf_counter() * 1000


@dataclass(frozen=True)
class KeyEvent:
    lane: str  # "S" or "1".."7"
    down: bool
    t: float
    dir: str | None = None  # scratch only: "up" or "down"


@dataclass(frozen=True)
class DeviceInfo:
    guid: str
    name: str
    bound: bool

    def to_json(self) -> dict:
        return {"guid": self.guid, "name": self.name, "bound": self.bound}
