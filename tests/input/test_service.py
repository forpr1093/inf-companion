import pytest

from inf_companion.input.model import Binding, RawEvent, Source, TARGETS
from inf_companion.input.service import InputService
from inf_companion.storage.db import BindingsRepo, open_db


class RecordingBus:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


class FakeSource:
    def __init__(self, on_raw, on_devices, on_idle):
        self.started = self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def g1_binding():
    m = {str(i): Source("button", i - 1) for i in range(1, 8)}
    m |= {"S_up": Source("axis", 0, sign=1), "S_down": Source("axis", 0, sign=-1)}
    return Binding("g1", "Pad", m)


@pytest.fixture
def repo(tmp_path):
    r = BindingsRepo(open_db(tmp_path / "c.sqlite3"))
    r.put(g1_binding())
    return r


@pytest.fixture
def bus():
    return RecordingBus()


@pytest.fixture
def svc(bus, repo):
    s = InputService(bus, repo, source_factory=FakeSource)
    s.start()
    return s


def events(bus, type=None):
    return [e for e in bus.events if type is None or e["type"] == type]


def test_start_stop_drive_source(svc):
    assert svc._source.started
    svc.stop()
    assert svc._source.stopped


def test_raw_button_publishes_key_down(svc, bus):
    svc.handle_devices([("g1", "Pad")])
    svc.handle_raw(RawEvent("g1", "button", 0, 1, 3.0))
    assert {"type": "key_down", "lane": "1", "dir": None, "t": 3.0}.items() <= events(bus)[-1].items()


def test_devices_event_marks_bound(svc, bus):
    svc.handle_devices([("g1", "Pad"), ("g2", "Keyboard thing")])
    ev = events(bus, "devices")[-1]
    assert ev["devices"] == [{"guid": "g1", "name": "Pad", "bound": True}, {"guid": "g2", "name": "Keyboard thing", "bound": False}]
    assert [d.guid for d in svc.devices()] == ["g1", "g2"]


def test_bind_flow_saves_and_stops_key_events(svc, bus, repo):
    svc.handle_devices([("g2", "New pad")])
    svc.handle_client({"type": "bind_start"})
    assert events(bus, "bind_step")[-1]["target"] == "1"
    for i in range(7):
        svc.handle_raw(RawEvent("g2", "button", i, 1, 0.0))
    svc.handle_raw(RawEvent("g2", "axis", 1, 0, 0.0))
    svc.handle_raw(RawEvent("g2", "axis", 1, 6000, 1.0))
    svc.handle_raw(RawEvent("g2", "axis", 1, -6000, 2.0))
    assert events(bus, "key_down") == []
    done = events(bus, "bind_done")[-1]
    assert done["binding"]["device_guid"] == "g2" and done["binding"]["name"] == "New pad"
    assert repo.get("g2").map["S_down"] == Source("axis", 1, sign=-1)
    assert events(bus, "devices")[-1]["devices"][0]["bound"] is True
    steps = events(bus, "bind_step")
    assert [s["target"] for s in steps] == list(TARGETS) and steps[0]["total"] == 9
    svc.handle_raw(RawEvent("g2", "button", 2, 1, 5.0))
    assert events(bus, "key_down")[-1]["lane"] == "3"


def test_bind_cancel(svc, bus):
    svc.handle_client({"type": "bind_start"})
    svc.handle_client({"type": "bind_cancel"})
    assert events(bus)[-1]["type"] == "bind_cancelled"
    svc.handle_raw(RawEvent("g1", "button", 0, 1, 1.0))
    assert events(bus, "key_down")


def test_device_removed_releases_held_keys(svc, bus):
    svc.handle_devices([("g1", "Pad")])
    svc.handle_raw(RawEvent("g1", "button", 0, 1, 1.0))
    svc.handle_devices([])
    assert any(e["type"] == "key_up" and e["lane"] == "1" for e in events(bus))


def test_idle_tick_releases_scratch(svc, bus):
    svc.handle_raw(RawEvent("g1", "axis", 0, 0, 0.0))
    svc.handle_raw(RawEvent("g1", "axis", 0, 512, 5.0))
    svc.handle_idle(200.0)
    up = events(bus, "key_up")[-1]
    assert up["lane"] == "S" and up["dir"] == "up"


def test_counts_reset_publishes_zeros(svc, bus):
    svc.handle_raw(RawEvent("g1", "button", 0, 1, 1.0))
    assert svc.counts()["1"] == 1
    svc.handle_client({"type": "counts_reset"})
    assert events(bus, "counts")[-1]["counts"] == {t: 0 for t in TARGETS}
    assert svc.counts()["1"] == 0


def test_unknown_client_message_ignored(svc, bus):
    svc.handle_client({"type": "nope"})
    svc.handle_client({})
    assert events(bus) == []


def test_binding_cancelled_when_its_page_goes_away(svc, bus):
    svc.handle_client({"type": "bind_start"}, client="a")
    svc.client_gone("b")                       # another page closing changes nothing
    svc.handle_raw(RawEvent("g1", "button", 0, 1, 1.0))
    assert events(bus, "key_down") == []       # still binding
    svc.client_gone("a")
    assert events(bus)[-1]["type"] == "bind_cancelled"
    svc.handle_raw(RawEvent("g1", "button", 1, 1, 2.0))
    assert events(bus, "key_down")[-1]["lane"] == "2"


def test_binding_state_is_reported_for_hello(svc):
    assert svc.binding_state() is None
    svc.handle_client({"type": "bind_start"}, client="a")
    assert svc.binding_state() == {"target": "1", "index": 0, "total": 9}
