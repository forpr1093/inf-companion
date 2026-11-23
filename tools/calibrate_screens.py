"""Calibrate screen recognition against labelled screenshots.

  uv run python tools/calibrate_screens.py [--tables tables] [--fixtures tests/fixtures/screens]

Prints, for every fixture, how far its area key is from each get_screen entry in both
orientations, then scores candidate play crops by average-hash distance (play fixtures
should sit close to the reference, everything else far away). Read the output, then set
SCREEN_ORIENTATION / SCREEN_TOLERANCE in inf_companion/recog/screen.py and write
inf_companion/recog/refs/play.json (use --write-play to do the latter).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inf_companion.capture.base import normalise  # noqa: E402
from inf_companion.recog.screen import REFS, area_key, average_hash, hamming  # noqa: E402
from inf_companion.tables.load import load_tables  # noqa: E402

# Candidate play crops (1P, FHD), most robust first: the first one that separates cleanly
# is used. The score labels belong to the lane frame and are always shown; the graph panel
# can be turned off in-game, so it comes last.
PLAY_CANDIDATES = {
    "1P": {
        "score_labels": {"left": 140, "top": 950, "width": 380, "height": 22},
        "left_frame": {"left": 0, "top": 0, "width": 75, "height": 1050},
        "bottom_left_panel": {"left": 0, "top": 860, "width": 520, "height": 220},
        "graph_header": {"left": 545, "top": 0, "width": 410, "height": 18},
    },
}


def fixtures(root: Path) -> list[tuple[str, Path]]:
    return [(p.parent.name, p) for p in sorted(root.glob("*/*.png"))]


def report_keys(tables, items) -> None:
    entries = tables.screen["get_screen"]
    for orientation in ("as_is", "flipped"):
        print(f"\n== area keys, {orientation} (distance to each entry; * = own label) ==")
        for label, path in items:
            frame = normalise(Image.open(path))
            cells = []
            for name, e in entries.items():
                d = abs(area_key(frame, e["area"], orientation) - e["value"])
                cells.append(f"{name}{'*' if name == label else ''}={d}")
            print(f"{label}/{path.name}: " + " ".join(cells))


def report_play(items, side: str) -> dict | None:
    best = None
    print(f"\n== play crops, {side} (reference = first play_{side.lower()} fixture) ==")
    plays = [p for label, p in items if label == f"play_{side.lower()}"]
    others = [p for label, p in items if not label.startswith("play_")]
    if not plays:
        print("no play fixtures for this side")
        return None
    for name, area in PLAY_CANDIDATES[side].items():
        hashes = {p: average_hash(crop(normalise(Image.open(p)), area)) for p in plays + others}
        ref = hashes[plays[0]]
        within = max(hamming(ref, hashes[p]) for p in plays)
        apart = min((hamming(ref, hashes[p]) for p in others), default=256)
        ok = within <= 10 and apart > 20
        print(f"{name:20s} within={within:3d} nearest_other={apart:3d} {'OK' if ok else '-'}")
        if ok and best is None:
            best = {"area": area, "hash": ref}
    return best


def crop(frame, area):
    return frame[area["top"]:area["top"] + area["height"], area["left"]:area["left"] + area["width"]]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tables", default="tables")
    ap.add_argument("--fixtures", default="tests/fixtures/screens")
    ap.add_argument("--write-play", action="store_true", help="write the best play crops to refs/play.json")
    a = ap.parse_args(argv)
    tables = load_tables(Path(a.tables))
    items = fixtures(Path(a.fixtures))
    report_keys(tables, items)
    refs = {"max_distance": 10}
    for side in PLAY_CANDIDATES:
        best = report_play(items, side)
        if best:
            refs[side] = best
    if a.write_play:
        (REFS / "play.json").write_text(json.dumps(refs, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {REFS / 'play.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
