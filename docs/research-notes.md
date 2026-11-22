# Research notes (2026-11-23)

Findings from the planning conversation. The design is in
`docs/superpowers/specs/2026-11-23-infinitas-companion-design.md`.

## Reference projects

### inf_daken_counter_obsw — https://github.com/dj-kata/inf_daken_counter_obsw (Apache-2.0)
OBS-oriented INFINITAS key/judge counter. Useful parts:
- `src/screen_reader.py`
  - **Screen detection:** `imagehash.average_hash` of fixed crops compared with stored
    hex hashes, match when Hamming distance < 10. Functions `is_select`, `is_play`
    (per play side), `is_result`, `is_option`, `is_endselect`, `is_endresult`.
  - **Live judge digits during play:** crop the real-time judge display, threshold the
    blue channel > 100, and use the lit-pixel sum per digit as the lookup key. 6 and 9
    have equal sums, so they're told apart by one pixel. Needs the in-game option
    「判定の数リアルタイム表示」 turned on.
  - **Result judge digits:** `imagehash.phash` per digit vs stored hashes.
  - Title, score, lamp and the rest are delegated to inf-notebook's `recog` module.
- `src/dxcam_window_capture.py`: finds the monitor of the game window
  (`MonitorFromWindow`), creates a dxcam camera for the matching DXGI output, and
  resizes frames to 1920×1080. Retries with backoff.
- Capture options in its settings: direct GDI (default), legacy direct, Spout.
- It works only from screen images, with no memory reading.

### inf-notebook — https://github.com/kaktuswald/inf-notebook (NO licence file found)
Source of the ready-made recognition tables. Last commit seen: 2026-10-15.
- `recog.py`
  - **Title on song select:** `Recognition.MusicSelect.get_songname`, around line 756.
  - **Title on result:** `Recognition.Result.Informations.get_songname`, around line
    100.
  - **Method:** crop the area at fixed 1920×1080 coordinates and threshold each RGB
    channel into a binary mask. Pack every 4 pixels of a row into a hex nibble, so each
    row becomes a string key. Walk a nested dict (a trie), row by row, until reaching a
    `str` title.
  - **Fallback order for titles:** infinitas, then leggendaria, then arcade tables.
  - The result screen picks blue, red or gray text colour by pixel count.
  - Levels, notes, scores, miss count, lamps and DJ level use the same
    "mask → hex → table" idea.
- `resources.py`
  - Loads `resources/<name><version>.res`. These are **pickle** files, some
    gzip-compressed (`load_resource_serialized(name, compress)`).
  - Downloads updates from Google Cloud Storage buckets (names in `storage.py`, around
    line 27).
- Bundled tables in `resources/`:
  - `musicselect2.3.res`, `informations4.1.res`, `details3.2.res`,
    `screenrecognition1.0.res`, `musictable1.2.res`, `notesradar1.2.res`
    (gzip), `unofficialdifficulty1.0.res`, `resultothers1.0.res`,
    `resultrecognition1.0.res`, `musicnamechanges.res`.
  - Versions are in `define.py`.
- `notesradar1.2.res`
  - **Safety:** inspected with `pickletools` (not unpickled). It holds plain
    dict/list/float/int/str data with **no GLOBAL opcodes**.
  - **Shape (seen):** `{ 'SP'|'DP': { 'musics': { <title>: { <difficulty>: { 'notes',
    'radars': { NOTES, CHORD, PEAK, CHARGE, SCRATCH, SOF-LAN } } } }, 'attributes': ... } }`.
  - **Coverage:** includes INFINITAS-only songs (e.g. "Chocolate Planet").
- **Checked 2026-11-23** (commit `f43158edfb65006c976ed7785cfa7b066c3ffcf4`, inspected
  with `pickletools`, never unpickled):
  - `musictable1.2.res` has **no BPM**. It has no int or float opcodes, only versions,
    titles and level strings.
  - There are no global references in `musictable`, `notesradar` or `deeper0.3`
    (`deeper` holds unofficial levels, notes, clear rates and max EX).
  - `screenrecognition`, `musicselect`, `informations`, `details`, `resultothers` and
    `resultrecognition` **do** reference globals: `builtins.slice`, `numpy.dtype`,
    `numpy._core.multiarray.scalar`, `numpy._core.numeric._frombuffer`,
    `numpy._core.multiarray._reconstruct` and `numpy.ndarray`. A `find_class` that always
    raises can't read them (see plan 1, Roadmap).
  - `musicnamechanges.res` is plain JSON (a list of [old, new] title pairs).
- Building tables: `resources_learning_musicselect.py` (e.g.
  `learning_songname_infinitas`, around line 677) builds the tries from labelled
  screenshots.

**Rules for using inf-notebook:**
- Learn from the method, but don't copy its code (no licence).
- Never redistribute its `.res` files in a public repo or release. Fetch them at
  runtime or setup.
- Convert pickles to JSON with a restricted `pickle.Unpickler` whose `find_class`
  always raises. The app only ever reads the JSON.

### Other
- **Reflux** — https://github.com/olji/Reflux (MIT): reads INFINITAS memory. Out of
  scope (no memory reading), noted for reference only.
- **iidx.directory / iidx-db** — https://github.com/vanHavel/iidx-db (MIT): INFINITAS chart
  directory built from a Reflux dump. No radar.
- **INFINITAS Notes Radar:** added to INFINITAS on 2026-03-12 (RemyWiki,
  CS_INFINITAS_2020).
- **Window mode:** a community "custom launcher for beatmania IIDX Infinitas with
  window mode and zoom in functions" is listed under GitHub topic `iidx`. It's a
  fallback for the capture spike if exclusive fullscreen blocks capture.

## User context
- **Gaming PC:** Windows, about 5 GB free on C:, so keep installs off C:. Development
  is on a Mac.
- **Official score export** (CSV, Japanese headers): `バージョン,タイトル,アーティスト,`
  then per difficulty (BEGINNER, NORMAL, HYPER, ANOTHER, LEGGENDARIA):
  `スコア, 最終スコア更新時刻, ミスカウント, クリアタイプ, プレー回数, 最終プレー日時`.
  - `---` means empty.
  - Lamp `NO PLAY` with a play count > 0 means the song was quit mid-play.
  - There's a trailing empty column.
  - Titles can contain full-width commas `，`.
