# Web App and Key Input Implementation Plan (Plan 1 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Python app that reads the controller and pushes key events over a websocket to a second-monitor web page. The page shows the 2DX-style lane with notes floating up (skinned from the local WMII_FHD skin), the button counter, the BPM-synced GIF, and settings and bindings. All of it works on macOS without any screen capture.

**Architecture:** One Python process (`inf-companion`): an SDL2 input thread turns raw controller events into lane events through a pure mapper. An `EventBus` hands events to a Starlette websocket. SQLite stores settings and bindings. A Vite + Svelte + PixiJS page is built into `inf_companion/web_dist/` and served by the same process. Capture and recognition come in Plans 2 and 3 (see Roadmap at the end).

**Tech Stack:** Python 3.12 via uv, Starlette, uvicorn + websockets, pysdl2 + pysdl2-dll, sqlite3 (stdlib), pytest + httpx. Web: Vite 6, Svelte 5, TypeScript, PixiJS 8, gifuct-js 2, Vitest 3.

**Spec:** `docs/superpowers/specs/2026-11-23-infinitas-companion-design.md` (approved 2026-11-23). Also read `CLAUDE.md`.

**Order change (user, 2026-11-23):** the user wants the UI design and key tracking proven before any capture work. So this plan covers spec §5.4, §5.7, and the §5.8 lane, GIF and settings parts. The capture spike (§7) is the first task of Plan 2.

## Global Constraints

- No memory reading or injection into INFINITAS. This plan doesn't touch the game at all.
- Never load pickle files at runtime. (Nothing in this plan reads tables.)
- Keep `data/`, `tables/` and `skins/*` (except `skins/.gitkeep`) in `.gitignore`. `.gitignore` already exists (created 2026-11-23). Never commit or bundle skin images: the WMII_FHD terms ban redistribution.
- The skin lives at `skins/WMII_FHD/` (the `skin_dir` setting). Sprite boxes and lane sizes come from spec §5.9.
- No OpenCV. Keep Python dependencies to: `starlette`, `uvicorn`, `websockets`, `pysdl2`, `pysdl2-dll`. Dev only: `pytest`, `httpx`.
- Install and data paths must be configurable: `--data-dir`, or the `INF_COMPANION_DATA` env var, with default `./data` next to the project.
- Controller input never waits on anything else. The input thread only does non-blocking publishes.
- Key press to note shown on the page: under 30 ms on the same PC (spec §8).
- SP only. The lane has scratch plus 7 keys. The scratch is on the left for 1P and on the right for 2P.
- Listen on `127.0.0.1` by default. Default port `8765`.
- Respect `prefers-reduced-motion`.
- Node is only needed on the Mac. The built page is committed in `inf_companion/web_dist/` so Windows can run `git pull && uv run inf-companion` with no Node (builder's call, flagged for the user).

## Review Focus

1. **Turntable axis wrap-around.** Spinning one way, the axis jumps from about +32767 to about −32768. This must read as the same direction continuing, not a reversal. Test: Task 5 `test_axis_wraparound_continues_same_direction`.
2. **Controller plugged in after start, or unplugged and replugged.** The app keeps running, picks the device up again by GUID with its saved binding, and sends `devices`. Any key held on a removed device is released. Test: Task 7 `test_device_removed_releases_held_keys`.
3. **Page loads before the server, or the server restarts.** The page reconnects with backoff, gets `hello` again, clears any notes still held, and takes its counts from `hello`. After a server restart that means zero, because counts reset on app start. Tests: Task 8 `ws client reconnects and emits reset`, Task 10 `releaseAll on reset`, Task 12 `hello replaces local counts`.
4. **Fast repeats (trills, more than 20 presses/s on one key) and a slow or stalled browser tab.** Every press makes a note and adds exactly 1 to the count, in order. A stalled tab never blocks the input thread. Each subscriber queue drops its oldest events when full. Tests: Task 2 `test_full_queue_drops_oldest_and_never_blocks`, Task 10 `rapid presses each spawn a note`, Task 7 `test_counts_follow_key_downs_only`.
5. **Skin folder missing, incomplete, or asked for a file outside it.** `/skin/...` serves only `.png` files that resolve inside `skin_dir`. `..`, absolute paths, and symlinks pointing out of the folder all get 404. A missing skin or file makes the lane fall back to drawn shapes, never a broken page. Tests: Task 4 `test_skin_route_blocks_escape`, Task 11 `missing sprite falls back`.

Also covered, but less likely to bite: a bad GIF upload or all-zero frame delays (Task 4 `test_gif_upload_rejects_non_gif_and_keeps_old`, Task 14 `zero delays treated as 100 ms`).

---

## File Structure

```
pyproject.toml, uv.lock, .python-version (3.12), .gitignore
inf_companion/
  __init__.py            __version__ = "0.1.0"
  cli.py                 argument parsing, wiring, uvicorn.run
  paths.py               data dir resolution
  events.py              EventBus, make_event
  settings.py            DEFAULT_SETTINGS, validate_settings_patch
  storage/db.py          open_db + migrations, SettingsRepo, BindingsRepo
  input/model.py         RawEvent, Source, Binding, KeyEvent, DeviceInfo, TARGETS
  input/mapper.py        InputMapper (pure)
  input/binder.py        BindingSession (pure)
  input/counter.py       PressCounter (pure)
  input/sdl_source.py    SdlInputThread (SDL2, hardware)
  input/service.py       InputService (glue: thread + mapper + binder + bus)
  server/app.py          create_app(ctx) -> Starlette
  server/skin.py         safe skin file resolution + listing
  web_dist/              built page (committed)
skins/.gitkeep           (skins/WMII_FHD is local only, gitignored)
tests/
  test_paths.py test_events.py test_storage.py test_server.py test_skin.py
  input/test_mapper.py input/test_binder.py input/test_counter.py input/test_service.py
web/
  package.json vite.config.ts tsconfig.json index.html
  src/main.ts src/App.svelte
  src/lib/events.ts      event types (mirrors the Python event shapes)
  src/lib/ws.ts          websocket client with reconnect
  src/lib/stores.ts      connection, settings, devices, bindings stores
  src/lib/demo.ts        synthetic key-event generator + dev keyboard input
  src/lib/theme.css      design tokens
  src/lib/lane/layout.ts laneLayout (pure)
  src/lib/lane/notes.ts  NoteField model (pure)
  src/lib/lane/skin.ts   WMII_FHD sprite map + loader with fallback
  src/lib/lane/Lane.svelte  PixiJS renderer
  src/lib/counter/counts.ts  applyKey, emptyCounts (pure)
  src/lib/counter/Counter.svelte
  src/lib/gif/rate.ts    loopRate, normaliseDelays (pure)
  src/lib/gif/GifPlayer.svelte
  src/display/Display.svelte   second-monitor layout
  src/settings/Settings.svelte src/settings/Bindings.svelte
  src/**/*.test.ts       Vitest
```

## Wire protocol (used by Tasks 2–14)

Every server→page event is a JSON object made by `make_event(type, **fields)`. It always has `type` and `at` (epoch ms, float, from `time.time()*1000`, used for the latency overlay).

| type | fields |
|---|---|
| `hello` | `version: str`, `settings: dict`, `devices: [DeviceInfo]`, `bindings: {guid: Binding}`, `has_gif: bool`, `counts: Counts` |
| `counts` | `counts: Counts`. Sent only after a reset. Between resets the page adds 1 per `key_down` itself. |
| `settings` | `settings: dict` (full, after a change) |
| `devices` | `devices: [DeviceInfo]` where DeviceInfo = `{guid, name, bound: bool}` |
| `key_down` / `key_up` | `lane: "S"\|"1".."7"`, `dir: "up"\|"down"\|null` (scratch only), `t: float` (ms, `time.perf_counter()*1000` at the source) |
| `bind_step` | `target: "1".."7"\|"S_up"\|"S_down"`, `index: int`, `total: 9` |
| `bind_done` | `binding: Binding` |
| `bind_cancelled` | — |
| `gif` | `version: int` (bumped on upload) |
| `error` | `message: str` |

Page→server messages on the same socket: `{"type":"bind_start"}`, `{"type":"bind_cancel"}`, `{"type":"counts_reset"}`.

`Counts` is `{"1": int, …, "7": int, "S_up": int, "S_down": int}`, keyed by `TARGETS`. A scratch `key_down` with `dir: "up"` counts toward `S_up`, and `dir: "down"` toward `S_down`.

Binding JSON: `{"device_guid": str, "name": str, "map": {target: Source}}`. Source is one of `{"kind":"button","index":n}`, `{"kind":"axis","index":n,"sign":1|-1}` or `{"kind":"hat","index":n,"mask":m}`. `TARGETS = ("1","2","3","4","5","6","7","S_up","S_down")`.

---

### Task 1: Python project scaffold and CLI

**Files:**
- Create: `pyproject.toml`, `.python-version`, `inf_companion/__init__.py`, `inf_companion/paths.py`, `inf_companion/cli.py`
- Already present: `.gitignore`, `skins/.gitkeep`
- Test: `tests/test_paths.py`

**Interfaces:**
- Produces: `resolve_data_dir(arg: str | None, env: Mapping[str, str] = os.environ) -> Path` (argument first, then `INF_COMPANION_DATA`, then `Path.cwd() / "data"`. It creates the folder and returns an absolute path). `parse_args(argv: list[str] | None) -> argparse.Namespace` with `--host` (default `127.0.0.1`), `--port` (int, `8765`), `--data-dir` (default None) and `--no-input` (flag: don't start SDL). `main(argv=None) -> int`.
- `pyproject.toml`: `requires-python = ">=3.12"`, `[project.scripts] inf-companion = "inf_companion.cli:main"`, the runtime dependencies from Global Constraints, and `[dependency-groups] dev = ["pytest", "httpx"]`. Build backend `hatchling` with `inf_companion/web_dist/**` included as package data.
- `.gitignore` already ignores `data/`, `tables/`, `skins/*` (except `!skins/.gitkeep`), `.venv/`, `__pycache__/`, `web/node_modules/` and `.DS_Store`. **Don't** add `inf_companion/web_dist/`. Before committing, `git status --short -uall skins` must show only `skins/.gitkeep`.

- [ ] **Step 1: Write the failing tests**

```python
def test_arg_wins_over_env(tmp_path):
    p = resolve_data_dir(str(tmp_path / "a"), env={"INF_COMPANION_DATA": str(tmp_path / "b")})
    assert p == (tmp_path / "a").resolve() and p.is_dir()

def test_env_used_when_no_arg(tmp_path):
    assert resolve_data_dir(None, env={"INF_COMPANION_DATA": str(tmp_path / "b")}) == (tmp_path / "b").resolve()

def test_default_is_cwd_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert resolve_data_dir(None, env={}) == (tmp_path / "data").resolve()

def test_parse_args_defaults():
    a = parse_args([])
    assert (a.host, a.port, a.data_dir, a.no_input) == ("127.0.0.1", 8765, None, False)
```

- [ ] **Step 2:** `uv run pytest tests/test_paths.py -v`. Expected: FAIL (module not found).
- [ ] **Step 3:** Implement `paths.py` and `parse_args`. For now `main` only resolves the data dir, prints it and returns 0.
- [ ] **Step 4:** `uv run pytest -v` PASS, and `uv run inf-companion --data-dir /tmp/x` prints `/tmp/x`.
- [ ] **Step 5: Commit** (this first commit also adds the existing `CLAUDE.md` and `docs/`)

```bash
git add pyproject.toml uv.lock .python-version .gitignore skins/.gitkeep inf_companion tests CLAUDE.md docs
git commit -m "chore: scaffold inf_companion package and CLI"
```

### Task 2: Event bus

**Files:**
- Create: `inf_companion/events.py`
- Test: `tests/test_events.py`

**Interfaces:**
- Produces: `make_event(type: str, **fields) -> dict` (adds `type` and `at`). `class EventBus`, with:
  - `bind_loop(loop: asyncio.AbstractEventLoop) -> None`
  - `publish(event: dict) -> None`. Safe from any thread and never blocks. Before `bind_loop` it drops the event silently.
  - `subscribe(maxsize: int = 256) -> Subscription`. `Subscription` is an async iterator of events with `close()`.
  - A full subscriber queue drops its oldest event, then enqueues the new one.
- Approach: `publish` calls `loop.call_soon_threadsafe(self._fanout, event)`. `_fanout` runs on the loop and does put_nowait / drop-oldest per subscriber queue.

- [ ] **Step 1: Write the failing tests** (plain `asyncio.run`, no pytest-asyncio)

```python
def test_publish_from_thread_reaches_subscriber():
    async def run():
        bus = EventBus(); bus.bind_loop(asyncio.get_running_loop())
        sub = bus.subscribe()
        threading.Thread(target=bus.publish, args=(make_event("key_down", lane="1"),)).start()
        ev = await asyncio.wait_for(sub.__anext__(), 1)
        assert ev["type"] == "key_down" and ev["lane"] == "1" and isinstance(ev["at"], float)
    asyncio.run(run())

def test_full_queue_drops_oldest_and_never_blocks():
    async def run():
        bus = EventBus(); bus.bind_loop(asyncio.get_running_loop())
        sub = bus.subscribe(maxsize=3)
        t0 = time.perf_counter()
        for i in range(10): bus.publish({"type": "x", "i": i})
        assert time.perf_counter() - t0 < 0.05
        await asyncio.sleep(0.05)
        got = [(await sub.__anext__())["i"] for _ in range(3)]
        assert got == [7, 8, 9]
    asyncio.run(run())

def test_closed_subscription_stops_receiving(): ...  # close(), then publish, then queue stays empty
```

- [ ] **Step 2:** Run `uv run pytest tests/test_events.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement as described.
- [ ] **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat: thread-safe event bus with drop-oldest queues`.

### Task 3: Storage, settings and bindings

**Files:**
- Create: `inf_companion/settings.py`, `inf_companion/storage/__init__.py`, `inf_companion/storage/db.py`, `inf_companion/input/__init__.py`, `inf_companion/input/model.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- `settings.py`: `DEFAULT_SETTINGS = {"side": "1P", "manual_bpm": 150, "beats_per_loop": 4, "theme": "dark", "orientation": "auto", "skin_dir": "skins/WMII_FHD", "skin_notes": "default", "skin_frame": "SpaceShip", "skin_beam": "defalut", "skin_flash": "blue246red1357", "skin_lane": "default", "skin_turntable": "simpleBlue_whiteLine"}`. (`defalut` is the file's real spelling.) `validate_settings_patch(patch: dict) -> dict` raises `ValueError` on an unknown key or bad value. The rules:
  - side ∈ {"1P","2P"}
  - manual_bpm a number with 30 ≤ x ≤ 999
  - beats_per_loop an int with 1 ≤ x ≤ 64
  - theme ∈ {"dark","light"}
  - orientation ∈ {"auto","landscape","portrait"}
  - skin_dir a non-empty string (relative paths resolve against the working directory)
  - each other `skin_*` value matches `^[A-Za-z0-9_\-]{1,64}$`, since it's a file-name stem
- `input/model.py` (frozen dataclasses with `to_json()` / `from_json()`):
  - `Source(kind: Literal["button","axis","hat"], index: int, sign: int = 0, mask: int = 0)`
  - `Binding(device_guid: str, name: str, map: dict[str, Source])`
  - `RawEvent(device_guid: str, kind: Literal["button","axis","hat"], index: int, value: int, t: float)`
  - `KeyEvent(lane: str, down: bool, t: float, dir: str | None = None)`
  - `DeviceInfo(guid: str, name: str, bound: bool)`
  - `TARGETS`
- `storage/db.py`:
  - `open_db(path: Path) -> sqlite3.Connection` uses WAL and `check_same_thread=False`, and migrates by `PRAGMA user_version`. Migration 1 creates `settings(key TEXT PRIMARY KEY, value TEXT NOT NULL)` and `bindings(device_guid TEXT PRIMARY KEY, name TEXT NOT NULL, map TEXT NOT NULL, updated_at TEXT NOT NULL)`.
  - `SettingsRepo(conn)` with `get_all() -> dict` (defaults merged with stored values) and `update(patch) -> dict` (validates, stores, returns the full settings).
  - `BindingsRepo(conn)` with `all() -> dict[str, Binding]`, `get(guid) -> Binding | None` and `put(binding) -> None`.
  - Repos guard writes with a `threading.Lock`.
- DB file: `<data_dir>/companion.sqlite3`.

- [ ] **Step 1: Write the failing tests**

```python
def test_defaults_then_update_persists(tmp_path):
    conn = open_db(tmp_path / "c.sqlite3"); s = SettingsRepo(conn)
    assert s.get_all() == DEFAULT_SETTINGS
    assert s.update({"side": "2P"})["side"] == "2P"
    assert SettingsRepo(open_db(tmp_path / "c.sqlite3")).get_all()["side"] == "2P"

@pytest.mark.parametrize("patch", [{"side": "3P"}, {"manual_bpm": 0}, {"beats_per_loop": 1.5}, {"nope": 1}, {"skin_notes": "../x"}, {"skin_dir": ""}])
def test_invalid_patch_rejected_and_nothing_stored(tmp_path, patch):
    s = SettingsRepo(open_db(tmp_path / "c.sqlite3"))
    with pytest.raises(ValueError): s.update(patch)
    assert s.get_all() == DEFAULT_SETTINGS

def test_binding_round_trip(tmp_path):
    b = Binding("g1", "Pad", {"1": Source("button", 0), "S_up": Source("axis", 0, sign=1), "S_down": Source("axis", 0, sign=-1)})
    r = BindingsRepo(open_db(tmp_path / "c.sqlite3")); r.put(b)
    assert r.get("g1") == b and r.all() == {"g1": b}

def test_reopen_does_not_rerun_migrations(tmp_path): ...  # user_version == 1 after opening twice
```

- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat: sqlite settings and bindings storage`.

### Task 4: HTTP + websocket server

**Files:**
- Create: `inf_companion/server/__init__.py`, `inf_companion/server/app.py`, `inf_companion/server/skin.py`
- Modify: `inf_companion/cli.py` (build the context and run uvicorn)
- Test: `tests/test_server.py`, `tests/test_skin.py`

**Interfaces:**
- Consumes: `EventBus`, `make_event` (Task 2), `SettingsRepo`, `BindingsRepo` (Task 3).
- Produces:
  - `@dataclass AppContext(bus, settings, bindings, data_dir: Path, static_dir: Path | None, input: InputLike | None = None)`. `InputLike` is a Protocol with `devices() -> list[DeviceInfo]`, `counts() -> dict[str, int]` and `handle_client(msg: dict) -> None`. With `input=None`, `hello.counts` is all zeros.
  - `server/skin.py`:
    - `resolve_skin_file(skin_dir: Path, rel: str) -> Path | None` returns the resolved path only when `rel` ends in `.png`, isn't absolute, and `path.resolve()` is inside `skin_dir.resolve()` (`Path.is_relative_to`) and is a file. Otherwise it returns None.
    - `list_skin(skin_dir: Path) -> dict` returns `{"available": bool, "notes": [...], "frames": [...], "beams": [...], "flashes": [...], "lanes": [...], "turntables": [...]}`. Each list holds the sorted `.png` stems of `play/parts/notes`, `play/parts/frame/Wide`, `play/parts/laser`, `play/parts/keyflash`, `play/parts/lane` and `play/parts/turntable`. `available` is true only when `skin_dir/play/parts/notes` exists.
  - `create_app(ctx) -> Starlette`. The app's startup calls `ctx.bus.bind_loop(asyncio.get_running_loop())`.
- Routes:
  - `GET /api/settings` → settings dict.
  - `PATCH /api/settings` (JSON) → 200 with the full settings and a `settings` event published, or 400 `{"error": msg}`.
  - `GET /api/bindings` → `{guid: Binding}`.
  - `PUT /api/gif` (raw body, `Content-Type: image/gif`) → 204 and a `gif` event. It writes to `<data_dir>/loop.gif` atomically (temp file + `os.replace`). It rejects with 415 when the body doesn't start with `GIF87a`/`GIF89a`, and with 413 when the body is over 20 MB. It returns 400 when the body is empty.
  - `GET /api/gif` → the file with `Cache-Control: no-store`, or 404.
  - `GET /api/skin` → `list_skin(current skin_dir)`.
  - `GET /skin/{rel:path}` → `FileResponse` for `resolve_skin_file(current skin_dir, rel)`, with `Cache-Control: max-age=3600`, or 404. `skin_dir` is read from settings on each request, so a settings change applies without a restart.
  - `WS /ws`: sends `hello` first, then forwards bus events. Incoming JSON goes to `ctx.input.handle_client` when input is present.
  - `/` → `StaticFiles(directory=static_dir, html=True)` when static_dir exists. Otherwise a plain-text page: "web page not built; run npm run build in web/".
- `cli.main` uses `static_dir = Path(inf_companion.__file__).parent / "web_dist"`, and runs `uvicorn.run(app, host, port, log_level="warning")`.

- [ ] **Step 1: Write the failing tests** (Starlette `TestClient` with a temp data dir and `input=None`)

```python
def test_ws_hello_then_bus_events(client, ctx):
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["settings"]["side"] == "1P" and hello["has_gif"] is False
        ctx.bus.publish(make_event("key_down", lane="3", dir=None, t=1.0))
        assert ws.receive_json()["lane"] == "3"

def test_patch_settings_broadcasts(client): ...  # PATCH {"side":"2P"} -> 200, ws receives {"type":"settings", ...side 2P}
def test_patch_settings_invalid_400(client): ...  # {"manual_bpm": -1} -> 400, body has "error"

def test_gif_upload_rejects_non_gif_and_keeps_old(client):
    good = b"GIF89a" + b"\x00" * 10
    assert client.put("/api/gif", content=good, headers={"content-type": "image/gif"}).status_code == 204
    assert client.put("/api/gif", content=b"\x89PNG....", headers={"content-type": "image/gif"}).status_code == 415
    assert client.put("/api/gif", content=b"", headers={"content-type": "image/gif"}).status_code == 400
    assert client.get("/api/gif").content == good

def test_gif_too_large_413(client): ...  # 20 MB + 1 byte
def test_root_without_build_says_not_built(client): ...  # static_dir=None -> 200 text contains "not built"
```

```python
# tests/test_skin.py: build a tiny fake skin in tmp_path (play/parts/notes/default.png, etc.)
def test_resolves_png_inside(skin):
    assert resolve_skin_file(skin, "play/parts/notes/default.png") == (skin / "play/parts/notes/default.png").resolve()

@pytest.mark.parametrize("rel", ["../secret.png", "/etc/passwd", "play/parts/notes/default.lua", "play/parts/notes/missing.png"])
def test_skin_route_blocks_escape(skin, rel):
    assert resolve_skin_file(skin, rel) is None

def test_symlink_out_of_skin_blocked(skin, tmp_path): ...  # skin/evil.png -> tmp_path/outside.png => None
def test_list_skin(skin): ...                              # available True, notes == ["default"]; missing dir -> available False, lists empty
def test_skin_http_404_and_200(client_with_skin): ...      # GET /skin/../x.png -> 404; a real file -> 200 image/png
```

- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS.
- [ ] **Step 5:** Manual check: `uv run inf-companion --no-input` serves `http://127.0.0.1:8765/api/settings`.
- [ ] **Step 6:** Commit `feat: starlette server with settings, gif, skin files and websocket`.

### Task 5: Input mapper (raw controller events → lane events)

**Files:**
- Create: `inf_companion/input/mapper.py`
- Test: `tests/input/test_mapper.py`

**Interfaces:**
- Consumes: `RawEvent`, `Source`, `Binding`, `KeyEvent` (Task 3).
- Produces: `InputMapper(bindings: dict[str, Binding], axis_deadband: int = 64, scratch_release_ms: float = 80.0)`, with:
  - `set_bindings(bindings) -> None`
  - `feed(ev: RawEvent) -> list[KeyEvent]`
  - `tick(t: float) -> list[KeyEvent]` (scratch idle release)
  - `release_device(guid: str, t: float) -> list[KeyEvent]`
  - `release_all(t: float) -> list[KeyEvent]`
- Rules:
  - A button source fires down when value is 1 and up when value is 0.
  - A hat source is down while `value & mask`.
  - `"1".."7"` map to lanes with that name. `S_up` and `S_down` map to lane `"S"` with `dir` "up" or "down".
  - Never emit a down for a lane+dir that is already down, or an up for one that isn't.
  - Axis scratch: the first value seen for an axis only primes it. After that, compute `delta = ((v - last + 32768) % 65536) - 32768`. If `|delta| > axis_deadband`, the direction is `sign(delta)`. If that direction differs from the held one, emit the up for the held one first, then the down for the new one. Each motion records `last_motion_t`. `tick(t)` releases the held scratch once `t - last_motion_t >= scratch_release_ms`.
  - Events from devices with no binding are ignored.

- [ ] **Step 1: Write the failing tests**

```python
G = "g1"
def binding():
    m = {str(i): Source("button", i - 1) for i in range(1, 8)}
    m |= {"S_up": Source("axis", 0, sign=1), "S_down": Source("axis", 0, sign=-1)}
    return Binding(G, "Pad", m)

def test_button_press_and_release_map_to_lane():
    m = InputMapper({G: binding()})
    assert m.feed(RawEvent(G, "button", 2, 1, 10.0)) == [KeyEvent("3", True, 10.0)]
    assert m.feed(RawEvent(G, "button", 2, 0, 55.0)) == [KeyEvent("3", False, 55.0)]

def test_unbound_device_ignored():
    assert InputMapper({G: binding()}).feed(RawEvent("other", "button", 0, 1, 1.0)) == []

def test_axis_motion_presses_then_idle_releases():
    m = InputMapper({G: binding()})
    assert m.feed(RawEvent(G, "axis", 0, 0, 0.0)) == []
    assert m.feed(RawEvent(G, "axis", 0, 512, 5.0)) == [KeyEvent("S", True, 5.0, "up")]
    assert m.feed(RawEvent(G, "axis", 0, 1024, 10.0)) == []
    assert m.tick(89.0) == []
    assert m.tick(90.0) == [KeyEvent("S", False, 90.0, "up")]

def test_axis_reversal_releases_then_presses_other_direction():
    m = InputMapper({G: binding()}); m.feed(RawEvent(G, "axis", 0, 0, 0.0)); m.feed(RawEvent(G, "axis", 0, 512, 5.0))
    assert m.feed(RawEvent(G, "axis", 0, 0, 20.0)) == [KeyEvent("S", False, 20.0, "up"), KeyEvent("S", True, 20.0, "down")]

def test_axis_wraparound_continues_same_direction():
    m = InputMapper({G: binding()}); m.feed(RawEvent(G, "axis", 0, 32512, 0.0))
    assert m.feed(RawEvent(G, "axis", 0, 32700, 5.0)) == [KeyEvent("S", True, 5.0, "up")]
    assert m.feed(RawEvent(G, "axis", 0, -32700, 10.0)) == []   # wrapped, still "up"

def test_jitter_inside_deadband_ignored(): ...   # 0 -> 40: []
def test_button_style_scratch(): ...             # S_up=Source("button", 8): press -> KeyEvent("S", True, t, "up")
def test_hat_mask(): ...                         # "7"=Source("hat",0,mask=4): value 6 -> down, value 2 -> up
def test_no_duplicate_down(): ...                # two value-1 events -> one KeyEvent
def test_release_all_and_release_device(): ...   # held "1" and scratch -> both ups, then [] on repeat
```

- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat: input mapper with axis scratch and wrap-around`.

### Task 6: Binding session ("press key 1 … scratch down")

**Files:**
- Create: `inf_companion/input/binder.py`
- Test: `tests/input/test_binder.py`

**Interfaces:**
- Produces: `BindingSession(device_names: dict[str, str], axis_trigger: int = 4000)`, with:
  - `current_target -> str | None`
  - `feed(ev: RawEvent) -> Binding | None`. It returns the finished `Binding` after the 9th target and None before that.
  - `index -> int`
- Rules:
  - Targets go in `TARGETS` order.
  - The first device to give a valid input becomes the session's device. Input from other devices is ignored after that.
  - A button press (value 1) assigns `Source("button", i)`. Releases are ignored.
  - A hat with value ≠ 0 assigns `Source("hat", i, mask=value)`.
  - Axis: accumulate wrap-corrected deltas from the first value seen. Once `|sum| >= axis_trigger`, assign `Source("axis", i, sign=sign(sum))` and reset all sums.
  - A source already assigned in this session (the same kind, index, sign and mask) is skipped and doesn't advance. So spinning the turntable the same way for `S_down` won't double-assign.

- [ ] **Step 1: Write the failing tests**

```python
def test_full_session_with_axis_scratch():
    s = BindingSession({"g1": "Pad"})
    for i in range(7):
        assert s.current_target == str(i + 1)
        assert s.feed(RawEvent("g1", "button", i, 1, 0.0)) is None
    s.feed(RawEvent("g1", "axis", 0, 0, 0.0)); s.feed(RawEvent("g1", "axis", 0, 5000, 1.0))
    assert s.current_target == "S_down"
    s.feed(RawEvent("g1", "axis", 0, 9000, 2.0))      # same direction again: skipped
    assert s.current_target == "S_down"
    b = s.feed(RawEvent("g1", "axis", 0, 0, 3.0))     # -9000: opposite direction
    assert b.map["S_up"] == Source("axis", 0, sign=1) and b.map["S_down"] == Source("axis", 0, sign=-1)
    assert b.device_guid == "g1" and b.name == "Pad"

def test_other_device_ignored_after_first(): ...
def test_button_release_and_duplicate_button_ignored(): ...
```

- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat: binding session`.

### Task 7: SDL input thread, press counter and input service, wired into the app

**Files:**
- Create: `inf_companion/input/sdl_source.py`, `inf_companion/input/counter.py`, `inf_companion/input/service.py`
- Modify: `inf_companion/cli.py` (start `InputService` unless `--no-input`, and stop it on shutdown)
- Test: `tests/input/test_counter.py`, `tests/input/test_service.py`

**Interfaces:**
- Consumes: `InputMapper` (T5), `BindingSession` (T6), `BindingsRepo` (T3), `EventBus` / `make_event` (T2), `AppContext.input` protocol (T4).
- Produces:
  - `SdlInputThread(on_raw: Callable[[RawEvent], None], on_devices: Callable[[list[tuple[str, str]]], None], on_idle: Callable[[float], None])`, with `start()` and `stop()`.
    - It sets the hint `SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS="1"` before `SDL_Init(SDL_INIT_JOYSTICK)`.
    - It loops on `SDL_WaitEventTimeout(event, 5)`. It handles JOYAXISMOTION, JOYBUTTONDOWN/UP, JOYHATMOTION and JOYDEVICEADDED/REMOVED (open or close the joystick, then call `on_devices` with `(guid_string, name)` pairs).
    - Timestamp: `time.perf_counter()*1000` when the event is taken from the queue.
    - It calls `on_idle(now)` every loop iteration.
    - Use joystick (not game controller) APIs: IIDX controllers are rarely standard gamepads.
  - `PressCounter()` with `add(ev: KeyEvent) -> None`, `snapshot() -> dict[str, int]` and `reset() -> None`. Only `down=True` events count. Lane `"S"` counts toward `S_up` or `S_down` by `dir`. The snapshot always has all 9 `TARGETS` keys. It's created fresh with the service, so counts reset on app start.
  - `InputService(bus: EventBus, bindings: BindingsRepo, source_factory=SdlInputThread)`, with:
    - `start()` and `stop()`
    - `devices() -> list[DeviceInfo]`
    - `counts() -> dict[str, int]`
    - `handle_client(msg: dict) -> None` (handles `bind_start`, `bind_cancel` and `counts_reset`; the last resets the counter and publishes a `counts` event)
    - `handle_raw(ev: RawEvent)`, `handle_devices(pairs)` and `handle_idle(t)`. These are the callbacks, public so tests can drive them.
  - Behaviour:
    - Mapper output goes to `PressCounter.add` and is then published as `key_down` / `key_up` with `lane`, `dir` and `t`. Counting is in memory and doesn't block.
    - While a binding session is active, raw events go only to the session (no key events). It publishes `bind_step` after each advance. On completion it saves the binding, updates the mapper, and publishes `bind_done` and then `devices`.
    - When a device is removed, call `mapper.release_device` and publish the ups.
    - `devices` events mark `bound` from the repo.

- [ ] **Step 1: Write the failing tests** (a fake source factory and a real `EventBus` bound to a loop. Collect published events through a subscription.)

```python
def test_raw_button_publishes_key_down(svc, events):
    svc.handle_devices([("g1", "Pad")]); svc.handle_raw(RawEvent("g1", "button", 0, 1, 3.0))
    assert {"type": "key_down", "lane": "1", "dir": None, "t": 3.0}.items() <= events()[-1].items()

def test_bind_flow_saves_and_stops_key_events(svc, events, repo): ...  # bind_start -> bind_step target "1"; 7 buttons + 2 axis moves -> bind_done, repo.get("g1") set; no key_down while binding
def test_bind_cancel(svc, events): ...                                # -> bind_cancelled, keys flow again
def test_device_removed_releases_held_keys(svc, events):
    svc.handle_devices([("g1", "Pad")]); svc.handle_raw(RawEvent("g1", "button", 0, 1, 1.0))
    svc.handle_devices([])
    assert any(e["type"] == "key_up" and e["lane"] == "1" for e in events())
def test_idle_tick_releases_scratch(svc, events): ...
def test_counts_reset_publishes_zeros(svc, events): ...  # press "1"; handle_client({"type":"counts_reset"}) -> counts event all 0; svc.counts()["1"] == 0
```

```python
# tests/input/test_counter.py
def test_counts_follow_key_downs_only():
    c = PressCounter()
    for t in range(25): c.add(KeyEvent("4", True, t)); c.add(KeyEvent("4", False, t + 0.5))
    c.add(KeyEvent("S", True, 30, "up")); c.add(KeyEvent("S", True, 31, "down")); c.add(KeyEvent("S", False, 32, "down"))
    s = c.snapshot()
    assert s["4"] == 25 and s["S_up"] == 1 and s["S_down"] == 1 and s["1"] == 0 and set(s) == set(TARGETS)

def test_reset_zeroes_all(): ...
```

(The fixture pre-loads a binding for `g1` with buttons 0–6 and axis 0.)

- [ ] **Step 2:** FAIL. **Step 3:** Implement `service.py`, then `sdl_source.py`. **Step 4:** PASS.
- [ ] **Step 5: Manual test on the Mac with the controller.** Run `uv run inf-companion`, then `websocat ws://127.0.0.1:8765/ws` (or a browser console `new WebSocket(...)`). Send `{"type":"bind_start"}`, follow the steps, then press keys and spin the turntable. Expected: one `key_down`/`key_up` pair per press, scratch `up`/`down` matching the spin direction, and a release about 80 ms after the turntable stops. If the controller's turntable is an axis that never wraps, or reports large jumps, note it in the commit message.
- [ ] **Step 6:** Commit `feat: SDL2 input thread, press counter and input service`.

### Task 8: Web scaffold, websocket client, stores, build into `web_dist`

**Files:**
- Create: `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `web/index.html`, `web/src/main.ts`, `web/src/App.svelte`, `web/src/lib/events.ts`, `web/src/lib/ws.ts`, `web/src/lib/stores.ts`
- Test: `web/src/lib/ws.test.ts`
- Create (built): `inf_companion/web_dist/*`

**Interfaces:**
- `vite.config.ts`: `build.outDir = "../inf_companion/web_dist"`, `emptyOutDir: true`. The dev server proxies `/api` and `/ws` (ws: true) to `http://127.0.0.1:8765`.
- `events.ts`: TS types for every row of the wire-protocol table (`ServerEvent` union, discriminated on `type`) plus `Binding`, `Source` and `DeviceInfo`. Also `type Lane = "S" | "1" | "2" | "3" | "4" | "5" | "6" | "7"` and `type KeyEvent = { type: "key_down" | "key_up"; lane: Lane; dir: "up" | "down" | null; t: number; at: number }`. The demo and the dev keyboard produce the same `KeyEvent` shape, with `at = Date.now()`. Also `type Counts` (wire protocol), `type Settings` (mirrors the Python `DEFAULT_SETTINGS` keys, Task 3) and `const DEFAULTS: Settings` with the same default values.
- `ws.ts`: `connect(url: string, handlers: { onEvent(e: ServerEvent): void; onStatus(s: "connecting" | "open" | "closed"): void; onReset(): void }, opts?: { WebSocketImpl?: typeof WebSocket; backoffMs?: number[] }) -> { send(msg: object): void; close(): void }`. Backoff is `[500, 1000, 2000, 5000]`, then 5000 repeating. `onReset` fires on every (re)open, before the `hello` is delivered.
- `stores.ts`: writable stores `status`, `settings`, `devices`, `bindings`, `hasGif`, `gifVersion`, `bindProgress` (`{target, index, total} | null`) and `counts` (`Counts`, replaced by `hello.counts` and by `counts` events). It also exports a key pub/sub: `emitKey(e: KeyEvent) -> void` and `subscribeKeys(fn: (e: KeyEvent) => void) -> () => void`. The ws handler, the demo and the dev keyboard all call `emitKey`. `subscribeReset(fn) -> () => void` fires on `onReset`. Key events don't go through Svelte stores because they're too frequent. Plus `patchSettings(patch) -> Promise<void>` (PATCH /api/settings).
- `App.svelte`: hash routing, `#/` → Display, `#/settings` → Settings (placeholders until Tasks 9 and 11).
- `package.json` scripts: `dev`, `build`, `test` (`vitest run`).

- [ ] **Step 1: Write the failing test**

```ts
test("ws client reconnects and emits reset", async () => {
  vi.useFakeTimers();
  const sockets: FakeWS[] = [];  // FakeWS records instances and exposes open()/close()/message()
  const events: string[] = [];
  connect("ws://x/ws", { onEvent: e => events.push(e.type), onStatus: s => events.push(s), onReset: () => events.push("reset") },
          { WebSocketImpl: fakeWsFactory(sockets), backoffMs: [10] });
  sockets[0].open(); sockets[0].message({ type: "hello" }); sockets[0].close();
  await vi.advanceTimersByTimeAsync(10);
  sockets[1].open();
  expect(events).toEqual(["connecting", "open", "reset", "hello", "closed", "connecting", "open", "reset"]);
});
```

- [ ] **Step 2:** `cd web && npm test`. Expected: FAIL.
- [ ] **Step 3:** Implement. **Step 4:** PASS.
- [ ] **Step 5:** `npm run build`, then `uv run inf-companion --no-input`, and open `http://127.0.0.1:8765/`. Expected: the page loads and the status shows "open".
- [ ] **Step 6:** Commit `feat(web): vite svelte scaffold, ws client, stores` (including `inf_companion/web_dist`).

### Task 9: Display layout and visual direction (user checkpoint)

**Files:**
- Create: `web/src/display/Display.svelte`, `web/src/lib/theme.css`, `web/src/lib/demo.ts`
- Modify: `web/src/App.svelte`
- Test: `web/src/lib/demo.test.ts`

**Interfaces:**
- Consumes: stores (T8).
- Produces:
  - `startDemo(emit: (e: KeyEvent) => void, opts?: { seed?: number; bpm?: number }) -> () => void`. It makes a seeded pseudo-random stream of key_down/key_up events: 8th and 16th notes at the BPM, chords and scratch. It's used with `?demo=1` so the page can be designed with no controller or server.
  - `devKeyboard(emit) -> () => void` maps `Shift`=S, `z s x d c f v`=1–7 while the page has focus (`?dev=1`).
- Layout (second monitor):
  - **Landscape:** the lane on the left (about 30% width, full height, keeping the skin frame's 685:1080 aspect). The GIF is in the centre with the button counter below it. A right column has a "now playing" card (placeholder until Plan 3: title, difficulty, BPM showing `manual_bpm`) above a "last result" card (placeholder).
  - **Portrait:** the GIF on top, then the lane and the counter side by side, then the cards at the bottom.
  - `orientation: auto` uses `matchMedia("(orientation: portrait)")`.
  - A small connection dot in a corner.
  - For 2P the lane moves to the right edge in landscape.
- Visual direction: load the `frontend-design` skill first. A dark, arcade-cabinet feel that suits a dim room. Tokens are CSS custom properties in `theme.css` (`--bg`, `--panel`, `--text`, `--muted`, `--accent`, `--key-white`, `--key-black`, `--key-scratch`), with a light theme under `[data-theme=light]`.

- [ ] **Step 1: Write the failing test**

```ts
test("demo is deterministic and balanced", () => {
  vi.useFakeTimers();
  const a: KeyEvent[] = [], b: KeyEvent[] = [];
  const stopA = startDemo(e => a.push(e), { seed: 1, bpm: 150 }); vi.advanceTimersByTime(4000); stopA();
  const stopB = startDemo(e => b.push(e), { seed: 1, bpm: 150 }); vi.advanceTimersByTime(4000); stopB();
  expect(a.map(e => [e.type, e.lane])).toEqual(b.map(e => [e.type, e.lane]));
  expect(a.filter(e => e.type === "key_down").length).toBe(a.filter(e => e.type === "key_up").length);
});
```

- [ ] **Step 2:** FAIL. **Step 3:** Implement demo, layout and theme. Use plain placeholder boxes where the lane and the counter go (Tasks 10–12 fill them).
- [ ] **Step 4:** PASS. `npm run dev`, then open `/?demo=1`.
- [ ] **Step 5: User checkpoint.** Take screenshots at 1920×1080 landscape and 1080×1920 portrait, in dark and light, at 1P and 2P. Show them to the user and **stop until they approve the look** or ask for changes. Record their decisions in the commit message.
- [ ] **Step 6:** Build, then commit `feat(web): second-monitor layout, theme, demo mode`.

### Task 10: Lane — layout, note model, PixiJS renderer (drawn shapes), latency overlay

**Files:**
- Create: `web/src/lib/lane/layout.ts`, `web/src/lib/lane/notes.ts`, `web/src/lib/lane/Lane.svelte`
- Modify: `web/src/display/Display.svelte`
- Test: `web/src/lib/lane/layout.test.ts`, `web/src/lib/lane/notes.test.ts`

**Interfaces:**
- Consumes: `subscribeKeys`, `settings`, the `onReset` path (T8), and `startDemo` / `devKeyboard` (T9).
- Produces:
  - `laneLayout(side: "1P" | "2P", width: number, height: number) -> { lanes: { lane: Lane; x: number; w: number; color: "white" | "black" | "scratch" }[]; judgeY: number }`.
    - Order is `S,1..7` for 1P and `1..7,S` for 2P.
    - Widths follow the skin (spec §5.9), scaled by `width / 576`: scratch 120, white 68, black 52, with a 4 px gap between lanes. Keys 1/3/5/7 are white and 2/4/6 are black.
    - The first lane starts at x 0 and the last ends at `width`. `judgeY = height * 0.88`.
  - `class NoteField(opts: { riseMs: number = 900; fadeFrom: number = 0.7; maxNotes: number = 256 })`, with:
    - `press(lane, t)`
    - `release(lane, t)`
    - `releaseAll(t)`
    - `frame(t) -> { lane; top: number; bottom: number; alpha: number }[]`, positions as fractions of the travel (0 = judge line, 1 = top of the lane)
    - `flashes(t) -> { lane; alpha }[]` (a 120 ms press flash)
  - While a key is held, the note's bottom stays at 0 and its top rises, so the note grows with the hold. On release the whole note rises at a speed of `1/riseMs`, and alpha fades linearly from `fadeFrom` of the travel to the top. Notes past 1 are removed. Past `maxNotes`, the oldest is dropped. A hold is capped at a length of 1.
  - Lane.svelte: one PixiJS `Application`. Graphics objects are reused from a pool, nothing is allocated per frame. It redraws on `requestAnimationFrame`, re-lays out on resize, and calls `releaseAll` on reset. With `prefers-reduced-motion: reduce`, notes don't rise: show only the flashes and a held-key highlight.
  - `?debug=1` overlay: the rolling mean and p95 of `(performance.timeOrigin + performance.now()) - event.at` over the last 50 key events, in ms.

- [ ] **Step 1: Write the failing tests**

```ts
test("1P puts scratch left, 2P right, skin proportions", () => {
  const l1 = laneLayout("1P", 576, 1000), l2 = laneLayout("2P", 576, 1000);
  expect(l1.lanes[0].lane).toBe("S"); expect(l2.lanes.at(-1)!.lane).toBe("S");
  const last = l1.lanes.at(-1)!; expect(l1.lanes[0].x).toBe(0); expect(last.x + last.w).toBeCloseTo(576);
  expect(l1.lanes[0].w).toBeCloseTo(120); expect(l1.lanes[1].x).toBeCloseTo(124);
  expect(l1.lanes.find(l => l.lane === "2")!.color).toBe("black");
  expect(laneLayout("1P", 288, 500).lanes[0].w).toBeCloseTo(60);
});

test("tap note rises and fades out", () => {
  const f = new NoteField({ riseMs: 1000 });
  f.press("1", 0); f.release("1", 50);
  const n = f.frame(550)[0]; expect(n.bottom).toBeCloseTo(0.5); expect(n.alpha).toBe(1);
  expect(f.frame(900)[0].alpha).toBeLessThan(1); expect(f.frame(2100)).toEqual([]);
});

test("held note grows from the judge line", () => {
  const f = new NoteField({ riseMs: 1000 }); f.press("S", 0);
  const n = f.frame(300)[0]; expect(n.bottom).toBe(0); expect(n.top).toBeCloseTo(0.3);
});

test("rapid presses each spawn a note", () => {
  const f = new NoteField();
  for (let i = 0; i < 30; i++) { f.press("4", i * 40); f.release("4", i * 40 + 10); }
  expect(f.frame(30 * 40).filter(n => n.lane === "4").length).toBeGreaterThanOrEqual(25);
});

test("releaseAll on reset ends held notes", () => { /* press 2 lanes, releaseAll(100), frame(100) has no note with bottom 0 and growing */ });
```

- [ ] **Step 2:** FAIL. **Step 3:** Implement layout and notes, then Lane.svelte. **Step 4:** PASS.
- [ ] **Step 5:** `/?demo=1&debug=1` looks right. With the server and controller running, presses show instantly, and the overlay mean is under 30 ms on the Mac.
- [ ] **Step 6:** Build, then commit `feat(web): pixi lane with floating notes and latency overlay`.

### Task 11: Skinned lane (WMII_FHD sprites)

**Files:**
- Create: `web/src/lib/lane/skin.ts`
- Modify: `web/src/lib/lane/Lane.svelte`
- Test: `web/src/lib/lane/skin.test.ts`

**Interfaces:**
- Consumes: `laneLayout`, `NoteField` and Lane.svelte (T10); `settings` (T8); `GET /api/skin` and `/skin/...` (T4).
- Produces:
  - `skinUrls(s: Settings, side: "1P" | "2P") -> { notes: string; beam: string; flash: string; lane: string; frame: string; turntable: string }`. Each URL is `/skin/play/parts/<folder>/<stem>.png`, using the spec §5.9 folders and the `skin_*` setting stems.
  - `SPRITES`: a constant with the §5.9 boxes, `{ note: { s: [94,0,90,19], w: [187,0,52,19], b: [241,0,40,19] }, beam: { b: [0,0,40,723], w: [42,0,52,723], s: [96,0,90,723] }, flash: { w: [0,0,63,92], b: [70,0,46,78] }, lane: { "1P": [0,0,432,6], "2P": [434,0,432,6] }, frame: { "1P": [0,0,685,1080], "2P": [717,0,685,1080] }, turntable: { label: [0,0,49,49] } }`.
  - `FRAME_LANE_BOX = { x: 75, y: 287, w: 576 }`: where the 576-wide lane sits inside the 685×1080 frame (for 1P; mirror x for 2P).
  - `loadSkin(urls) -> Promise<{ textures: SkinTextures | null; missing: string[] }>`. It loads with PixiJS `Assets`, cuts sub-textures with `new Texture({ source, frame: new Rectangle(...) })`, and returns `textures: null` if any required file fails (notes, beam, frame).
  - `spriteKind(lane: Lane) -> "s" | "w" | "b"`.
- Rendering: when textures exist, draw the frame scaled to the lane container (685:1080), and place the lanes inside `FRAME_LANE_BOX` scaled to match. Each note is the note sprite for its lane kind, stretched vertically for held notes. The key beam shows on press (alpha 1 → 0 over 200 ms), and the key flash sits at the judge line. The turntable label rotates with scratch: +1 turn per second while `S` is held up, −1 while held down. When textures are null, keep the drawn shapes from T10 and show a small "skin not found: <missing>" note in the settings page, never on the display.

- [ ] **Step 1: Write the failing tests**

```ts
test("skin urls follow settings", () => {
  const u = skinUrls({ ...DEFAULTS, skin_notes: "pastel", skin_frame: "fancy_purple" }, "1P");
  expect(u.notes).toBe("/skin/play/parts/notes/pastel.png");
  expect(u.frame).toBe("/skin/play/parts/frame/Wide/fancy_purple.png");
});
test("sprite kind per lane", () => {
  expect(["S", "1", "2", "7"].map(l => spriteKind(l as Lane))).toEqual(["s", "w", "b", "w"]);
});
test("missing sprite falls back", async () => {
  // Stub the loader so the frame URL rejects -> textures null, missing lists the frame URL
});
```

- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS.
- [ ] **Step 5:** `/?demo=1` with `skins/WMII_FHD` present. Expected: the frame, notes, beams and flashes come from the skin. In 2P the frame and lanes mirror. Rename the skin folder temporarily, and the lane falls back to drawn shapes.
- [ ] **Step 6:** Build, then commit `feat(web): skinned lane from local WMII_FHD sprites`. Check `git status` shows no `skins/` files staged.

### Task 12: Button counter

**Files:**
- Create: `web/src/lib/counter/counts.ts`, `web/src/lib/counter/Counter.svelte`
- Modify: `web/src/display/Display.svelte`, `web/src/lib/stores.ts` (apply key events to `counts`)
- Test: `web/src/lib/counter/counts.test.ts`

**Interfaces:**
- Consumes: the `counts` store, `subscribeKeys`, `subscribeReset` and `ws.send` (T8); the `counts_reset` message and `counts` event (T7).
- Produces:
  - `emptyCounts() -> Counts`
  - `applyKey(c: Counts, e: KeyEvent) -> Counts` returns a new object, +1 on `key_down` only. Lane `S` counts toward `S_up` or `S_down` by `dir`.
  - `counterTarget(e: KeyEvent) -> keyof Counts`
- Counter.svelte, like the user's screenshot:
  - Boxes 2, 4 and 6 in the top row, offset half a box right. Boxes 1, 3, 5 and 7 in the bottom row.
  - A round turntable on the scratch side (left for 1P, right for 2P) showing the `S_up` count above and the `S_down` count below.
  - A box's border uses `--counter-held` (yellow) while its key or scratch direction is held, and `--counter-idle` (green) otherwise.
  - A small "Reset" button sends `{"type":"counts_reset"}`.
  - Numbers use tabular figures, so they don't shift as they grow.
  - The page adds key events locally with `applyKey`. The server's numbers win whenever `hello` or `counts` arrives.

- [ ] **Step 1: Write the failing tests**

```ts
test("key downs count, ups don't, scratch split by direction", () => {
  let c = emptyCounts();
  for (const e of [down("1"), up("1"), down("1"), down("S", "up"), down("S", "down"), up("S", "down")]) c = applyKey(c, e);
  expect(c).toMatchObject({ "1": 2, S_up: 1, S_down: 1, "2": 0 });
});
test("hello replaces local counts", () => {
  // Store: apply 3 key downs for "5", then a hello event with counts all 0 -> counts store is all 0
});
```

- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS.
- [ ] **Step 5:** With the server and controller running: press keys and spin both ways, and the counts match. Reload the page and the counts stay. Click Reset and the counts go to 0 in every open tab. Restart the app and the counts are 0.
- [ ] **Step 6:** Build, then commit `feat(web): button counter with reset`.

### Task 13: Settings page and bindings flow

**Files:**
- Create: `web/src/settings/Settings.svelte`, `web/src/settings/Bindings.svelte`
- Modify: `web/src/App.svelte`

**Interfaces:**
- Consumes: `settings`, `patchSettings`, `devices`, `bindings`, `bindProgress` and `ws.send` (T8). The server events `bind_step`, `bind_done` and `bind_cancelled` (T7).
- Settings fields:
  - side (1P/2P)
  - manual BPM (number, used until recognition supplies the chart BPM)
  - beats per GIF loop
  - theme
  - orientation
  - a GIF upload (file input → `PUT /api/gif` with the raw file body; a 4xx shows the server's error)
  - skin: a folder path text field (`skin_dir`), and a dropdown for each style (`skin_notes`, `skin_frame`, `skin_beam`, `skin_flash`, `skin_lane`, `skin_turntable`), filled from `GET /api/skin`. If `available` is false, show "No skin found in <skin_dir>. The lane uses plain shapes." plus the `missing` list from `loadSkin` (T11).
  - The page shows server-side validation errors next to the field.
- Bindings:
  - A list of devices with a bound/unbound badge.
  - A "Bind controller" button sends `bind_start` and shows a large prompt such as "Press key 3" or "Spin turntable clockwise (scratch up)". The prompt follows `bind_step` and includes a mini lane with the target highlighted. "Cancel" sends `bind_cancel`.
  - After `bind_done`, a "Test" view shows the live lane, so the user can check every key and both scratch directions.
- These are mostly view components over tested logic, so verification is manual (next step).

- [ ] **Step 1:** Implement both components.
- [ ] **Step 2: Manual check on the Mac with the controller.** Bind from scratch, restart the app, and check the binding still works. Switch to 2P and check the lane mirrors on the display page in real time. Enter BPM 0 and check the error shows and the value isn't saved.
- [ ] **Step 3:** Build, then commit `feat(web): settings and controller binding flow`.

### Task 14: BPM-synced GIF player

**Files:**
- Create: `web/src/lib/gif/rate.ts`, `web/src/lib/gif/GifPlayer.svelte`
- Modify: `web/src/display/Display.svelte`, `web/package.json` (add `gifuct-js`)
- Test: `web/src/lib/gif/rate.test.ts`

**Interfaces:**
- Consumes: the stores `settings` (`manual_bpm`, `beats_per_loop`), `hasGif` and `gifVersion` (T8). Later plans add a `chart` store with `bpm_max`. The player takes `bpm` as a prop so the source can change.
- Produces:
  - `normaliseDelays(delaysMs: number[]) -> number[]`. Any delay ≤ 10 ms becomes 100 ms, matching browsers.
  - `loopRate(bpm: number, beatsPerLoop: number, gifDurationMs: number) -> number`. It returns the playback-speed multiplier `gifDurationMs / (beatsPerLoop * 60000 / bpm)`.
  - `frameAt(elapsedMs: number, delaysMs: number[], rate: number) -> number` (frame index, looping).
  - GifPlayer: fetch `/api/gif?v=${gifVersion}`, decode with gifuct-js (`parseGIF` + `decompressFrames(gif, true)`), and composite the frames onto offscreen canvases once (respecting the disposal type). Then draw the frame at `frameAt(now - start, delays, rate)` on rAF.
    - When the rate changes, keep the loop phase so the speed changes without a jump: recompute `start` from the current phase.
    - With no GIF, show an "Upload a GIF in settings" placeholder.
    - With reduced motion, show the first frame only.

- [ ] **Step 1: Write the failing tests**

```ts
test("loop lasts beatsPerLoop beats", () => {
  expect(loopRate(120, 4, 2000)).toBeCloseTo(1);    // 4 beats at 120 bpm = 2000 ms
  expect(loopRate(240, 4, 2000)).toBeCloseTo(2);
  expect(loopRate(150, 2, 1000)).toBeCloseTo(1.25);
});
test("zero delays treated as 100 ms", () => {
  expect(normaliseDelays([0, 10, 20])).toEqual([100, 100, 20]);
  expect(Number.isFinite(loopRate(150, 4, normaliseDelays([0, 0]).reduce((a, b) => a + b)))).toBe(true);
});
test("frameAt loops and scales", () => {
  expect(frameAt(0, [100, 100], 1)).toBe(0); expect(frameAt(150, [100, 100], 1)).toBe(1);
  expect(frameAt(250, [100, 100], 1)).toBe(0); expect(frameAt(75, [100, 100], 2)).toBe(1);
});
```

- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS.
- [ ] **Step 5:** Manual check: upload a GIF, set 4 beats/loop and BPM 120, and confirm a 4-beat loop by eye against a metronome. Change the BPM and check the speed changes smoothly.
- [ ] **Step 6:** Build, then commit `feat(web): bpm-synced gif player`.

### Task 15: Windows run and real-controller check (user runs it)

**Files:**
- Create: `docs/windows-setup.md` (the steps below, with D: as the example drive)

- [ ] **Step 1:** Write `docs/windows-setup.md` with these PowerShell steps. Everything goes on D: (or any non-C: drive):

```powershell
# One-time: install uv to D:
powershell -ExecutionPolicy ByPass -c {$env:UV_INSTALL_DIR = "D:\tools\uv"; irm https://astral.sh/uv/install.ps1 | iex}
# One-time: keep uv's Python, caches and tool shims off C: (new terminals pick these up)
setx UV_PYTHON_INSTALL_DIR D:\tools\uv\python
setx UV_CACHE_DIR D:\tools\uv\cache
setx UV_PYTHON_BIN_DIR D:\tools\uv\bin
setx UV_TOOL_DIR D:\tools\uv\tools
# Open a NEW PowerShell window, then:
cd D:\code
git clone <repo-url> inf-companion   # Git for Windows: choose a D: install folder, or use PortableGit on D:
cd inf-companion
uv run inf-companion                 # .venv and data\ are created inside D:\code\inf-companion
```

  Skins aren't in git, so copy your `WMII_FHD` folder to `D:\code\inf-companion\skins\WMII_FHD` (or set the skin folder in settings to wherever it is).

  Then: open `http://127.0.0.1:8765/` on the second monitor, and `#/settings` to bind. Updating later is `git pull && uv run inf-companion`. Check afterwards: `uv cache dir` and `uv python dir` both print D: paths.
- [ ] **Step 2:** Commit `docs: windows setup off C:`. Ask the user to run it with INFINITAS open, playing a song with the page on the second monitor and `?debug=1`. Ask them to report:
  1. whether every press shows (try a trill and a scratch-heavy song)
  2. the overlay mean and p95 latency
  3. whether input still registers while INFINITAS has focus (background events)
  4. any feel of stutter in the game
- [ ] **Step 3:** Fix what they report through `superpowers:systematic-debugging`, before starting Plan 2.

---

## Revision 2 (user, 2026-11-23, after reviewing Tasks 1–12)

The user approved the lane's feel but changed three things (spec §5.8, §5.9):
1. Only the skin's **notes** are used. The frame, lane strip, beams, flashes and turntable are drawn.
2. The layout is a **3×4 grid**: the lane spans rows 1–3 of column 1. Now playing (row 1) and Personal best (row 2) span columns 2–3. Row 3 has the counter in column 2 and a square GIF in column 3. Recent plays spans row 4. Portrait is dropped.
3. New panels: **Personal best** and **Recent plays**. They get their layout and empty states now. Plan 3 feeds them data.

**Order from here:** Task 16, then Task 17, then the user design check, then Tasks 13, 14 and 15 as amended below.

**Amendments to Tasks 13–14:**
- **Task 13:** settings show the skin folder and the note style only. `orientation` is gone.
- **Task 14:** the GIF player goes in the grid's GIF cell, as a square sized to the counter row's height.

### Task 16: Drawn IIDX lane, skin notes only

**Files:**
- Modify: `inf_companion/settings.py`, `inf_companion/server/skin.py`, `web/src/lib/events.ts`, `web/src/lib/lane/skin.ts`, `web/src/lib/lane/Lane.svelte`
- Test: `tests/test_storage.py`, `tests/test_skin.py`, `web/src/lib/lane/skin.test.ts`

**Interfaces:**
- **Settings:** remove `orientation`, `skin_frame`, `skin_beam`, `skin_flash`, `skin_lane` and `skin_turntable` from `DEFAULT_SETTINGS`, the validator and the TS `Settings` / `DEFAULTS`. Keep `skin_dir` and `skin_notes`. Keys still stored from an older version are ignored by `get_all()`, which already filters to known keys.
- `list_skin(skin_dir) -> {"available": bool, "notes": [str]}`.
- **skin.ts:**
  - `SPRITES = { note: {...} }` only.
  - `skinUrls(s) -> { notes: string }` (still carrying `?dir=`).
  - `loadSkin(urls, deps?) -> { textures: { note: Record<SpriteKind, Texture> } | null; missing: string[] }`.
  - `frameGeometry` is removed.
- **Lane.svelte, drawn parts:**
  - Lanes fill the canvas width with `laneLayout` proportions. The background is `--lane-bg` with 1 px `--line` dividers. The judge line is a 4 px `--key-scratch` bar at `judgeY = 0.80 * height`.
  - Below the judge line:
    - **Key caps:** white keys full height, black keys starting 12% lower. They're lit (`--key-white` / `--key-black` at full alpha) while held and dimmed to 0.28 otherwise.
    - **Turntable disc:** a circle under the scratch lane, with a diameter of 0.9 × the scratch lane width, a `--line-strong` rim and one radial marker line. It rotates +1 turn/s while `S` is held up and −1 turn/s while held down.
  - **Beam on press:** a vertical gradient from `--accent` at 0.45 alpha at the judge line to transparent at 45% of the lane height. It's fully lit while held and fades out over 200 ms after release.
  - **Notes:** the skin sprite when loaded, otherwise a bar in the lane colour.

- [ ] **Step 1:** Update the tests first.
  - Python: `DEFAULT_SETTINGS` has no `orientation` or `skin_frame`. `list_skin` returns only `available` and `notes`. A stored legacy key `skin_frame` doesn't appear in `get_all()`.
  - TS: `skinUrls` returns only `notes`, and `loadSkin` with a failing notes URL returns `textures: null`.
  - Run them and watch them FAIL.
- [ ] **Step 2:** Implement. Run `uv run pytest -q` and `npx vitest run`, both PASS.
- [ ] **Step 3:** Check in the browser at `/?demo=1`: the drawn lane with skin notes, in 1P and 2P, plus the fallback with a missing skin.
- [ ] **Step 4:** Build, then commit `feat(web): drawn IIDX lane, skin notes only`.

### Task 17: Grid layout with now playing, personal best and recent plays

**Files:**
- Create: `web/src/lib/score.ts`, `web/src/lib/score.test.ts`, `web/src/display/NowPlaying.svelte`, `web/src/display/PersonalBest.svelte`, `web/src/display/RecentPlays.svelte`, `web/src/lib/demoPanels.ts`
- Modify: `web/src/lib/events.ts`, `web/src/lib/stores.ts`, `web/src/lib/theme.css`, `web/src/display/Display.svelte`

**Interfaces:**
- `events.ts` types, shared with Plan 3, which will send `chart`, `personal_best` and `recent_plays` events with these exact shapes:
  - `type Difficulty = "BEGINNER" | "NORMAL" | "HYPER" | "ANOTHER" | "LEGGENDARIA"`
  - `interface Chart { title: string; difficulty: Difficulty; level: number; bpm: number | null; notes: number | null }`
  - `interface PersonalBest { score: number; notes: number | null; lamp: string; miss_count: number | null; last_played: string | null; source: "official" | "local" }`
  - `interface RecentPlay { title: string; difficulty: Difficulty; level: number; score: number; notes: number | null; option: string | null; played_at: string }`
  - New `ServerEvent` members: `{ type: "chart"; chart: Chart | null }`, `{ type: "personal_best"; best: PersonalBest | null }` (null means not played yet) and `{ type: "recent_plays"; plays: RecentPlay[] }`. `applyEvent` stores them.
- Stores: `nowPlaying: Writable<Chart | null>`, `personalBest: Writable<PersonalBest | null>` and `recentPlays: Writable<RecentPlay[]>`.
- `score.ts`:
  - `DJ_LEVELS = ["F","E","D","C","B","A","AA","AAA"]`
  - `djLevel(score, notes) -> string` returns the highest level with `score >= ceil(notes*2*k/9)`, where k = 2..8 for E..AAA, and F otherwise.
  - `djBorder(score, notes) -> { level: string; diff: number; label: string }` finds the nearest line among E..AAA. On a tie it takes the line at or below the score. `label` is `level + ("+" | "−") + |diff|`. Without notes it returns null.
  - `DIFF_SHORT = { BEGINNER: "B", NORMAL: "N", HYPER: "H", ANOTHER: "A", LEGGENDARIA: "L" }`.
- Difficulty colour tokens in `theme.css`, for both themes: `--diff-beginner` (green), `--diff-normal` (blue), `--diff-hyper` (yellow), `--diff-another` (red), `--diff-leggendaria` (purple).
- **Display grid:**
  - `grid-template-columns: auto minmax(0,1fr) auto`. The lane column width comes from aspect-ratio 576:1000 against rows 1–3.
  - `grid-template-rows: auto auto minmax(0,1fr) minmax(0, 0.9fr)`.
  - Areas: `"lane now now" "lane pb pb" "lane counter gif" "recent recent recent"`. The 2P mirror is `"now now lane" "pb pb lane" "counter gif lane" "recent recent recent"`.
  - The GIF cell is square (`aspect-ratio: 1; height: 100%`).
- **Panels:**
  - **NowPlaying:** the difficulty tag and level in the difficulty colour, the title, and the BPM. With no chart it shows "No song selected" and the manual BPM marked "(manual)".
  - **PersonalBest:**
    - With a best: EX score, `djBorder` label, lamp, miss count and last played.
    - With a chart but no best: "Not played yet".
    - With no chart: "No song selected".
  - **RecentPlays:** a table with columns difficulty tag (coloured) | title (coloured) | EX score | `djBorder` label | option. Newest first, rows that don't fit are clipped, and the empty state is "No plays yet".
- `demoPanels()` fills the three stores with made-up sample data (invented titles) when `?demo=1`, for design review only.

- [ ] **Step 1: Write the failing tests** (`score.test.ts`). With `notes = 1000` (max 2000), the lines are E 445, D 667, C 889, B 1112, A 1334, AA 1556, AAA 1778.

```ts
test("dj level", () => {
  expect(djLevel(2000, 1000)).toBe("AAA"); expect(djLevel(1777, 1000)).toBe("AA");
  expect(djLevel(444, 1000)).toBe("F"); expect(djLevel(445, 1000)).toBe("E");
});
test("nearest border label", () => {
  expect(djBorder(1600, 1000)!.label).toBe("AA+44");
  expect(djBorder(1700, 1000)!.label).toBe("AAA−78");
  expect(djBorder(367, 1000)!.label).toBe("E−78");
  expect(djBorder(1556, 1000)!.label).toBe("AA+0");
  expect(djBorder(100, null)).toBeNull();
});
test("panel events land in stores", () => { /* applyEvent chart / personal_best / recent_plays -> stores */ });
```

- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS, and svelte-check is clean.
- [ ] **Step 5:** Check `/?demo=1` at 1920×1080 in 1P and 2P, dark and light. Then **stop for the user's design check.**
- [ ] **Step 6:** Build, then commit `feat(web): 3x4 grid with now playing, personal best, recent plays`.

## Revision 3 (user, 2026-11-23, after reviewing Tasks 16–17)

- **No skin at all.** The notes are drawn, so the skin settings (`skin_dir`, `skin_notes`), `/api/skin`, `/skin/...`, `server/skin.py` and `web/src/lib/lane/skin.ts` are removed. Settings are now `side`, `manual_bpm`, `beats_per_loop` and `theme`.
- **Task 13:** no skin fields on the settings page.
- **Review Focus #5** (skin path escape) no longer applies, since the route is gone. `test_skin_routes_are_gone` checks it stays gone.
- **Narrow windows (≤ 1440 px wide):** 5 rows, with the GIF row above the counter row, both spanning columns 2–3. The two rows share the height. The counter area is a CSS size container, and the counter's box size is `clamp(20px, min(9cqi, 27cqh), 92px)`.

## Revision 4 (user, 2026-11-23)

- **Row ratios beside the lane:** 2 : 3 : 2 (now playing, personal best, counter + GIF) in the 4-row layout, and 1 : 2 : 1 : 1 in the 5-row layout (user revised from 3:3:2 / 3:3:1:1). Recent plays stays a fixed six-row height.
- **Panels fill their rows.** The `now` and `pb` cells are CSS size containers, and panel text scales with `cqh` / `cqi`.
- **Artist:** `Chart` gains `artist: string | null`. Now playing shows it under the title. Plan 3's `chart` event must include it.

## Revision 5 (user, 2026-11-23)

- **One layout at every size.** The 5-row breakpoint is removed. Areas are `"lane now now" "lane gif pb" "lane counter counter" "recent recent recent"`, with columns `auto 3fr 5fr` (user revised from 1:3, then 2:5) and rows `2fr 3fr 2fr auto`. The 2P mirror is `"now now lane" "gif pb lane" "counter counter lane"`.
- **Personal best stack:** a muted "Personal best" header, clear type (small), DJ grade from `djLevel` (large), EX score (medium) with the `djBorder` label beside it (small), then misses (small), and last played (small) pinned to the bottom right.
- **Task 14:** the GIF fills the `gif` cell and is fitted inside it (contain), so it's not always square.

## Roadmap: Plans 2 and 3 (written after this plan ships)

Each gets its own writing-plans pass, because each depends on results that don't exist yet: spike numbers and fixture screenshots.

**Plan 2 — Capture and tables**
1. `tools/capture_spike.py` (throwaway, spec §7). It reuses `docs/windows-setup.md` for the off-C: environment, and is run with `uv run --with dxcam --with pywin32 python tools/capture_spike.py`. It saves sample frames, which become `tests/fixtures/`.
2. `tools/convert_tables.py`. Findings from 2026-11-23 (pinned inf-notebook commit `f43158edfb65006c976ed7785cfa7b066c3ffcf4`):
   - `musictable1.2.res` has **no BPM**. It has no numbers at all, only versions, titles and level strings. BPM must come from the song-select screen (a locally learned digit table) or manual entry (spec §5.3 fallback). The manual BPM setting from this plan stays as the last resort.
   - `musictable`, `notesradar` and `deeper` contain **no global references**.
   - `screenrecognition`, `musicselect`, `informations`, `details`, `resultothers` and `resultrecognition` **do** reference globals. The full set is `builtins.slice`, `numpy.dtype`, `numpy._core.multiarray.scalar`, `numpy._core.numeric._frombuffer`, `numpy._core.multiarray._reconstruct` and `numpy.ndarray`. A `find_class` that always raises can't read them.
   - **Needs the user's decision before Plan 2:** proposed allowlist that maps exactly those six names to our own inert stand-ins (plain functions and classes that turn the data into ints, lists and `[start, stop]` pairs). The real numpy or builtins are never imported from the pickle. Everything else raises. This changes the CLAUDE.md hard rule "no globals allowed".
3. Capture interface + `replay` backend + screen classification, tested against the spike's fixtures.

**Plan 3 — Recognition, records and the rest of the page**
Capture process with adaptive rate; the `dxcam`/`window` backends the spike picks; state machine; song-select reading (title, difficulty, level, BPM digits); result reading; `charts`/`plays` storage with difference vs best; unknown-title fingerprints + naming UI; now-playing/result/history cards with the score graph; official CSV import; table update check; PyInstaller release workflow. Keyboard players (global key reading on Windows) is open. It's only needed if the user plays on keyboard.
