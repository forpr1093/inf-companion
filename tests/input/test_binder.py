from inf_companion.input.binder import BindingSession
from inf_companion.input.model import RawEvent, Source


def test_full_session_with_axis_scratch():
    s = BindingSession({"g1": "Pad"})
    for i in range(7):
        assert s.current_target == str(i + 1) and s.index == i
        assert s.feed(RawEvent("g1", "button", i, 1, 0.0)) is None
    s.feed(RawEvent("g1", "axis", 0, 0, 0.0))
    s.feed(RawEvent("g1", "axis", 0, 5000, 1.0))
    assert s.current_target == "S_down"
    s.feed(RawEvent("g1", "axis", 0, 9000, 2.0))  # same direction again: skipped
    assert s.current_target == "S_down"
    b = s.feed(RawEvent("g1", "axis", 0, 0, 3.0))  # -9000: opposite direction
    assert b.map["S_up"] == Source("axis", 0, sign=1) and b.map["S_down"] == Source("axis", 0, sign=-1)
    assert b.device_guid == "g1" and b.name == "Pad"
    assert s.current_target is None


def test_other_device_ignored_after_first():
    s = BindingSession({"g1": "Pad", "g2": "Other"})
    s.feed(RawEvent("g1", "button", 0, 1, 0.0))
    s.feed(RawEvent("g2", "button", 5, 1, 0.0))
    assert s.current_target == "2"


def test_button_release_and_duplicate_button_ignored():
    s = BindingSession({"g1": "Pad"})
    s.feed(RawEvent("g1", "button", 3, 1, 0.0))
    s.feed(RawEvent("g1", "button", 3, 0, 0.0))
    s.feed(RawEvent("g1", "button", 3, 1, 0.0))
    assert s.current_target == "2"


def test_hat_assigns_mask():
    s = BindingSession({"g1": "Pad"})
    s.feed(RawEvent("g1", "hat", 0, 4, 0.0))
    s.feed(RawEvent("g1", "hat", 0, 0, 0.0))
    assert s.current_target == "2"
    for i in range(6):
        s.feed(RawEvent("g1", "button", i, 1, 0.0))
    s.feed(RawEvent("g1", "button", 10, 1, 0.0))
    b = s.feed(RawEvent("g1", "button", 11, 1, 0.0))
    assert b.map["1"] == Source("hat", 0, mask=4) and b.map["S_up"] == Source("button", 10)


def test_unknown_device_name_falls_back_to_guid():
    s = BindingSession({})
    for i in range(9):
        b = s.feed(RawEvent("gx", "button", i, 1, 0.0))
    assert b.name == "gx"
