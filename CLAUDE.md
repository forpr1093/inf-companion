# inf-companion

A local companion app for beatmania IIDX INFINITAS:
- A Python background process captures the game window, recognises screens, songs and
  results, reads the controller, and stores play records.
- A web page served on localhost shows on a second monitor: a key lane with floating
  notes, a button counter, a BPM-synced GIF, and results/history. SP only, 1P or 2P side.

Read first:
- `docs/superpowers/specs/2026-11-23-infinitas-companion-design.md` — the design
  (source of truth).
- `docs/research-notes.md` — how the reference projects work, file pointers, data
  shapes.

## Hard rules
- **No memory reading or injection into INFINITAS.** Image-only recognition.
- **Never load pickle files at runtime.** inf-notebook `.res` tables are converted
  offline by `tools/convert_tables.py` with a restricted unpickler (no globals allowed).
  The app reads only the JSON output.
- **Never commit inf-notebook's `.res` files or the converted tables.** inf-notebook
  has no licence. Tables are fetched at setup/runtime. Keep `data/` and `tables/` in
  `.gitignore`.
- **Never commit or bundle skin images.** Skins (e.g. WMII_FHD) live in `skins/`, which
  is gitignored except `skins/.gitkeep`. Their terms ban redistribution.
- **Don't copy inf-notebook code verbatim.** Re-implement the method (crop → channel
  threshold → hex-packed rows → trie lookup).
- **The game comes first.** Capture and recognition run in a separate process, at an
  adaptive low frame rate, on crops only. Controller input never waits on recognition.
- **Keep the gaming PC's C: drive clean.** No OpenCV (numpy + Pillow only), and keep
  dependencies minimal. Install paths must be configurable.

## Stack
- **Python** via `uv` (`pyproject.toml` + `uv.lock`). Package: `inf_companion`. Entry
  point: `inf-companion`.
- **Capture backends:** `dxcam`, `window` (GDI/PrintWindow), optional `wgc`, and
  `replay` (folder or video; runs on macOS).
- **Input:** SDL2 via `pysdl2` + `pysdl2-dll`.
- **Server:** Starlette + uvicorn (static page, websocket events, small REST API).
- **Storage:** SQLite.
- **Web:** Vite + Svelte + PixiJS in `web/`. The build output is served by the Python
  app.

## Workflow
- Develop on macOS with `inf-companion --capture replay --source <dir|video>`. Only
  capture needs Windows.
- **Windows testing:** `git pull && uv run inf-companion`, with `UV_PYTHON_INSTALL_DIR`
  and `UV_CACHE_DIR` set to a non-C drive.
- **Releases:** GitHub Actions `windows-latest`, PyInstaller one-folder zip, tables not
  bundled.
- **Tests:** recognition against fixture screenshots in `tests/fixtures/` (which are the
  user's own captures), plus state-machine tests driven by replay sequences.
- Use the superpowers skills: brainstorming → writing-plans → TDD.
