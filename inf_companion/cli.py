"""Command-line entry point: `inf-companion`."""

import argparse
import sys
from pathlib import Path

import inf_companion
from inf_companion.paths import resolve_data_dir


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="inf-companion", description="Companion app for IIDX INFINITAS")
    p.add_argument("--host", default="127.0.0.1", help="address to listen on (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=8765, help="port to listen on (default 8765)")
    p.add_argument("--data-dir", default=None, help="data folder (default: $INF_COMPANION_DATA or ./data)")
    p.add_argument("--no-input", action="store_true", help="don't read the controller (no SDL)")
    p.add_argument("--tables-dir", default="tables", help="converted recognition tables (default ./tables)")
    p.add_argument("--capture", choices=["auto", "off", "dxcam", "replay"], default="auto",
                   help="screen capture backend (default auto: dxcam on Windows, off elsewhere)")
    p.add_argument("--source", default=None, help="replay: folder of screenshots or one image")
    p.add_argument("--record", default=None, metavar="DIR",
                   help="save labelled screenshots to DIR/<screen>/ while capturing (for calibration)")
    p.add_argument("--replay-fps", type=float, default=None, help="replay: frames per second (default: adaptive)")
    args = p.parse_args(argv)
    if args.capture == "auto":
        args.capture = default_capture(sys.platform)
    if args.replay_fps is not None and args.replay_fps <= 0:
        p.error("--replay-fps must be greater than 0")
    return args


def default_capture(platform: str) -> str:
    return "dxcam" if platform == "win32" else "off"


def main(argv: list[str] | None = None) -> int:
    import uvicorn

    from inf_companion.events import EventBus
    from inf_companion.server.app import AppContext, create_app
    from inf_companion.storage.db import BindingsRepo, SettingsRepo, open_db

    args = parse_args(argv)
    data_dir = resolve_data_dir(args.data_dir)
    conn = open_db(data_dir / "companion.sqlite3")
    ctx = AppContext(
        bus=EventBus(),
        settings=SettingsRepo(conn),
        bindings=BindingsRepo(conn),
        data_dir=data_dir,
        static_dir=Path(inf_companion.__file__).parent / "web_dist",
    )
    service = None
    if not args.no_input:
        from inf_companion.input.service import InputService

        service = InputService(ctx.bus, ctx.bindings)
        ctx.input = service
        service.start()
    capture = None
    if args.capture != "off":
        from inf_companion.capture.process import start_capture

        if args.capture == "replay" and not args.source:
            print("--capture replay needs --source <folder of screenshots>")
            return 2
        capture = start_capture(args.capture, args.source, Path(args.tables_dir).resolve(),
                                ctx.settings.get_all()["side"], ctx.bus, fixed_fps=args.replay_fps,
                                record_dir=args.record)
        ctx.capture = capture
    print(f"inf-companion {inf_companion.__version__}: data in {data_dir}")
    print(f"open http://{args.host}:{args.port}/")
    try:
        uvicorn.run(create_app(ctx), host=args.host, port=args.port, log_level="warning")
    finally:
        if service is not None:
            service.stop()
        if capture is not None:
            capture.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
