"""One frame convention across the Workbench and Blender (Melee frame-data style).

Frame 1 is the first frame of the move (frame 0 is the entry pose). A hitbox the script opens at frame S and
clears at frame E (wait_until S ... clear on E) is ACTIVE on frames S..E-1: the UI says "active S-(E-1)" and the
hitbox is visible when the shown frame is any of those. The wire (list_hitboxes / edit_hitbox) keeps the stored
numbers (end_frame = E); Blender's Hitbox panel, strips and sweep show and edit the last active frame.
The Qt side converts the engine's own numbering (one ahead) in EngineLink; the fake engine here is the
script-numbered server Blender actually talks to.
"""
import api, client, hitviz_math
from fake_engine import FakeWorkbench


def make():
    fake = FakeWorkbench(); port = fake.start()
    s = api.WbSession(lambda: client.McpClient(port=port, timeout=2.0))
    s.connect(); s.refresh_rows()
    return fake, s


def visible_frames(s, last=12):
    out = []
    for f in range(1, last + 1):
        assert s.set_frame(f), s.last_error
        if s.info.get("hitboxes"):
            out.append(f)
    return out


def test_script_window_3_to_5_is_visible_on_ui_frames_3_and_4(monkeypatch):
    import fake_engine
    original = fake_engine._source_hitboxes

    def window_3_to_5():
        boxes = original()
        for record in boxes["jab"]:
            record["start_frame"], record["end_frame"] = 3, 5     # stored: opens on 3, cleared on 5
        return boxes

    monkeypatch.setattr(fake_engine, "_source_hitboxes", window_3_to_5)
    fake, s = make()
    try:
        s.load_row("jab"); s.refresh_hitboxes()
        box = s.hitboxes[0]
        assert (box["start_frame"], box["end_frame"]) == (3, 4)          # shown as "active 3-4"
        assert visible_frames(s) == [3, 4]
    finally:
        fake.stop()


def test_editing_the_last_active_frame_writes_the_clear_frame():
    fake, s = make()
    try:
        s.load_row("jab"); s.refresh_hitboxes()
        # UI: first active frame 3, last active frame 4  ->  stored window [3,5)
        assert s.edit_hitbox(ordinal=0, start_frame=3, end_frame=4), s.last_error
        assert fake._source["jab"][0]["start_frame"] == 3 and fake._source["jab"][0]["end_frame"] == 5
        assert (s.hitboxes[0]["start_frame"], s.hitboxes[0]["end_frame"]) == (3, 4)
    finally:
        fake.stop()


def test_stored_window_is_read_back_as_last_active_frame():
    fake, s = make()
    try:
        s.load_row("jab"); s.refresh_hitboxes()
        # the fixture's stored window is [5,8): active 5-7
        assert (s.hitboxes[0]["start_frame"], s.hitboxes[0]["end_frame"]) == (5, 7)
        assert visible_frames(s) == [5, 6, 7]
    finally:
        fake.stop()


def test_a_never_cleared_hitbox_runs_to_the_playback_cap():
    boxes = api.WbSession.source_boxes([{"start_frame": 4, "end_frame": -1}])
    assert boxes[0]["end_frame"] == api.OPEN_END_FRAME


def test_sweep_join_uses_the_same_active_range():
    box = {"slot": 0, "start_frame": 3, "end_frame": 4, "ordinal": 0}
    assert hitviz_math.match_source([box], 0, 3) is box
    assert hitviz_math.match_source([box], 0, 4) is box
    assert hitviz_math.match_source([box], 0, 5) is None
