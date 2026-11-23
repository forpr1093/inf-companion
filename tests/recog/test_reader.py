from inf_companion.recog.reader import Reader
from inf_companion.recog.result import ResultRead
from inf_companion.recog.select import SelectRead

NOTESRADAR = {"SP": {"musics": {"Mermaid girl": {"HYPER": {"notes": 856}}}}}


class Queue:
    """A stub reader that returns queued reads, one per call."""

    def __init__(self, *reads):
        self.reads = list(reads)

    def read(self, frame):
        return self.reads.pop(0)


def sel(title="Mermaid girl", difficulty="HYPER", playmode="SP", score=1437):
    return SelectRead(playmode, title, difficulty, 8, "HARD CLEAR", "AA", score, 8)


def res(score=1228, side="1P", playmode="SP"):
    return ResultRead(side=side, playmode=playmode, title="Mermaid girl", difficulty="HYPER", level=8,
                      cleartype="CLEAR", score=score, judges={"pgreat": 485})


def run(reader, screens):
    out = []
    for s in screens:
        out.extend(reader.on_frame(None, s))
    return out


def charts(msgs):
    return [m["chart"] for m in msgs if m["type"] == "chart"]


def test_chart_needs_two_equal_reads():
    r = Reader(Queue(sel("A"), sel("B"), sel("B")), None, NOTESRADAR, "1P")
    msgs = run(r, ["music_select"] * 3)
    assert [c["title"] for c in charts(msgs)] == ["B"]
    assert [m["type"] for m in msgs] == ["chart", "personal_best"]


def test_chart_not_repeated():
    r = Reader(Queue(*[sel()] * 4), None, NOTESRADAR, "1P")
    assert len(charts(run(r, ["music_select"] * 4))) == 1


def test_chart_and_best_shape():
    r = Reader(Queue(sel(), sel()), None, NOTESRADAR, "1P")
    msgs = run(r, ["music_select"] * 2)
    assert msgs[0] == {"type": "chart", "chart": {"title": "Mermaid girl", "artist": None, "difficulty": "HYPER",
                                                  "level": 8, "bpm": None, "notes": 856}}
    assert msgs[1] == {"type": "personal_best", "best": {"score": 1437, "notes": 856, "lamp": "HARD CLEAR",
                                                         "miss_count": 8, "last_played": None, "source": "official"}}


def test_no_score_means_no_best():
    r = Reader(Queue(sel(score=None), sel(score=None)), None, NOTESRADAR, "1P")
    assert run(r, ["music_select"] * 2)[1] == {"type": "personal_best", "best": None}


def test_dp_sends_nothing():
    r = Reader(Queue(*[sel(playmode="DP")] * 3), Queue(*[res(playmode="DP")] * 3), NOTESRADAR, "1P")
    assert run(r, ["music_select"] * 3 + ["result"] * 3) == []


def test_unknown_title_still_sent():
    r = Reader(Queue(sel(title=None), sel(title=None)), None, NOTESRADAR, "1P")
    chart = charts(run(r, ["music_select"] * 2))[0]
    assert chart["title"] is None and chart["notes"] is None and chart["difficulty"] == "HYPER"


def test_other_screens_reset_the_pair():
    r = Reader(Queue(sel("A"), sel("A")), None, NOTESRADAR, "1P")
    assert run(r, ["music_select", "play", "music_select"]) == []


def test_result_sent_once_when_complete():
    incomplete = ResultRead(title="Mermaid girl")
    # No read happens once the result is sent, so the 4th result frame consumes nothing.
    r = Reader(None, Queue(incomplete, res(), res(), res(1300), res(1300)), NOTESRADAR, "1P")
    msgs = run(r, ["result"] * 4 + ["play"] + ["result"] * 2)
    results = [m["result"] for m in msgs if m["type"] == "result"]
    assert [x["score"] for x in results] == [1228, 1300]
    assert results[0]["judges"] == {"pgreat": 485}


def test_notes_from_notesradar():
    r = Reader(Queue(sel(difficulty="ANOTHER"), sel(difficulty="ANOTHER")), None, NOTESRADAR, "1P")
    assert charts(run(r, ["music_select"] * 2))[0]["notes"] is None  # not in the table


def test_missing_readers_do_nothing():
    r = Reader(None, None, NOTESRADAR, "1P")
    assert run(r, ["music_select", "result"]) == []
