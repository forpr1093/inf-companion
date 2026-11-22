from inf_companion.input.mapper import InputMapper
from inf_companion.input.model import Binding, KeyEvent, RawEvent, Source

G = "g1"


def binding(**extra):
    m = {str(i): Source("button", i - 1) for i in range(1, 8)}
    m |= {"S_up": Source("axis", 0, sign=1), "S_down": Source("axis", 0, sign=-1)}
    m |= extra
    return Binding(G, "Pad", m)


def test_button_press_and_release_map_to_lane():
    m = InputMapper({G: binding()})
    assert m.feed(RawEvent(G, "button", 2, 1, 10.0)) == [KeyEvent("3", True, 10.0)]
    assert m.feed(RawEvent(G, "button", 2, 0, 55.0)) == [KeyEvent("3", False, 55.0)]


def test_unbound_device_ignored():
    assert InputMapper({G: binding()}).feed(RawEvent("other", "button", 0, 1, 1.0)) == []


def test_unbound_button_ignored():
    assert InputMapper({G: binding()}).feed(RawEvent(G, "button", 12, 1, 1.0)) == []


def test_axis_motion_presses_then_idle_releases():
    m = InputMapper({G: binding()})
    assert m.feed(RawEvent(G, "axis", 0, 0, 0.0)) == []
    assert m.feed(RawEvent(G, "axis", 0, 512, 5.0)) == [KeyEvent("S", True, 5.0, "up")]
    assert m.feed(RawEvent(G, "axis", 0, 1024, 10.0)) == []
    assert m.tick(89.0) == []
    assert m.tick(90.0) == [KeyEvent("S", False, 90.0, "up")]
    assert m.tick(200.0) == []


def test_axis_reversal_releases_then_presses_other_direction():
    m = InputMapper({G: binding()})
    m.feed(RawEvent(G, "axis", 0, 0, 0.0))
    m.feed(RawEvent(G, "axis", 0, 512, 5.0))
    assert m.feed(RawEvent(G, "axis", 0, 0, 20.0)) == [KeyEvent("S", False, 20.0, "up"), KeyEvent("S", True, 20.0, "down")]


def test_axis_wraparound_continues_same_direction():
    m = InputMapper({G: binding()})
    m.feed(RawEvent(G, "axis", 0, 32512, 0.0))
    assert m.feed(RawEvent(G, "axis", 0, 32700, 5.0)) == [KeyEvent("S", True, 5.0, "up")]
    assert m.feed(RawEvent(G, "axis", 0, -32700, 10.0)) == []


def test_axis_wraparound_downward():
    m = InputMapper({G: binding()})
    m.feed(RawEvent(G, "axis", 0, -32600, 0.0))
    assert m.feed(RawEvent(G, "axis", 0, 32600, 5.0)) == [KeyEvent("S", True, 5.0, "down")]


def test_jitter_inside_deadband_ignored():
    m = InputMapper({G: binding()})
    m.feed(RawEvent(G, "axis", 0, 0, 0.0))
    assert m.feed(RawEvent(G, "axis", 0, 40, 1.0)) == []


def test_slow_spin_accumulates_past_deadband():
    m = InputMapper({G: binding()})
    m.feed(RawEvent(G, "axis", 0, 0, 0.0))
    assert m.feed(RawEvent(G, "axis", 0, 40, 1.0)) == []
    assert m.feed(RawEvent(G, "axis", 0, 80, 2.0)) == [KeyEvent("S", True, 2.0, "up")]


def test_button_style_scratch():
    m = InputMapper({G: binding(S_up=Source("button", 8), S_down=Source("button", 9))})
    assert m.feed(RawEvent(G, "button", 8, 1, 1.0)) == [KeyEvent("S", True, 1.0, "up")]
    assert m.feed(RawEvent(G, "button", 8, 0, 2.0)) == [KeyEvent("S", False, 2.0, "up")]


def test_hat_mask():
    m = InputMapper({G: binding(**{"7": Source("hat", 0, mask=4)})})
    assert m.feed(RawEvent(G, "hat", 0, 6, 1.0)) == [KeyEvent("7", True, 1.0)]
    assert m.feed(RawEvent(G, "hat", 0, 2, 2.0)) == [KeyEvent("7", False, 2.0)]


def test_no_duplicate_down():
    m = InputMapper({G: binding()})
    assert len(m.feed(RawEvent(G, "button", 0, 1, 1.0))) == 1
    assert m.feed(RawEvent(G, "button", 0, 1, 2.0)) == []
    assert len(m.feed(RawEvent(G, "button", 0, 0, 3.0))) == 1
    assert m.feed(RawEvent(G, "button", 0, 0, 4.0)) == []


def test_release_all_and_release_device():
    m = InputMapper({G: binding()})
    m.feed(RawEvent(G, "button", 0, 1, 1.0))
    m.feed(RawEvent(G, "axis", 0, 0, 1.0))
    m.feed(RawEvent(G, "axis", 0, 512, 2.0))
    ups = m.release_device(G, 5.0)
    assert sorted((e.lane, e.down, e.dir) for e in ups) == [("1", False, None), ("S", False, "up")]
    assert m.release_all(6.0) == []
    m.feed(RawEvent(G, "button", 1, 1, 7.0))
    assert m.release_all(8.0) == [KeyEvent("2", False, 8.0)]


def test_set_bindings_replaces_map():
    m = InputMapper({})
    assert m.feed(RawEvent(G, "button", 0, 1, 1.0)) == []
    m.set_bindings({G: binding()})
    assert m.feed(RawEvent(G, "button", 0, 1, 2.0)) == [KeyEvent("1", True, 2.0)]
