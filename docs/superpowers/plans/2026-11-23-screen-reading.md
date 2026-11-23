# Screen Reading (Plan 3a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Read the song-select and result screens from the converted inf-notebook tables, send the current chart, personal best and result to the page, and record labelled frames for later calibration.

**Architecture:** A small set of packing primitives (`recog/pack.py`) reproduces the reference keys: crop → mask → hex → table/trie. `recog/select.py` and `recog/result.py` read one frame each into frozen dataclasses. Tables are compiled once into numpy indexes and arrays. In the capture child, a `Reader` runs after classification. It emits `chart`, `personal_best` and `result` only after the same read has been seen twice in a row. A `FrameRecorder` can save frames by screen label. Nothing here touches input or the server loop.

**Tech Stack:** Python 3.12, numpy, Pillow, pytest; Svelte 5 for one small page change.

**Spec:** `docs/superpowers/specs/2026-11-23-infinitas-companion-design.md` (§5.2 song select / result reading, §5.3 song metadata, §5.7 event types, §8 performance).

## Global Constraints

- Re-implement inf-notebook's method; don't copy its code. Its `recog.py` was read only to learn the semantics recorded below (pinned commit `f43158edfb65006c976ed7785cfa7b066c3ffcf4`).
- The app reads only the converted JSON; never pickle at runtime. Never commit `tables/`.
- No OpenCV. numpy + Pillow only.
- The game comes first: reading runs in the capture child, on crops only, at the existing adaptive rate.
- SP only: a DP read emits nothing except the screen.
- Frames are `(1080, 1920, 3)` uint8 **RGB** (`capture.base.normalise`). Calibrated 2026-11-23: the tables match RGB, not BGR.
- **Lamp names on the wire use the official CSV spelling** (checked against the user's export, 2026-11-23). Map the table names with `LAMPS` in `recog/pack.py`:
  - `NO PLAY` and `FAILED` stay as they are
  - `A-CLEAR` → `ASSIST CLEAR`, `E-CLEAR` → `EASY CLEAR`, `CLEAR` stays
  - `H-CLEAR` → `HARD CLEAR`, `EXH-CLEAR` → `EX HARD CLEAR`, `F-COMBO` → `FULLCOMBO CLEAR`

  The readers return these mapped names.

## Semantics (calibrated against the user's fixtures 2026-11-23)

These were found by a throwaway prototype; every value below was read correctly from `tests/fixtures/screens/`:

| Item | Source | Notes |
|---|---|---|
| song-select view | full frame `[135:952, 48:1188]` | every `musicselect` trim is relative to this crop |
| result informations view | `[910:1066, 560:1360]` | `informations` trims |
| result details view | 1P `[64:1016, 10:564]`, 2P `[64:1016, 1360:1914]` | `details` trims; the side comes from `details_side` below |
| result judges view | 1P `[780:920, 293:503]`, 2P `[780:920, 1642:1852]` | `resultrecognition.judges` |
| result timings view | 1P `[959:1015, 30:294]`, 2P `[959:1015, 1374:1638]` | `resultrecognition.timings` |
| details side | details view `[5, 4:548:8, 0] == 150` → nibble key; `0fffffffffffffffe` = 1P, `7fffffffffffffff0` = 2P | None while the result is still animating in |
| JSON trim | list whose items are `{"slice": [a, b, c]}` or ints | `to_index` turns it into a numpy index tuple |
| int-keyed tables | keys are decimal strings (`"198"`) | look up with `str(int(v))` |

Key packing (bits are 0/1 ints):
- `nibbles(bits)`: flatten row-major, then `b[0::4]*8 + b[1::4]*4 + b[2::4]*2 + b[3::4]`, each value as one lowercase hex digit.
- `nibbles_cols(bits2d)`: `b[:,0::4]*8 + b[:,1::4]*4 + b[:,2::4]*2 + b[:,3::4]` **with numpy broadcasting**, then flatten. When the width isn't a multiple of 4, the narrower slices broadcast. This is required for result digits (6×2 → transposed 2×6), and it gives different keys from `nibbles`.
- `packbits_hex(bits)`: `np.packbits(bits.astype(uint8)).tobytes().hex()` (judges and timings).
- Digits: split the field into `digit` equal parts with `np.hsplit` and read from the right. Stop at the first part whose key isn't in the table. If no digit matched, the value is None.
- Song-select title: the `infinitas` table (thresholds per channel, AND, one key per row via `nibbles`), then `leggendaria`, then `arcade`. Arcade takes gray pixels only (R==G==B), uses a per-row threshold on that gray value, then halves each row with `row[::2] & row[1::2]` before `nibbles`. The trie walk stops at the first `str`.
- Result title: three colour bands (blue, red, gray) from `factors.{band}.{lower,upper}` (per pixel, per channel, inclusive). Blue keeps channel 2 where all three channels are in range, red keeps channel 0, and gray keeps channel 0 where the three in-range values are equal. Pick the band with the most non-zero pixels; on a tie, red beats blue beats gray. Apply `masks.{band}`. For each row h: if the row has more than one distinct value, the intensity is the most frequent non-zero value, with the **last** one winning ties (`-argmax(flip(counts[1:])) - 1`). The key is `f"{h:02d}" + nibbles(row == intensity)`; otherwise it's just `f"{h:02d}"`. Walk `tables.{band}`.
- Clear type (select and result): the most frequent value in the trim (`np.unique`, first max) looked up as `str(int(v))`. DJ level: the count of pixels equal to `maskvalue`, looked up as a string.
- Select difficulty and level: for each difficulty in `levels.select`, mask with per-channel thresholds, then `nibbles_cols`. The first difficulty whose key is in its table gives `(difficulty, level)`.
- Select score and miss count: `musicselect.number`, with `.T` before `nibbles_cols`.
- Result difficulty and level: pack each pixel to `R<<16 | G<<8 | B`. The most frequent value names the difficulty, and `nibbles(trimlevel == that value)` gives the level.
- Result score and miss count: `details.define.{score,miss_count}.{best,current}`, digit trim `numberbest` / `numbercurrent`, `.T`, then `nibbles_cols`, using the tables `number_best` / `number_current`.
- Play mode: `nibbles(trim.flatten() == maskvalue)`, giving `"SP"` or `"DP"`.

Fixture truth (the user's Mermaid girl captures):
- **Select:** SP, `Mermaid girl`, HYPER 8, HARD CLEAR, AA, score 1437, miss 8. This matches the user's official CSV (HYPER 1437 / 8 / HARD CLEAR).
- **Result `dxcam_max_0012`:**
  - 1P, SP, `Mermaid girl`, HYPER 8
  - clear CLEAR (best HARD CLEAR), DJ A (best AA)
  - score 1228 (best 1437), miss 14 (best 8)
  - PG 485, GR 258, GD 100, BD 4, PR 10
- **Result `dxcam_max_0008`:** the side is None (still animating in).

## Review Focus

1. **Song-select frames mid-scroll or mid-animation** give partial or wrong reads. A chart is sent only after two identical reads in a row. Test: Task 4 `test_chart_needs_two_equal_reads`.
2. **A result still animating in** (side None, or digits missing) never sends a result. It's sent once, after a complete read repeats. Tests: Task 3 `test_result_animating_is_incomplete`, Task 4 `test_result_sent_once_when_complete`.
3. **DP charts** send nothing beyond the screen. Test: Task 4 `test_dp_sends_nothing`.
4. **A title missing from the tables** still sends the chart with `title: null`, so the page shows the difficulty and level. Test: Task 4 `test_unknown_title_still_sent`.
5. **Recorder failures** (unwritable folder, disk full) never stop capture; the recorder turns itself off and says so once. Test: Task 5 `test_recorder_failure_turns_off`.

---

### Task 1: Packing primitives and compiled tables

**Files:**
- Create: `inf_companion/recog/pack.py`, `tests/recog/test_pack.py`

**Interfaces:**
- Produces: `LAMPS: dict[str, str]`, `to_index(trim: list) -> tuple`, `nibbles(bits) -> str`, `nibbles_cols(bits2d) -> str`, `packbits_hex(bits) -> str`, `walk(trie: dict, keys: Iterable[str]) -> str | None`, `in_ranges(img, ranges: list[list[int]]) -> np.ndarray[bool]` (per-channel inclusive, ANDed), `dominant(a) -> int`, `read_digits(field, count, part_index, mask, table, packer) -> int | None`, `as_array(json_array: dict) -> np.ndarray` (from `{"array","dtype","shape"}`).

- [ ] **Step 1: Write the failing tests:**
  - `test_to_index_slices_and_ints`: `to_index([{"slice":[1,5,2]}, 3])` gives `(slice(1,5,2), 3)`.
  - `test_nibbles`: `[1,0,1,1, 0,0,0,1]` gives `"b1"`.
  - `test_nibbles_cols_broadcasts`: a 2×6 array of ones gives `nibbles_cols` = `"ffff"` (each row is `[15, 15]`: the width-1 `2::4` and `3::4` slices broadcast onto both columns), and `nibbles` of the same array gives `"fff"`.
  - `test_packbits_hex`: `packbits_hex([1]*8+[0]*8)` gives `"ff00"`.
  - `test_walk_stops_at_str`: walks a nested dict to a string; a missing key gives None.
  - `test_in_ranges`: per-channel bounds with both edges inclusive.
  - `test_dominant_first_max`: equal counts give the smaller value (`np.unique` order).
  - `test_lamps_use_official_names`: `LAMPS["H-CLEAR"] == "HARD CLEAR"`, `LAMPS["F-COMBO"] == "FULLCOMBO CLEAR"`; every value in `details.clear_type` and `musicselect.cleartype` maps (skipped without tables).
  - `test_read_digits_right_to_left_stops_on_unknown`: a synthetic field of 4 parts reads `"_12"` as 12 and an all-unknown field as None.
- [ ] **Step 2:** Run `uv run pytest tests/recog/test_pack.py -q`. Expected: FAIL (module missing).
- [ ] **Step 3:** Implement `pack.py`.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit `feat(recog): key packing primitives`.

### Task 2: Song-select reader

**Files:**
- Create: `inf_companion/recog/select.py`, `tests/recog/test_select.py`

**Interfaces:**
- Consumes: Task 1, `Tables.raw("musicselect")`.
- Produces:
  - `SelectRead(playmode, title, difficulty, level: int|None, cleartype, djlevel, score: int|None, misscount: int|None)`, a frozen dataclass. `difficulty` is upper case (`"HYPER"`).
  - `SelectReader(tables)` compiles the trims once. `read(frame) -> SelectRead`. A missing table raises `TablesError` in `__init__`.

- [ ] **Step 1: Write the failing tests:**
  - `test_reads_every_select_fixture`: parametrised over `tests/fixtures/screens/music_select/*.png` (skipped without tables). Each gives `SelectRead("SP", "Mermaid girl", "HYPER", 8, "HARD CLEAR", "AA", 1437, 8)`.
  - `test_black_frame_reads_nothing`: every field is None.
  - `test_bgr_frame_does_not_read_playmode`: a channel-swapped fixture gives `playmode` None. This pins the RGB calibration.
- [ ] **Step 2:** FAIL. **Step 3:** Implement it, following the Semantics table. **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat(recog): read song select from tables`.

### Task 3: Result reader

**Files:**
- Create: `inf_companion/recog/result.py`, `tests/recog/test_result.py`

**Interfaces:**
- Consumes: Task 1, `Tables.raw("informations" | "details" | "resultrecognition")`.
- Produces:
  - `ResultRead(side, playmode, title, difficulty, level: int|None, notes: int|None, cleartype, cleartype_best, djlevel, djlevel_best, score, score_best, misscount, misscount_best, judges: dict[str,int|None], fast: int|None, slow: int|None)`, frozen.
  - `ResultRead.complete -> bool`: side, playmode, difficulty, cleartype and score are all not None.
  - `ResultReader(tables).read(frame) -> ResultRead`. With no side, it returns a `ResultRead` with only `side=None` and the informations fields filled.

- [ ] **Step 1: Write the failing tests:**
  - `test_reads_result_fixture`: `dxcam_max_0012` gives the fixture truth above, including judges `{"pgreat":485,"great":258,"good":100,"bad":4,"poor":10}`. `complete` is True.
  - `test_result_animating_is_incomplete`: `dxcam_max_0008` gives side None and `complete` False, but the title still reads `Mermaid girl`.
  - `test_score_needs_broadcast_packing`: monkeypatch `nibbles_cols` to `nibbles`, then `score` is None. This shows why the quirk is kept.
  - `test_black_frame_incomplete`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement it. Fill `fast`/`slow` from `resultrecognition.timings` with the same digit rule. **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat(recog): read result screen from tables`.

### Task 4: Reader in the capture loop, events to the page

**Files:**
- Create: `inf_companion/recog/reader.py`, `tests/recog/test_reader.py`
- Modify:
  - `inf_companion/capture/process.py`: `capture_loop` takes an optional `on_frame(frame, screen) -> list[dict]`; the child builds a `Reader`; `CaptureHandle` keeps the last `chart` / `personal_best` / `result`.
  - `inf_companion/server/app.py`: `hello` carries `chart` and `personal_best`.
  - `web/src/lib/events.ts`, `web/src/lib/stores.ts`: `hello` sets `nowPlaying` / `personalBest`; `Chart.title` and `Chart.level` may be null.
  - `web/src/display/NowPlaying.svelte`: a null title shows "Unknown title".
  - `tests/capture/test_process.py`, `tests/test_server.py`, `web` store tests.

**Interfaces:**
- Consumes: Tasks 2–3, `Tables.notesradar`, `capture_loop`.
- Produces:
  - `Reader(select: SelectReader|None, result: ResultReader|None, notesradar: dict, side: str)`.
  - `Reader.on_frame(frame, screen) -> list[dict]`, returning wire messages (without `at`):
    - On `music_select`: after two equal `SelectRead`s in a row with `playmode == "SP"` and a difficulty, and only when it differs from the last chart sent, send `{"type":"chart","chart":{title, artist: None, difficulty, level, bpm: None, notes}}` and `{"type":"personal_best","best":{score, notes, lamp: cleartype, miss_count, last_played: None, source: "official"}}`. If there is no score, send `"best": None`. `notes` comes from `notesradar["SP"]["musics"][title][difficulty]["notes"]`, or None.
    - On `result`: send `{"type":"result","result":asdict(read)}` once per visit to the result screen, after two equal complete reads with `playmode == "SP"`. Leaving the result screen re-arms it.
    - Other screens: nothing. They reset the select pair so stale reads don't count.
  - The child builds the readers from `Tables.raw`. If a table is missing, that reader is None and the running status message says which reading is off.

- [ ] **Step 1: Write the failing tests** (use stub readers that return queued reads):
  - `test_chart_needs_two_equal_reads`: reads A, B, B send one chart (B).
  - `test_chart_not_repeated`: B, B, B, B sends once.
  - `test_dp_sends_nothing`.
  - `test_unknown_title_still_sent`: title None gives a chart with `title: None` and `notes: None`.
  - `test_result_sent_once_when_complete`: incomplete, then complete, complete, complete sends one result; going to `play` and back to `result` with a new read sends again.
  - `test_notes_from_notesradar`.
  - `test_capture_loop_forwards_on_frame_messages`.
  - `test_hello_carries_chart`.
  - Web: `applyEvent(hello with chart)` sets `nowPlaying`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement it, then rebuild the page (`cd web && npm run build`). **Step 4:** PASS. Run `uv run pytest -q` and `cd web && npx vitest run && npx svelte-check --threshold error`.
- [ ] **Step 5:** Manual: replay a folder made from music_select, then play, then result fixtures (`--capture replay --source … --replay-fps 2`). The page shows Mermaid girl HYPER 8 with personal best AA 1437; the server log, or a websocket client, sees one `result` with score 1228.
- [ ] **Step 6:** Commit `feat: send chart, personal best and result from screen reading`.

### Task 5: Frame recorder

**Files:**
- Create: `inf_companion/capture/recorder.py`, `tests/capture/test_recorder.py`
- Modify: `inf_companion/cli.py` (`--record DIR`), `inf_companion/capture/process.py` (pass it to the child), `docs/windows-setup.md` (a "Recording screenshots" section).

**Interfaces:**
- Produces: `FrameRecorder(root: Path, min_interval_s=1.0, min_distance=12, max_files=3000, clock=time.monotonic, save=png_writer)`.
  - `.offer(frame, screen) -> str | None` saves `root/<screen>/<YYYYmmdd-HHMMSS-fff>.png` when the frame's 16×16 `average_hash` is ≥ `min_distance` from the last saved frame **of that screen**, and `min_interval_s` has passed since the last save. It returns a one-time status message when it turns itself off.
  - PNGs are written with `compress_level=1`.

- [ ] **Step 1: Write the failing tests:**
  - `test_saves_first_frame_per_screen`
  - `test_skips_similar_frames`
  - `test_respects_interval`
  - `test_stops_at_max_files_with_message`
  - `test_recorder_failure_turns_off`: the save raises `OSError`, giving one message and then no more attempts.
  - `test_cli_record_flag`
- [ ] **Step 2:** FAIL. **Step 3:** Implement it. The child calls `offer` after classification and puts any message on the queue as `capture_status` running with that message. **Step 4:** PASS (full suite).
- [ ] **Step 5:** Commit `feat: --record saves labelled frames for calibration`.

---

## After this plan

- With recorded frames from about 10 songs: learn readers for **BPM** and **artist** on song select (no table has them), and add 2P play and `loading`/`other` fixtures.
- Plan 3b: state machine and play records (SQLite), Recent plays from real data, and a GIF synced to the read BPM.
- Plan 3c: official CSV import, naming unknown titles (fingerprints), and the release zip.
