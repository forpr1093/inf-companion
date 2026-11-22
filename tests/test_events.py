import asyncio
import threading
import time

from inf_companion.events import EventBus, make_event


def test_make_event_adds_type_and_at():
    ev = make_event("key_down", lane="1")
    assert ev["type"] == "key_down" and ev["lane"] == "1" and isinstance(ev["at"], float)
    assert abs(ev["at"] - time.time() * 1000) < 1000


def test_publish_from_thread_reaches_subscriber():
    async def run():
        bus = EventBus()
        bus.bind_loop(asyncio.get_running_loop())
        sub = bus.subscribe()
        threading.Thread(target=bus.publish, args=(make_event("key_down", lane="1"),)).start()
        ev = await asyncio.wait_for(sub.__anext__(), 1)
        assert ev["type"] == "key_down" and ev["lane"] == "1" and isinstance(ev["at"], float)

    asyncio.run(run())


def test_publish_before_bind_is_dropped():
    EventBus().publish({"type": "x"})  # must not raise


def test_full_queue_drops_oldest_and_never_blocks():
    async def run():
        bus = EventBus()
        bus.bind_loop(asyncio.get_running_loop())
        sub = bus.subscribe(maxsize=3)
        t0 = time.perf_counter()
        for i in range(10):
            bus.publish({"type": "x", "i": i})
        assert time.perf_counter() - t0 < 0.05
        await asyncio.sleep(0.05)
        got = [(await sub.__anext__())["i"] for _ in range(3)]
        assert got == [7, 8, 9]

    asyncio.run(run())


def test_closed_subscription_stops_receiving():
    async def run():
        bus = EventBus()
        bus.bind_loop(asyncio.get_running_loop())
        sub = bus.subscribe()
        sub.close()
        bus.publish({"type": "x"})
        await asyncio.sleep(0.02)
        assert sub.pending() == 0

    asyncio.run(run())
