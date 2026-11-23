# Windows setup (keeps C: clean)

Everything goes on another drive. These steps use `D:`; use any non-C: drive.

## One time

1. **Git.** Install Git for Windows and choose a `D:` install folder, or unzip
   PortableGit to `D:\tools\git` and add `D:\tools\git\cmd` to your `PATH`.

2. **uv**, installed to `D:` (PowerShell):

   ```powershell
   powershell -ExecutionPolicy ByPass -c {$env:UV_INSTALL_DIR = "D:\tools\uv"; irm https://astral.sh/uv/install.ps1 | iex}
   ```

3. **Keep uv's Python, caches and tools off C:.** These take effect in new terminals:

   ```powershell
   setx UV_PYTHON_INSTALL_DIR D:\tools\uv\python
   setx UV_CACHE_DIR D:\tools\uv\cache
   setx UV_PYTHON_BIN_DIR D:\tools\uv\bin
   setx UV_TOOL_DIR D:\tools\uv\tools
   ```

4. Open a **new** PowerShell window and get the code:

   ```powershell
   cd D:\code
   git clone https://github.com/forpr1093/inf-companion.git inf-companion
   cd inf-companion
   ```

5. Check that nothing points at C::

   ```powershell
   uv cache dir
   uv python dir
   ```

   Both should print `D:\tools\uv\...` paths.

## Run

```powershell
cd D:\code\inf-companion
uv run inf-companion
```

- The first run downloads Python and the packages into `D:\tools\uv`. The virtual
  environment (`.venv`) and your data (`data\`, settings, bindings, the GIF) live inside
  `D:\code\inf-companion`.
- Open `http://127.0.0.1:8765/` in a browser on the second monitor and make it full
  screen.
- Open `http://127.0.0.1:8765/#/settings` to bind the controller and upload a GIF. The
  settings link is also at the bottom-right of the display.
- To keep data somewhere else: `uv run inf-companion --data-dir E:\companion-data`.

## Screen capture

The app watches INFINITAS with **dxcam** (it was the fastest and lightest in the capture
spike). It needs inf-notebook's recognition tables, converted once:

```powershell
cd D:\code\inf-companion
uv run python tools/convert_tables.py
```

This writes `tables\` (ignored by git). Run it again after an update only if the app
says the tables are missing or unusable.

- `uv run inf-companion` captures automatically on Windows. Start INFINITAS before or
  after the app; it finds the game window by itself, on any monitor.
- To check it, open `http://127.0.0.1:8765/?debug=1`. The label in the corner shows the
  screen the app sees: `music_select`, `play`, `result`, and so on.
- Turn capture off with `uv run inf-companion --capture off`.
- Only the 1P play screen is recognised for now. If you play 2P, the status says play
  detection is off until 2P screenshots are calibrated.

## What the page reads from the game

- **Song select:** Now playing shows the title, difficulty, level and note count. Personal
  best shows the best score, clear lamp and miss count the game displays.
- **Result:** the app reads the score, lamp, DJ level, miss count and judgments, ready for
  play history in a later update.
- Not read yet: BPM and artist. They need screenshots to learn from (see below).

## Recording screenshots

To help calibrate BPM, artist and other screens, let the app save screenshots while you
play:

```powershell
uv run inf-companion --record D:\inf-record
```

- Screenshots go to `D:\inf-record\<screen>\` (`music_select`, `play`, `result`, `unknown`,
  …). It saves at most one a second, skips frames that look the same, and stops after 3000.
- Scroll through about 10 songs on song select (different BPMs and difficulties), play a
  few, and stay on each result screen for a couple of seconds.
- Zip the folder and bring it back. Delete it after; it's only for calibration.

## Update

```powershell
cd D:\code\inf-companion
git checkout main
git pull
uv run inf-companion
```

- The built web page is part of the repository, so Windows never needs Node.
- To try work in progress, switch to its branch, e.g. `git checkout feat/capture-and-tables`,
  then `git pull`. Go back with `git checkout main`.

## First real-controller check

Run it with INFINITAS open and the page on the second monitor at
`http://127.0.0.1:8765/?debug=1`. Then check:

1. **Binding.** Bind the controller in settings: keys 1–7, then spin the turntable one
   way and then the other.
2. **Every press shows.** Play a song with trills and a scratch-heavy song. Every press
   should draw a note and count once.
3. **Latency.** Read the "key → note" readout in the top-left of the lane. The target is
   a mean under 30 ms.
4. **Input while INFINITAS has focus.** Notes should keep appearing while you play.
5. **The game feels the same.** No stutter or input delay in INFINITAS.

Note the numbers and anything odd, and bring them back.

## Capture spike (one-time test)

This measures which way of capturing INFINITAS works on your PC and what it costs. It
needs two extra packages, `dxcam` and `psutil`, which go into uv's cache on D:, not into
the app. OpenCV is **not** needed.

### Get the spike

It lives on the `feat/capture-and-tables` branch until that's merged:

```powershell
cd D:\code\inf-companion
git fetch origin
git checkout feat/capture-and-tables
git pull
```

### Run it

1. Start INFINITAS and pick a song you know.
2. In PowerShell:

   ```powershell
   cd D:\code\inf-companion
   uv run --with dxcam --with psutil --with pillow --with numpy python tools/capture_spike.py --out D:\capture-spike\fullscreen
   ```

   It tries three capture methods, each twice: at 4 fps, then as fast as it can. Each run
   is 30 seconds, so about 3 minutes in total. Play the song while it runs, then stay on
   the result screen until it finishes.

   | method | how it captures |
   |---|---|
   | `window` | asks the INFINITAS window to draw itself (PrintWindow) |
   | `screen` | copies the game's area off the desktop (BitBlt, what inf-notebook uses) |
   | `dxcam` | DirectX desktop duplication of the monitor INFINITAS is on |

   - **Second monitor:** nothing extra is needed. `dxcam` finds INFINITAS's monitor and
     graphics adapter by itself, and prints which one it picked ("dxcam: adapter …,
     output …"). Only if that line looks wrong, force an output with `--dxcam-output N`.
   - To try one method on its own: `--method screen`, `--method dxcam` or
     `--method window`.
3. If INFINITAS has a windowed or borderless mode, switch to it and run again with
   `--out D:\capture-spike\windowed`.
4. **PresentMon:** record the same song twice, once with the spike off and once with it
   running, so we can see whether capture affects the game's frame times.

### What the report means

`report.md` has one row per method and rate:

| status | meaning |
|---|---|
| `ok` | real frames. Look at `fps` and the CPU columns. |
| `black frames` | the method runs but only sees black (common for `window` in fullscreen) |
| `no frames` | nothing came back at all |
| `no window` | INFINITAS wasn't running, or its window title didn't match |
| `error: …` | that method failed. The other methods still ran. |

### Bring back

- `report.md` from each run (fullscreen, and windowed if you tried it)
- the PresentMon CSVs
- the console output if anything says `error`, or if every method shows black frames

### Screenshots for screen recognition

The spike saves a frame every 2 seconds under `D:\capture-spike\...\frames\`. Use
frames from a method whose status was `ok`. Copy at least 5 of each, from different songs,
into these folders in the repo:

```
tests/fixtures/screens/music_select/
tests/fixtures/screens/play_1p/      (or play_2p/, the side you play)
tests/fixtures/screens/result/
tests/fixtures/screens/loading/
tests/fixtures/screens/other/        (anything else: title, options, menus)
```

If you need more, run again with `--save-every 1`, or with a single method such as
`--method screen`.

### Troubleshooting

- **`No module named cv2`:** you have an old copy of the spike. Run `git pull` on the
  `feat/capture-and-tables` branch.
- **All black:** run `--method screen` on its own and check one saved PNG. If it's black
  too, try INFINITAS's windowed mode, and send the console output.
- **`no window`:** start INFINITAS first. The spike looks for a window whose title starts
  with "beatmania IIDX INFINITAS".
