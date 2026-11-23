# Capture and Tables Implementation Plan (Plan 2 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove which capture method works on the gaming PC (throwaway spike), convert inf-notebook's tables to JSON safely, and recognise which screen INFINITAS is showing. The recognition is developed on macOS from replayed screenshots, and the page shows the detected screen live.

**Architecture:** The spike is a standalone Windows script under `tools/`. The converter (`tools/convert_tables.py`) uses a restricted unpickler that allows exactly six named globals, each mapped to an inert stand-in, and writes JSON to `tables/`. The app gets a `capture/` package with a `CaptureSource` interface and a `replay` backend, plus a `recog/` package that classifies screens from the converted table and our own play-screen references. Capture and recognition run in a child process and send `screen` events through the existing `EventBus`.

**Tech Stack:** Python 3.12 via uv, numpy + Pillow (new runtime dependencies, both allowed by CLAUDE.md), multiprocessing. Spike-only, never project dependencies: `dxcam`, `psutil`, run with `uv run --with`.

**Spec:** `docs/superpowers/specs/2026-11-23-infinitas-companion-design.md` (§3, §5.1, §5.2, §5.5, §7, §8). Also read `CLAUDE.md` and `docs/research-notes.md`.

## Global Constraints

- No memory reading or injection into INFINITAS. Recognition is image-only.
- Never load pickle files at runtime. Only `tools/convert_tables.py` unpickles. It allows exactly `builtins.slice`, `numpy.dtype`, `numpy._core.multiarray.scalar`, `numpy._core.numeric._frombuffer`, `numpy._core.multiarray._reconstruct` and `numpy.ndarray`, each mapped to our own inert stand-in. Never import numpy or call the real objects there. Every other global raises.
- Never commit `.res` files or converted tables. `tables/` and `data/` stay in `.gitignore`.
- Don't copy inf-notebook code verbatim. Re-implement the method.
- The game comes first. Capture and recognition run in a separate process, at an adaptive low rate (about 4 fps on menus and result, about 2 fps during play, 0 fps when there's no window), on crops only.
- No OpenCV. The only new project dependencies are numpy and Pillow. Install and data paths stay configurable (`--tables-dir`, default `./tables`).
- Pinned table source: inf-notebook commit `f43158edfb65006c976ed7785cfa7b066c3ffcf4`. Tables used here: `screenrecognition1.0`, `musictable1.2`, `notesradar1.2`, `musicselect2.3`, `informations4.1`, `details3.2`, `resultothers1.0`, `resultrecognition1.0`, `deeper0.3` (all gzip pickle) and `musicnamechanges` (plain JSON).
- SP only. The play side (1P/2P) comes from settings.
- Frames are `numpy.ndarray`, shape `(1080, 1920, 3)`, `uint8`, RGB. Anything else is normalised to that first.

## Review Focus

1. **INFINITAS not running, minimised or alt-tabbed.** The spike and the capture process report "no window" and drop to 0 fps. They never crash or busy-loop. Tests: Task 1 `test_find_window_none_reports_missing`, Task 5 `test_capture_loop_idles_without_frames`.
2. **Exclusive fullscreen giving black frames.** The spike flags the method as "black frames" instead of reporting a good fps. Test: Task 1 `test_black_frames_flagged`.
3. **Capture not at 1920×1080** (a 1600×900 window, or high DPI). Frames are normalised before cropping, and classification still works. Test: Task 4 `test_normalise_resizes_to_1080p`, Task 6 `test_classify_downscaled_fixture`.
4. **A hostile or unexpected pickle.** Any global outside the six raises, numpy is never imported, and stand-ins given wrong arguments raise a clean error. Tests: Task 2 `test_refuses_other_globals`, `test_never_imports_numpy`, `test_bad_stand_in_args_raise`.
5. **Tables missing, partial or from an unknown version.** The app runs with recognition off and sends a clear `capture_status` message. It never crashes. Test: Task 3 `test_missing_tables_reported`, Task 5 `test_app_runs_without_tables`.

---

## Order and who runs what

Task 1 is for the user to run on the gaming PC. Tasks 2–4 don't need its results and can be built while it's being run. Task 6 needs the screenshots the spike saves, so it waits for them.

## File Structure

```
tools/capture_spike.py            throwaway Windows spike (not imported by the app)
tools/convert_tables.py           download + safe unpickle + JSON out
tools/make_pickle_fixtures.py     dev-only: builds tiny test pickles (run with --with numpy)
tools/calibrate_screens.py        dev-only: prints screen keys for labelled fixtures
inf_companion/tables/__init__.py
inf_companion/tables/load.py      load_tables(dir) -> Tables | raises TablesError
inf_companion/capture/__init__.py
inf_companion/capture/base.py     CaptureSource protocol, normalise()
inf_companion/capture/replay.py   ReplaySource (folder of PNGs)
inf_companion/capture/process.py  child-process loop + adaptive rate + stable-screen filter
inf_companion/recog/__init__.py
inf_companion/recog/screen.py     area_key(), classify()
inf_companion/recog/refs/play.json our own play-screen references (from user fixtures)
tests/fixtures/pickles/*.pkl      tiny synthetic pickles (ours, committed)
tests/fixtures/screens/<label>/*.png  the user's captures, labelled (committed)
tests/tools/test_capture_spike.py, tests/tools/test_convert_tables.py
tests/test_tables.py tests/capture/test_replay.py tests/capture/test_process.py tests/recog/test_screen.py
```

---

### Task 1: Capture spike (throwaway, Windows)

**Files:**
- Create: `tools/capture_spike.py`, `tests/tools/test_capture_spike.py`
- Modify: `docs/windows-setup.md` (add a "Capture spike" section)

**Interfaces:**
- Produces, for the user: a report folder holding `report.json`, `report.md` and `frames/<method>/<n>.png`.
- Pure helpers, tested on macOS:
  - `is_black(frame: np.ndarray) -> bool`: mean < 3.
  - `summarise(samples: list[Sample]) -> dict`, where `Sample(t: float, ok: bool, black: bool, cpu: float)`. Returns `{"frames", "fps", "black_ratio", "cpu_avg", "cpu_max", "status"}`. `status` is one of `"ok"`, `"black frames"` (black_ratio > 0.5), `"no frames"` and `"no window"`.
  - `find_window(enum=..., title="beatmania IIDX INFINITAS") -> int | None`. `enum` is injectable for tests and defaults to the ctypes `EnumWindows` version on Windows.
- Methods:
  - `window`: ctypes `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT=2)` into a DIB section. No pywin32.
  - `dxcam`: `dxcam.create(output_idx=<monitor of the window>)`, using `grab()` with no region and cropping to the window rect.
- CLI: `--method window|dxcam|all` (default all), `--seconds 30`, `--target-fps 4` (also `0` = as fast as possible), `--save-every 2.0` seconds, `--out <dir>` (required).
- Run with: `uv run --with dxcam --with psutil --with pillow --with numpy python tools/capture_spike.py --out D:\capture-spike`.

- [ ] **Step 1: Write the failing tests** (helpers only. Import with `importlib` from `tools/` and skip anything Windows-only.)

```python
def test_black_frames_flagged():
    s = [Sample(t=i / 4, ok=True, black=True, cpu=1.0) for i in range(40)]
    assert summarise(s)["status"] == "black frames"

def test_fps_and_cpu_summary():
    s = [Sample(t=i / 4, ok=True, black=False, cpu=2.0 + i % 2) for i in range(41)]
    r = summarise(s)
    assert r["status"] == "ok" and abs(r["fps"] - 4.0) < 0.2 and r["cpu_max"] == 3.0

def test_find_window_none_reports_missing():
    assert find_window(enum=lambda: [(1, "Notepad")]) is None
    assert find_window(enum=lambda: [(7, "beatmania IIDX INFINITAS")]) == 7

def test_is_black():
    assert is_black(np.zeros((4, 4, 3), np.uint8)) and not is_black(np.full((4, 4, 3), 40, np.uint8))
```

- [ ] **Step 2:** Run `uv run --with numpy pytest tests/tools/test_capture_spike.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3:** Implement the helpers and the Windows paths. Per method, run for `--seconds` at the target rate, then again at max rate. Save a frame every `--save-every` seconds, and write `report.json` and a `report.md` table (method × target → fps, black ratio, CPU avg/max, status).
- [ ] **Step 4:** Tests PASS.
- [ ] **Step 5:** Add a "Capture spike" section to `docs/windows-setup.md`:
  - The exact command, with uv already off C:. The packages land in `UV_CACHE_DIR` on D:.
  - Run it once per INFINITAS display mode (exclusive fullscreen, and windowed/borderless if offered). Each run takes about 2 minutes while you play a song, then stay on the result screen.
  - At the same time, record PresentMon for the same song, once with the spike off and once with it on.
  - Bring back `report.md`, the PresentMon CSVs, and the `frames/` folders.
  - **Screenshot set for Task 6.** Sort saved frames into `tests/fixtures/screens/{music_select,play_1p,play_2p,result,loading,other}/`. Aim for at least 5 per folder, from different songs. Only the side you play is needed in `play_*`.
- [ ] **Step 6:** Commit `feat(tools): capture spike`. **Stop and ask the user to run it.** Tasks 2–4 can go ahead while they do.

### Task 2: Safe table converter

**Files:**
- Create: `tools/convert_tables.py`, `tools/make_pickle_fixtures.py`, `tests/fixtures/pickles/*.pkl`, `tests/tools/test_convert_tables.py`

**Interfaces:**
- Produces:
  - `safe_load(data: bytes) -> Any`. It gunzips when the data starts with `\x1f\x8b`. Its `pickle.Unpickler` subclass `find_class` returns only these stand-ins and raises `pickle.UnpicklingError(f"refused global {module}.{name}")` otherwise:

    | global | stand-in result |
    |---|---|
    | `builtins.slice(*a)` | `{"slice": [start, stop, step]}` (missing items are `None`) |
    | `numpy.dtype(spec, align, copy)` (+ `__setstate__`) | `DtypeStub(kind: str, size: int, order: "<"\|">")`. Only kinds `u i f b`, sizes 1/2/4/8 |
    | `numpy._core.multiarray.scalar(dtype, raw)` | Python int, float or bool via `struct` |
    | `numpy._core.numeric._frombuffer(buf, dtype, shape, order)` | nested lists (C order). `order="F"` raises |
    | `numpy._core.multiarray._reconstruct(cls, shape, dtype)` + `__setstate__((ver, shape, dtype, fortran, raw))` | `ArrayStub` that becomes nested lists |
    | `numpy.ndarray` | a marker class accepted only as `_reconstruct`'s first argument |

  - `to_json(obj) -> Any`: converts stand-ins to plain JSON values. Dict keys become strings, and an `ArrayStub` becomes `{"array": nested, "dtype": "<u1", "shape": [...]}`.
  - `convert(names: list[str], out_dir: Path, commit: str = PINNED, fetch=fetch_raw) -> dict`. It writes `out_dir/<name>.json` for each table and `out_dir/manifest.json` = `{"source": "kaktuswald/inf-notebook", "commit", "converted_at" (ISO), "files": {name: {"sha256_res", "bytes"}}}`. It returns the manifest.
  - `fetch_raw(name, commit) -> bytes` downloads from raw.githubusercontent.com with urllib. It's injectable for tests.
  - CLI: `uv run python tools/convert_tables.py [--out tables] [--commit <sha>]`.
- `make_pickle_fixtures.py`, run with `uv run --no-project --with numpy python tools/make_pickle_fixtures.py`, writes:
  - `slice.pkl`
  - `scalar_u8.pkl` (`np.uint64(6112)`)
  - `frombuffer.pkl` (dict holding a `(2,3)` uint8 array via `np.frombuffer(...).reshape`)
  - `ndarray.pkl` (a `(2,2)` uint16 array)
  - `mixed.pkl` (nested dict with all of the above)
  - `evil_os.pkl` (`os.system` reduce)

- [ ] **Step 1:** Write `make_pickle_fixtures.py`, run it, and commit the `.pkl` files. They're our own synthetic data.
- [ ] **Step 2: Write the failing tests**

```python
def test_slice_and_scalar():
    assert to_json(safe_load(fx("slice.pkl"))) == {"slice": [577, 678, 50]}
    assert to_json(safe_load(fx("scalar_u8.pkl"))) == 6112

def test_arrays_become_lists():
    assert to_json(safe_load(fx("ndarray.pkl")))["array"] == [[1, 2], [300, 65535]]
    assert to_json(safe_load(fx("frombuffer.pkl")))["v"]["array"] == [[0, 1, 2], [3, 4, 5]]

def test_refuses_other_globals():
    with pytest.raises(pickle.UnpicklingError, match="refused global"):
        safe_load(fx("evil_os.pkl"))

def test_never_imports_numpy():
    safe_load(fx("mixed.pkl"))
    assert "numpy" not in sys.modules   # run in a subprocess so earlier imports can't leak in

def test_bad_stand_in_args_raise():   # e.g. scalar with a 3-byte buffer for u8, dtype "c16"
    ...  # hand-built pickles via pickle opcodes; expect ValueError, never a crash or call

def test_convert_writes_json_and_manifest(tmp_path):
    m = convert(["slice"], tmp_path, fetch=lambda n, c: fx("slice.pkl"))
    assert json.loads((tmp_path / "slice.json").read_text()) == {"slice": [577, 678, 50]}
    assert m["commit"] == PINNED and "sha256_res" in m["files"]["slice"]
```

- [ ] **Step 3:** FAIL. **Step 4:** Implement. **Step 5:** PASS.
- [ ] **Step 6: Real tables, by hand.** Run `uv run python tools/convert_tables.py --out tables`. Expected:
  - All 10 JSON files are written.
  - `screenrecognition.json["get_screen"]` has the keys `loading, result, music_select, screentransition, entry, gameend`.
  - `notesradar.json` has `SP`.
  - `git status` shows nothing under `tables/`.
- [ ] **Step 7:** Commit `feat(tools): safe table converter (six allowlisted globals)`.

### Task 3: Table loader (runtime, JSON only)

**Files:**
- Create: `inf_companion/tables/__init__.py`, `inf_companion/tables/load.py`, `tests/test_tables.py`
- Modify: `inf_companion/cli.py` (add `--tables-dir`, default `./tables`)

**Interfaces:**
- `@dataclass Tables(dir: Path, manifest: dict, screen: dict, music: dict, notesradar: dict, raw: dict[str, Any])`. `raw` loads the other tables lazily.
- `class TablesError(Exception)`.
- `load_tables(dir: Path) -> Tables`. It raises `TablesError` with a plain message when the folder, the manifest or a required file (`screenrecognition`, `musictable`, `notesradar`) is missing, or when JSON is malformed. The message names the file and the command that fixes it (`uv run python tools/convert_tables.py`).

- [ ] **Step 1: Write the failing tests:** `test_loads_minimal_tables(tmp_path)` (writes a fake manifest and three JSONs), and `test_missing_tables_reported(tmp_path)`:

```python
with pytest.raises(TablesError, match="screenrecognition.json is missing.*convert_tables.py"):
    load_tables(tmp_path)
```

- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS. **Step 5:** Commit `feat: json table loader`.

### Task 4: Capture interface and replay backend

**Files:**
- Modify: `pyproject.toml` (add `numpy`, `pillow`)
- Create: `inf_companion/capture/__init__.py`, `inf_companion/capture/base.py`, `inf_companion/capture/replay.py`, `tests/capture/test_replay.py`

**Interfaces:**
- `class CaptureSource(Protocol)`:
  - `def grab(self) -> np.ndarray | None`: a frame, or None when there's nothing to capture right now.
  - `def close(self) -> None`
- `normalise(img: np.ndarray | PIL.Image.Image) -> np.ndarray`. RGBA, BGR or other sizes become `(1080, 1920, 3)` uint8 RGB. It resizes with Pillow `BILINEAR` when needed. `bgr: bool = False` is a keyword argument for backends that give BGR.
- `ReplaySource(source: Path, loop: bool = False)`. It plays the PNG/JPG files in a folder, sorted by name, then a single image file. `grab()` returns the next normalised frame, or None once finished (unless `loop`). `__len__` is the frame count.

- [ ] **Step 1: Write the failing tests:**
  - `test_normalise_resizes_to_1080p`: a 1600×900 RGBA image becomes `(1080, 1920, 3)` uint8.
  - `test_replay_plays_folder_in_order_then_none`: three PNGs named 2, 10, 1 play back sorted as 1, 2, 10, then None.
  - `test_replay_loop`
  - `test_replay_missing_source_raises_clear_error`
- [ ] **Step 2:** FAIL. **Step 3:** `uv add numpy pillow`, then implement. **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat: capture interface and replay backend`.

### Task 5: Capture process, adaptive rate, `screen` events

**Files:**
- Create: `inf_companion/capture/process.py`, `tests/capture/test_process.py`
- Modify: `inf_companion/cli.py` (`--capture replay|off` with default `off` for now, `--source <dir>`, `--replay-fps 4`), `inf_companion/server/app.py` (`hello` gains `screen` and `capture_status`), `web/src/lib/events.ts`, `web/src/lib/stores.ts` (`screen`, `captureStatus` stores), `web/src/display/Display.svelte` (a small screen label next to the connection dot, `?debug=1` only)

**Interfaces:**
- Consumes: `CaptureSource`, `ReplaySource` (T4); `load_tables`, `TablesError` (T3); `classify(frame, tables, side) -> str` (T6). Until T6 lands, a stub that returns `"unknown"` keeps this task testable.
- Produces:
  - `RATE_FPS = {"play": 2.0, "default": 4.0, "idle": 0.0}`
  - `class StableScreen(n: int = 3)` with `feed(label: str) -> str | None`. It returns a new label only after `n` consecutive equal labels, else None.
  - `capture_loop(source, classify_fn, emit: Callable[[dict], None], stop: threading.Event | mp.Event, clock=time.monotonic, sleep=time.sleep)`. Each frame it calls `classify_fn` and feeds `StableScreen`. On a change it emits `{"type": "screen", "screen": label}`. It sleeps by the current screen's rate. When `grab()` returns None it emits `capture_status` `{"state": "no frames"}` once and backs off to 1 s polls.
  - `start_capture(kind, source_path, tables_dir, side, bus) -> CaptureHandle`. It runs `capture_loop` in a `multiprocessing.Process` (spawn) and relays its queue to `bus.publish` on a thread, using `make_event`. If `TablesError` is raised, it emits `capture_status {"state": "off", "message": str(err)}` and doesn't start the process.
  - Wire events: `screen` `{screen: "music_select"|"play"|"result"|"loading"|"screentransition"|"entry"|"gameend"|"unknown"}` and `capture_status` `{state: "running"|"no frames"|"off", message?: str}`.

- [ ] **Step 1: Write the failing tests** (in-thread `capture_loop` with a fake source, fake clock and fake sleep):

```python
def test_stable_screen_needs_three_in_a_row():
    s = StableScreen(3); assert [s.feed(x) for x in "aab" "bbb"] == [None, None, None, None, None, "b"]

def test_emits_screen_change_once(): ...          # frames classify a,a,a,p,p,p -> two screen events
def test_rate_follows_screen(): ...               # sleeps 0.25 s on menus, 0.5 s during "play"
def test_capture_loop_idles_without_frames(): ... # grab() None -> one capture_status, 1 s sleeps, no busy loop
def test_app_runs_without_tables(tmp_path): ...   # start_capture with empty tables dir -> capture_status off + message, no process
```

- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS.
- [ ] **Step 5:** Run by hand: `uv run inf-companion --capture replay --source tests/fixtures/screens/music_select --no-input`, then open `/?debug=1`. Expected: the label shows `music_select` within about 1 s, or `unknown` before T6. Stop the app and check no child process is left (`pgrep -f inf_companion`).
- [ ] **Step 6:** Build the web page, then commit `feat: capture process with adaptive rate and screen events`.

### Task 6: Screen classification (needs the user's screenshots from Task 1)

**Files:**
- Create: `inf_companion/recog/__init__.py`, `inf_companion/recog/screen.py`, `inf_companion/recog/refs/play.json`, `tools/calibrate_screens.py`, `tests/recog/test_screen.py`
- Add: `tests/fixtures/screens/**` (the user's labelled captures)

**Interfaces:**
- `area_key(frame: np.ndarray, area: dict, orientation: Orientation) -> int`. `area` is `{left, top, width, height}`, and it returns the sum of the crop's channel values. `Orientation` is `"as_is"` or `"flipped"`. `"flipped"` means the image is flipped vertically and BGR, which is how inf-notebook builds its keys; check this against `resources_generate_screenrecognition.py`.
- `SCREEN_ORIENTATION: Orientation`: a module constant fixed by Step 2.
- `classify(frame, tables: Tables, side: "1P"|"2P") -> str`:
  1. For each `get_screen` entry, if `area_key == value`, return that screen name.
  2. Otherwise, if `is_play(frame, side)`, return `"play"`.
  3. Otherwise return `"unknown"`.
- `is_play(frame, side) -> bool` compares a 16×16 average hash of `refs/play.json[side]["area"]` with the stored `hash`. It matches at a Hamming distance ≤ `refs/play.json["max_distance"]` (default 10).
- `average_hash(img: np.ndarray, size: int = 16) -> str` (hex). It uses Pillow grayscale and resize, without imagehash.

- [ ] **Step 1:** Commit the user's fixtures under `tests/fixtures/screens/<label>/`.
- [ ] **Step 2: Calibrate.** `tools/calibrate_screens.py --tables tables --fixtures tests/fixtures/screens` prints `area_key` for every fixture × screen entry in both orientations.
  - Pick the orientation where each labelled fixture matches its own entry exactly and no other. Set `SCREEN_ORIENTATION`.
  - If neither orientation matches exactly, try `abs(key - value) <= tolerance`. Pick the smallest tolerance that separates the screens cleanly, and record it as `SCREEN_TOLERANCE`.
  - For play: choose a crop (side-specific) whose average hash is within 10 between the play fixtures and further than 20 from every non-play fixture. Write it to `refs/play.json` as `{"1P": {"area": {...}, "hash": "..."}, "2P": {...}, "max_distance": 10}`. Only the user's side needs a reference. The other side is filled when fixtures exist.
  - Record what was found in the commit message.
- [ ] **Step 3: Write the failing tests:**

```python
@pytest.mark.parametrize("path,label", labelled_fixtures())   # walks tests/fixtures/screens
def test_classify_fixture(path, label, tables, settings_side):
    assert classify(load(path), tables, settings_side) == label_to_screen(label)

def test_classify_downscaled_fixture(tables):   # resize a fixture to 1600x900, normalise, classify -> same label
    ...

def test_area_key_orientation():   # 2x1 synthetic area, known pixels -> exact sums for both orientations
    ...
```

  Real tables are needed. These tests skip with a clear reason when `tables/` hasn't been converted (`pytest.mark.skipif`).
- [ ] **Step 4:** FAIL. **Step 5:** Implement and swap the T5 stub for `classify`. **Step 6:** PASS on every fixture.
- [ ] **Step 7:** Run `uv run inf-companion --capture replay --source <a mixed folder of fixtures> --replay-fps 2`. The `?debug=1` label follows the screens.
- [ ] **Step 8:** Commit `feat: screen classification from tables and play references`.

---

## After this plan

- Pick the default Windows backend from the spike report, then implement it behind `CaptureSource` (`dxcam` and/or `window`, plus `wgc` only if the spike shows it's needed).
- Plan 3: the state machine, song-select and result reading (title, difficulty, level, BPM digits, score, lamp, DJ level), records, CSV import, real data in the panels, and the release workflow.
