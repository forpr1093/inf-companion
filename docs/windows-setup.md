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
   git clone <repo-url> inf-companion
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

## Update

```powershell
cd D:\code\inf-companion
git pull
uv run inf-companion
```

The built web page is part of the repository, so Windows never needs Node.

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
