"""Download inf-notebook's recognition tables and convert them to JSON, safely.

The tables are (gzipped) pickle files. This is the only place in the project that unpickles
anything, and it never runs code the file asks for: the unpickler accepts exactly six named
globals (see CLAUDE.md), each mapped to our own inert stand-in that turns the data into plain
numbers and lists. numpy is never imported. Every other global is refused.

  uv run python tools/convert_tables.py [--out tables] [--commit <sha>]

The app only reads the JSON this writes. Never commit the .res files or the output.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import pickle
import struct
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PINNED = "f43158edfb65006c976ed7785cfa7b066c3ffcf4"
SOURCE = "kaktuswald/inf-notebook"

# Our name -> the file name in inf-notebook's resources/ folder (without .res).
TABLES = {
    "screenrecognition": "screenrecognition1.0",
    "musictable": "musictable1.2",
    "notesradar": "notesradar1.2",
    "musicselect": "musicselect2.3",
    "informations": "informations4.1",
    "details": "details3.2",
    "resultothers": "resultothers1.0",
    "resultrecognition": "resultrecognition1.0",
    "deeper": "deeper0.3",
    "musicnamechanges": "musicnamechanges",
}

_FORMATS = {("u", 1): "B", ("u", 2): "H", ("u", 4): "I", ("u", 8): "Q",
            ("i", 1): "b", ("i", 2): "h", ("i", 4): "i", ("i", 8): "q",
            ("f", 4): "f", ("f", 8): "d", ("b", 1): "?"}


# --- inert stand-ins ---------------------------------------------------------------------------

class SliceStub:
    def __init__(self, start: Any, stop: Any, step: Any):
        self.items = [start, stop, step]


def make_slice(*args: Any) -> SliceStub:
    if len(args) == 1:
        return SliceStub(None, args[0], None)
    if len(args) in (2, 3):
        return SliceStub(args[0], args[1], args[2] if len(args) == 3 else None)
    raise ValueError(f"slice takes 1 to 3 arguments, got {len(args)}")


class DtypeStub:
    """Stands in for numpy.dtype: only plain numbers (u, i, f, b) of 1/2/4/8 bytes."""

    def __init__(self, *args: Any):
        if not args or not isinstance(args[0], str):
            raise ValueError("dtype needs a type string")
        spec = args[0].lstrip("<>|=")
        kind, size = spec[:1], spec[1:]
        if not size.isdigit() or (kind, int(size)) not in _FORMATS:
            raise ValueError(f"unsupported dtype {args[0]!r}")
        self.kind, self.size, self.order = kind, int(size), "<"

    @classmethod
    def from_spec(cls, spec: str) -> "DtypeStub":
        return cls(spec)

    def __setstate__(self, state: Any) -> None:
        # numpy's state is (version, byte order, ...). "|" (not applicable) and "=" mean native.
        if not isinstance(state, tuple) or len(state) < 2 or state[1] not in "<>|=":
            raise ValueError("unexpected dtype state")
        self.order = ">" if state[1] == ">" else "<"

    @property
    def code(self) -> str:
        return f"{'|' if self.size == 1 else self.order}{self.kind}{self.size}"

    def unpack(self, raw: bytes, count: int) -> list:
        if not isinstance(raw, (bytes, bytearray)) or len(raw) != count * self.size:
            raise ValueError(f"expected {count * self.size} bytes for {count} × {self.code}")
        return list(struct.unpack(f"{self.order}{count}{_FORMATS[(self.kind, self.size)]}", raw))


class NdArrayMarker:
    """Stands in for numpy.ndarray: only accepted as _reconstruct's first argument."""


class ArrayStub:
    def __init__(self, dtype: DtypeStub | None = None, shape: tuple = (), flat: list | None = None):
        self.dtype, self.shape, self.flat = dtype, tuple(shape), flat

    def __setstate__(self, state: Any) -> None:
        # ndarray state: (version, shape, dtype, is_fortran, raw bytes)
        if not isinstance(state, tuple) or len(state) != 5:
            raise ValueError("unexpected ndarray state")
        _, shape, dtype, fortran, raw = state
        _fill(self, dtype, shape, raw, fortran)


def _shape(shape: Any) -> tuple[int, ...]:
    if not isinstance(shape, (tuple, list)) or not all(isinstance(n, int) and n >= 0 for n in shape):
        raise ValueError("array shape must be a tuple of non-negative ints")
    return tuple(shape)


def _fill(arr: ArrayStub, dtype: Any, shape: Any, raw: Any, fortran: bool) -> ArrayStub:
    if not isinstance(dtype, DtypeStub):
        raise ValueError("array dtype is not a dtype")
    if fortran:
        raise ValueError("Fortran-ordered arrays are not supported")
    shape = _shape(shape)
    arr.dtype, arr.shape, arr.flat = dtype, shape, dtype.unpack(raw, math.prod(shape))
    return arr


def scalar(dtype: Any, raw: Any) -> int | float | bool:
    if not isinstance(dtype, DtypeStub):
        raise ValueError("scalar dtype is not a dtype")
    return dtype.unpack(raw, 1)[0]


def frombuffer(buf: Any, dtype: Any, shape: Any = None, order: str = "C") -> ArrayStub:
    if order not in ("C", "F"):
        raise ValueError(f"unknown order {order!r}")
    if not isinstance(dtype, DtypeStub):
        raise ValueError("frombuffer dtype is not a dtype")
    if shape is None:
        shape = (len(buf) // dtype.size,)
    return _fill(ArrayStub(), dtype, shape, buf, order == "F")


def reconstruct(cls: Any, shape: Any, typecode: Any) -> ArrayStub:
    if cls is not NdArrayMarker:
        raise ValueError("_reconstruct is only allowed for ndarray")
    return ArrayStub()


ALLOWED: dict[tuple[str, str], Any] = {
    ("builtins", "slice"): make_slice,
    ("numpy", "dtype"): DtypeStub,
    ("numpy._core.multiarray", "scalar"): scalar,
    ("numpy._core.numeric", "_frombuffer"): frombuffer,
    ("numpy._core.multiarray", "_reconstruct"): reconstruct,
    ("numpy", "ndarray"): NdArrayMarker,
}


class _Unpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str) -> Any:
        try:
            return ALLOWED[(module, name)]
        except KeyError:
            raise pickle.UnpicklingError(f"refused global {module}.{name}") from None


def safe_load(data: bytes) -> Any:
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return _Unpickler(io.BytesIO(data)).load()


# --- to plain JSON -----------------------------------------------------------------------------

def _nest(flat: list, shape: tuple[int, ...]) -> Any:
    if not shape:
        return flat[0] if flat else None
    if len(shape) == 1:
        return flat
    step = math.prod(shape[1:])
    return [_nest(flat[i * step:(i + 1) * step], shape[1:]) for i in range(shape[0])]


def to_json(obj: Any) -> Any:
    if isinstance(obj, SliceStub):
        return {"slice": obj.items}
    if isinstance(obj, ArrayStub):
        if obj.dtype is None:
            raise ValueError("array was never filled in")
        return {"array": _nest(obj.flat, obj.shape), "dtype": obj.dtype.code, "shape": list(obj.shape)}
    if isinstance(obj, DtypeStub):
        return obj.code
    if isinstance(obj, dict):
        return {k if isinstance(k, str) else json.dumps(to_json(k)): to_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_json(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted((to_json(v) for v in obj), key=repr)
    if isinstance(obj, (bytes, bytearray)):
        return {"bytes": bytes(obj).hex()}
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    raise ValueError(f"unexpected value of type {type(obj).__name__}")


# --- fetch and convert -------------------------------------------------------------------------

def fetch_raw(name: str, commit: str) -> bytes:
    url = f"https://raw.githubusercontent.com/{SOURCE}/{commit}/resources/{TABLES.get(name, name)}.res"
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read()


def convert(names: list[str], out_dir: Path, commit: str = PINNED,
            fetch: Callable[[str, str], bytes] = fetch_raw) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in names:
        data = fetch(name, commit)
        value = json.loads(data) if data.lstrip()[:1] in (b"[", b"{") else to_json(safe_load(data))
        (out_dir / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        files[name] = {"sha256_res": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    manifest = {"source": SOURCE, "commit": commit,
                "converted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "files": files}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="tables")
    ap.add_argument("--commit", default=PINNED)
    ap.add_argument("--only", nargs="*", choices=sorted(TABLES), help="convert just these tables")
    a = ap.parse_args(argv)
    names = a.only or list(TABLES)
    m = convert(names, Path(a.out), a.commit)
    for name, f in m["files"].items():
        print(f"{name:20s} {f['bytes']:>8d} bytes -> {Path(a.out) / (name + '.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
