# inf-companion — Design

Date: 2026-11-23
Status: approved by the user, 2026-11-23
Repo: inf-companion · Python package: `inf_companion`

## 1. What this is and why

A personal companion app for beatmania IIDX INFINITAS. It runs alongside the game and
shows a web page on a second monitor while the user plays. It is inspired by
[inf_daken_counter_obsw](https://github.com/dj-kata/inf_daken_counter_obsw), but it is
built for one player at home, not for streaming:

- **No OBS.** The app captures the INFINITAS window itself.
- **Looks first.** It shows a 2DX-style lane where a note floats up from each button
  press, a button counter like the user's reference screenshot, and a looping GIF whose
  speed follows the song's BPM. The lane is built from a local beatoraja skin's images
  (WMII_FHD) when one is present.
- **Local play records.** It follows game state (song select, play, result) and keeps a
  local history of results, with score differences and graphs.

The user is a full-stack developer who wants to build and run this on their own
setup.

## 2. Goals, non-goals, anti-goals

**Goals**
- G1. Capture INFINITAS without OBS, with negligible impact on game performance.
- G2. Detect screen mode: song select, option, play, result, other.
- G3. Recognise song title, difficulty and level on song select and result screens, for
  SP charts. Read score, miss count, lamp, DJ level and judgements on the result screen.
- G3a. Play side (1P or 2P) is a setting. Play-screen detection and the lane follow it.
- G4. Keep a local history of plays, and show score difference vs previous best plus
  per-chart graphs over time.
- G5. Read the controller directly, with user-defined button bindings, to drive visual
  effects.
- G6. A local web page for the second monitor, with lane effects, the button counter,
  the BPM-synced GIF, and current/last result.
- G7. Develop mostly on macOS. Test and run on the Windows gaming PC.

**Non-goals**
- Per-song key-press tracking or statistics. Key presses are only for visuals (user's
  decision).
- Streaming features: OBS control, scene switching, Twitter/Discord posting, result
  image posting.
- Reading game memory. Recognition is image-only.
- Cloud sync or accounts. Records live in a local file. Deleting the app folder deletes
  them, and that's accepted. Long-term overall stats come from the official CSV export.
- SOF-LAN-aware GIF speed. Use the song's maximum BPM for now.
- Counter extras: ms, n/s and a total. Not needed (user, 2026-11-23). The counter only
  counts presses (§5.8).
- Redistributing skin images. Skins stay in the user's local `skins/` folder (§5.9).
- DP. SP only, on either side (user, 2026-11-23). DP plays aren't recognised or
  recorded. The screen shows as `unknown` and nothing is stored.
- Live judge counts during play. Nothing on the page shows them, so they aren't read
  (builder's call). Final judgements come from the result screen.

**Anti-goals** (failures even if everything "works")
- A1. Any noticeable stutter, frame drop or input delay in INFINITAS.
- A2. Key effects that lag or skip presses. They must feel instant.
- A3. Large installs on the gaming PC's C: drive (about 5 GB free).
- A4. Loading untrusted pickle data at runtime.

## 3. Constraints

- **Gaming PC:** Windows 10/11 64-bit, very little C: space. Everything (uv-managed
  Python, caches, app, data) must be able to live on another drive.
- **INFINITAS** renders at 1920×1080. It may run in exclusive fullscreen, which can
  defeat window-level capture (to be tested, see §7).
- **Development machine:** macOS. Windows-only parts (capture) must sit behind an
  interface with a Mac-runnable replacement.
- **Recognition tables** come from
  [kaktuswald/inf-notebook](https://github.com/kaktuswald/inf-notebook) (`resources/*.res`).
  - The repo has no licence file. This app is for personal use. Don't commit or
    redistribute the tables in a public repo or release. Fetch them from the source
    instead.
  - The tables are gzip/plain **pickle** files. They must be converted to JSON offline
    with a restricted unpickler that allows no globals. The app only reads JSON.
- The user agreed that **online calls are OK for fetching table updates**. Nothing
  else goes online.
- **Skin images** (WMII_FHD, a beatoraja FullHD play skin) are the user's local copy. Its
  terms ban redistribution outside approved sources and allow reuse in other skin
  projects. So it lives in `skins/`, which is gitignored except `skins/.gitkeep`, and
  never goes into a release.

## 4. Approaches considered

| | Approach | Trade-off | Decision |
|---|---|---|---|
| A | Python background process (capture, recognition, controller, storage, websocket) + web page (Vite/Svelte + PixiJS) | Follows inf-notebook's proven numpy recognition, and tables convert in the same language. Packaging a Python `.exe` is clunkier. | **Chosen** by the user |
| B | C#/.NET background process + same web page | Best Windows APIs, smallest `.exe`. Recognition has to be rewritten and tables converted, and .NET SDK uses a lot of disk. | Rejected |
| C | Thin backend; the page reads the controller via the browser Gamepad API | Fewest parts. But browsers can throttle background pages, and some IIDX controllers aren't standard gamepads, which risks A2. | Rejected |

## 5. Architecture

```
Windows gaming PC                                      Second monitor
┌────────────────────────────────────────────┐         ┌─────────────────┐
│ companion (Python, uv)                     │  ws://  │ web page        │
│                                            │ ──────▶ │ (static build)  │
│ capture proc ─frames─▶ recogniser ─▶ state │         │ lane, GIF,      │
│   (dxcam / window / replay)    machine ──▶ │ events  │ result,         │
│ input thread (SDL2) ─────────────────────▶ │         │ history, graphs │
│ storage (SQLite)  ◀────────────────────────│         └─────────────────┘
│ http server: static page + ws + REST       │
└────────────────────────────────────────────┘
```

### 5.1 Capture (`capture/`)
- Interface: `CaptureSource.grab() -> np.ndarray | None` (RGB, normalised to 1920×1080).
- Backends:
  - `dxcam` — DXGI Desktop Duplication of the monitor the INFINITAS window is on.
  - `window` — direct window capture (`PrintWindow` with `PW_RENDERFULLCONTENT`, or
    `BitBlt`).
  - `wgc` — Windows Graphics Capture. Optional. Include it only if the spike shows it
    helps.
  - `replay` — reads a folder of PNGs or a video file at a set rate. Runs on macOS.
- The default backend is chosen from the spike results (§7). It can be changed in
  settings.
- Runs in its own **process** (multiprocessing), so capture and numpy work never
  compete with the server or input thread. Frames go to the recogniser through shared
  memory, or as small crops only.
- **Adaptive rate:** about 4 fps on menus and result, lower during play (about 2 fps,
  enough to notice leaving play: result, quick retry or quit), 0 fps when the
  INFINITAS window doesn't exist. Only the needed regions are cropped and processed.

### 5.2 Recognition (`recog/`)
- **Screen classification:** average-hash of fixed crops compared with reference
  hashes. Same technique as inf_daken_counter's `screen_reader.py` (Hamming distance
  under a threshold). Use inf-notebook's `screenrecognition` table where it covers the
  case. Otherwise capture our own reference crops. Play-screen detection uses crops
  for the configured side (1P or 2P).
- **Song select / result reading:** re-implement inf-notebook's approach, without
  copying its code. Crop the area, threshold the colour channels into a binary mask,
  pack each row into hex nibbles, and walk the lookup tree to a title. Digits, levels,
  lamps and so on use the same table method. Sources: the `musicselect`,
  `informations` and `details` tables.
- **SP only:** read the play style from the screen. If it's DP, report `unknown` and
  read nothing else.
- **Unknown titles** (not in the tables): store the binarised fingerprint locally and
  let the user name it in the page. After that it matches exactly. This also covers
  songs released before tables update.
- **Table pipeline** (`tools/convert_tables.py`): download the `.res` files from the
  inf-notebook GitHub repo (pinned commit, or latest on request), unpickle with a
  restricted `Unpickler` whose `find_class` always raises, and write JSON plus a
  manifest (source commit, timestamps). The app checks for updates on start-up when the
  user allows it, or from a button in settings.

### 5.3 Song metadata
- Max BPM drives GIF speed. Notes radar is optional extra display.
- **Checked 2026-11-23:** `musictable1.2.res` holds **no BPM** (only versions, titles and
  level strings). So BPM comes from the song-select screen (below). `notesradar*.res` is known to
  hold per-chart radar values for SP/DP, including INFINITAS-only songs. Only the SP
  entries are used.
- If no table has BPM, read the BPM shown on the song-select screen with a locally
  learned digit table. As a last resort, let the user enter it per song.

### 5.4 Controller input (`input/`)
- SDL2 through `pysdl2` + `pysdl2-dll`. It works while INFINITAS has focus. Joystick
  buttons, axes and hats, plus keyboard for keyboard players.
- **Binding flow** in the page: "press key 1… key 7, scratch up, scratch down". Saved per
  device GUID.
- Turntable: handle both button-style and axis-style scratch (axis delta with a
  threshold, direction-aware).
- Events are timestamped with a monotonic clock at the source and sent to the page
  immediately. Input never waits on recognition.

### 5.5 State machine (`state/`)
- States: `idle → select → (option) → play → result → select…`, plus `unknown`.
- Moves happen on stable classification (N consecutive matching frames) to avoid
  flicker.
- On `select`: emit the current chart (title, difficulty, level, BPM, best score from
  the screen).
- On `play`: start a play record and emit `play_start`.
- On `result`: read the full result, finish the record, compute the difference vs
  previous best (from the result screen and from local history), emit, and store.
- Quick retry and quitting mid-song are recorded as incomplete plays.

### 5.6 Storage (`storage/`)
- SQLite file in the app's data folder (configurable path).
- Tables:
  - `charts`: title, style, difficulty, level, bpm_max
  - `plays`: chart, timestamp, score, misscount, lamp, djlevel, judges, options if
    read, complete flag
  - `fingerprints`: for user-named unknown titles
  - `settings` and `bindings`
- Official CSV import (the score export the user already has) fills best-known values
  for overall stats. Imported rows are marked `source=official`. Import is manual: the
  user picks the file in the page. Automatic download from the official site is out of
  scope for now (user decision, 2026-11-23).

### 5.7 Server (`server/`)
- One small ASGI app (Starlette + uvicorn). It serves the built page, a websocket for
  events, and a small REST API for history, settings, bindings and table updates.
  Listens on localhost by default.
- **Event types:** `hello`, `screen`, `chart`, `play_start`, `result`, `key_down`,
  `key_up`, `counts`, `capture_status`, `error`.

### 5.8 Web page (`web/`)
- Vite + Svelte. The build is static files served by the Python app. Node is only
  needed on the Mac.
- **Lane:** scratch plus 7 keys, drawn with PixiJS (WebGL). Each `key_down` spawns a
  note that floats up and fades, with a press flash on the key. The scratch sits on the
  left for 1P and on the right for 2P, following the side setting. Notes appear only
  for presses: there's no chart, and nothing falls. With a skin present, the frame,
  lane background, notes, key beams, key flashes and turntable come from the skin
  (§5.9). Without one, they're drawn as plain shapes.
- **Button counter** (user, 2026-11-23), like the user's reference screenshot:
  - Keys 2, 4 and 6 are in the top row and 1, 3, 5 and 7 in the bottom row. Each box
    shows how many times that key was pressed.
  - The turntable is a circle with two counts, scratch up and scratch down. Each
    direction is treated as its own button. The circle sits on the scratch side for 1P
    and 2P.
  - A box border is highlighted while its key is held (builder's assumption from the
    screenshot: yellow when held, green when idle).
  - Counts live in the Python process, so reloading the page doesn't reset them. They
    reset when the app starts and from a reset button on the page (user, 2026-11-23).
    Counts aren't stored on disk.
- **GIF:** the user uploads a GIF (stored locally) and sets how many beats one loop
  lasts. Frames are decoded (e.g. `gifuct-js`) and drawn on a canvas. Playback speed is
  `bpm_max × beats-per-loop` relative to the GIF's own duration, and it changes when
  the selected chart changes.
- **Current/last chart and result card:** score, score difference vs best, lamp change,
  miss count.
- **History:** per-chart list of plays with a score-over-time graph.
- **Settings:** capture backend, play side (1P/2P), data folder, bindings, GIF, theme,
  skin folder and skin style, table updates.

### 5.9 Skins
- **Folder:** `skins/<name>/` (setting `skin_dir`, default `skins/WMII_FHD`). The app
  serves only image files under that folder, at `/skin/...`.
- **WMII_FHD layout** (from its `play/lua/*.lua`, 1920×1080):
  - Sprite boxes:

    | Part | File | Box (x, y, w, h) |
    |---|---|---|
    | Notes | `play/parts/notes/<style>.png` (default, light, pastel, photon, simple) | scratch (94, 0, 90, 19), white (187, 0, 52, 19), black (241, 0, 40, 19) |
    | Key beam | `play/parts/laser/<name>.png` | black (0, 0, 40, 723), white (42, 0, 52, 723), scratch (96, 0, 90, 723) |
    | Key flash | `play/parts/keyflash/<colour>.png` | white (0, 0, 63, 92), black (70, 0, 46, 78) |
    | Lane background | `play/parts/lane/<name>.png` | 1P (0, 0, 432, 6), 2P (434, 0, 432, 6), repeated down the lane |
    | Lane frame | `play/parts/frame/Wide/<colour>.png` | 1P (0, 0, 685, 1080), 2P (717, 0, 685, 1080) |
    | Turntable | `play/parts/turntable/<name>.png` | label (0, 0, 49, 49) and symbol (49, 0, 49, 49) |
    | Turntable light | `play/parts/turntableLight/<colour>.png` | light (0, 0, 256, 256), flash (256, 0, 256, 256) |

  - Lane sizes: white keys 68, black keys 52, scratch 120, with 4 px gaps between lanes.
    The lane is 576 wide, starting 75 px into the frame, with the judge area from y 287.
- **Upward motion:** the skin's notes are drawn to fall toward the judge line. Here they
  rise from it. The sprites are symmetrical, so they're used as they are.
- **Missing or broken skin:** with no skin, or a missing file, the lane falls back to
  drawn shapes and the page shows a warning. The page never breaks.
- **Bombs** (`bomb/*`, animation strips) are an optional extra, left to the builder.
- Laid out for a second monitor (landscape and portrait). Respects
  `prefers-reduced-motion`.

## 6. Development and delivery

- **Repo layout:** `inf_companion/` (Python package), `web/` (Svelte),
  `tools/convert_tables.py`, `tools/capture_spike.py`, `docs/`.
- **Python** via uv with `pyproject.toml` + `uv.lock`. No OpenCV: numpy + Pillow only.
- **On Windows**, set `UV_PYTHON_INSTALL_DIR`, `UV_CACHE_DIR` and the project folder on
  a non-C drive. Day-to-day: `git pull && uv run inf-companion`.
- **Releases:** GitHub Actions `windows-latest` builds a PyInstaller one-folder zip with
  the built web page. Recognition tables are **not** bundled. They download on first
  run (§3).
- **macOS dev:** run `inf-companion --capture replay --source <folder|video>` and plug the
  controller into the Mac to test bindings. The page is developed with the Vite dev
  server, proxying to the Python websocket.
- **Tests:** recognition unit tests on a fixture set of real screenshots, with expected
  title/difficulty/score/judges. Also tests for the state machine driven by replay
  sequences, and the table converter (rejects any pickle with globals).

## 7. Capture spike (throwaway)

Build order (user, 2026-11-23): the web page and controller input come first, so the UI and
key effects can be checked before any capture work. The spike is the first step of the
capture work.

`tools/capture_spike.py`, run on the gaming PC:
- For each method (`window` GDI/PrintWindow, `wgc` if feasible, `dxcam`) and each
  INFINITAS display mode, run about 30 s during a song and record the results below.
  Display modes: exclusive fullscreen, plus windowed/borderless if INFINITAS offers
  it. If it doesn't, there's a community custom launcher with a window mode — see
  `docs/research-notes.md`. Record:
  - whether frames are real or black
  - achieved fps at a 4 fps target and at max
  - process CPU %
- At the same time, the user records INFINITAS frame times with PresentMon, with the
  spike off vs on.
- Saves sample frames from select, play and result screens. These become the first
  replay/fixture set.
- **Result:** pick the default backend and the target capture rate. Write the findings
  in `docs/`.

## 8. Performance budget
- Capture + recognition: under 5% of one CPU core on average, under 300 MB RAM.
- No measurable change in INFINITAS frame-time spread under PresentMon (compared over
  the same song).
- Key press to note shown on the page: under 30 ms on the same PC.

## 9. Decisions recorded
- Approach A (user).
- No OBS. Key presses are visual only. Records are local and loss on deletion is
  accepted. Overall stats come from the official export (user).
- Ready-made inf-notebook tables, with online fetching of table updates allowed (user).
- Develop on Mac. Windows test via source + uv, releases via GitHub Actions (user agreed).
- The button counter shows press counts only, with scratch up and down as two
  buttons. Counts reset when the app starts and from a reset button (user,
  2026-11-23).
- The lane uses local skin images from `skins/`, which is gitignored (user,
  2026-11-23).
- SP only, with 1P/2P as a setting (user, 2026-11-23).
- Builder's calls (can be changed):
  - Svelte + PixiJS, Starlette + uvicorn, SQLite, SDL2
  - adaptive capture rate
  - unknown-title fingerprints named by the user (Windows OCR dropped, since the tables
    cover naming)
  - JSON-only tables at runtime
  - tables never redistributed
  - no live judge reading, so capture stays at a low rate during play
  - DP screens are treated as `unknown` (not recorded)

## 10. Open questions (user)
None. Answered 2026-11-23:
1. Counter panel: press counts per key, plus scratch up and down. They reset when the
   app starts and from a reset button. No ms or n/s (§5.8).
2. SP only, either side. 1P/2P is a setting.

## 11. Left to the builder
- Exact crop coordinates and thresholds (taken from the tables and fixtures).
- How capture frames move between processes (shared memory vs crops).
- Visual design details of the page, within the elements listed in §5.8.
- Whether `wgc` is worth implementing after the spike.
