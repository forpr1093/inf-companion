"""Read the converted recognition tables (JSON only — never pickle, see CLAUDE.md)."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FIX = "Run: uv run python tools/convert_tables.py --out <tables folder>"
REQUIRED = ("screenrecognition", "musictable", "notesradar", "manifest")


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
    return Tables(dir=dir, manifest=manifest, screen=screen, music=music, notesradar=notesradar)
