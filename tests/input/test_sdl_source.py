import time

from inf_companion.input.sdl_source import SdlInputThread


def test_sdl_thread_starts_reports_devices_and_stops():
    devices, idles = [], []
    t = SdlInputThread(on_raw=lambda e: None, on_devices=devices.append, on_idle=idles.append)
    t.start()
    assert t.ready.wait(5)
    assert t.error is None
    deadline = time.time() + 2
    while not (devices and idles) and time.time() < deadline:
        time.sleep(0.01)
    t.stop()
    assert devices and isinstance(devices[0], list)
    assert idles
    assert not t._thread.is_alive()
