"""Read the converted recognition tables (JSON only — never pickle, see CLAUDE.md)."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FIX = "Run: uv run python tools/convert_tables.py --out <tables folder>"
REQUIRED = ("screenrecognition", "musictable", "notesradar", "manifest")
SOURCE = "kaktuswald/inf-notebook"
AREA_KEYS = ("left", "top", "width", "height")


class TablesError(Exception):
    """The tables can't be used; the message says what's wrong and how to fix it."""


def _read(dir: Path, name: str) -> Any:
    path = dir / f"{name}.json"
    if not path.is_file():
        raise TablesError(f"{name}.json is missing from {dir}. {FIX}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise TablesError(f"{name}.json is not valid JSON ({e}). {FIX}") from None


@dataclass
class Tables:
    dir: Path
    manifest: dict
    screen: dict
    music: dict
    notesradar: dict
    _cache: dict = field(default_factory=dict, repr=False)

    def raw(self, name: str) -> Any:
        """Any other converted table, read on first use."""
        if name not in self._cache:
            self._cache[name] = _read(self.dir, name)
        return self._cache[name]


def load_tables(dir: Path) -> Tables:
    dir = Path(dir)
    if not dir.is_dir():
        raise TablesError(f"No tables folder at {dir}. {FIX}")
    screen, music, notesradar, manifest = (_read(dir, n) for n in REQUIRED)
    _check(manifest, screen)
    return Tables(dir=dir, manifest=manifest, screen=screen, music=music, notesradar=notesradar)


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _check(manifest: Any, screen: Any) -> None:
    """Catch tables from another source or with a shape recognition can't use, at load time."""
    source = manifest.get("source") if isinstance(manifest, dict) else None
    if source != SOURCE:
        raise TablesError(f"Tables come from an unknown source ({source!r}, expected {SOURCE}). {FIX}")
    entries = screen.get("get_screen") if isinstance(screen, dict) else None
    if not isinstance(entries, dict):
        raise TablesError(f"screenrecognition.json has no get_screen section. {FIX}")
    for name, e in entries.items():
        area = e.get("area") if isinstance(e, dict) else None
        if not isinstance(area, dict) or not all(_is_int(area.get(k)) and area[k] >= 0 for k in AREA_KEYS):
            raise TablesError(f"screenrecognition.json entry {name!r} has a bad area. {FIX}")
        if not _is_int(e.get("value")):
            raise TablesError(f"screenrecognition.json entry {name!r} has a bad value. {FIX}")
