from inf_companion.input.counter import PressCounter
from inf_companion.input.model import TARGETS, KeyEvent


def test_counts_follow_key_downs_only():
    c = PressCounter()
    for t in range(25):
        c.add(KeyEvent("4", True, t))
        c.add(KeyEvent("4", False, t + 0.5))
    c.add(KeyEvent("S", True, 30, "up"))
    c.add(KeyEvent("S", True, 31, "down"))
    c.add(KeyEvent("S", False, 32, "down"))
    s = c.snapshot()
    assert s["4"] == 25 and s["S_up"] == 1 and s["S_down"] == 1 and s["1"] == 0 and set(s) == set(TARGETS)


def test_reset_zeroes_all():
    c = PressCounter()
    c.add(KeyEvent("1", True, 0))
    c.reset()
    assert c.snapshot() == {t: 0 for t in TARGETS}


def test_snapshot_is_a_copy():
    c = PressCounter()
    s = c.snapshot()
    s["1"] = 99
    assert c.snapshot()["1"] == 0
