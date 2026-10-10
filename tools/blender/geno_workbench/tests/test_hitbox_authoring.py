"""Add/delete hitbox and the role dropdown's data, against the fake engine."""
import api, client, props
from fake_engine import FakeWorkbench


def make():
    fake = FakeWorkbench(); port = fake.start()
    s = api.WbSession(lambda: client.McpClient(port=port, timeout=2.0))
    s.connect(); s.refresh_rows()
    return fake, s


def test_connect_loads_the_projects_roles():
    fake, s = make()
    try:
        names = [r["name"] for r in s.roles]
        assert "HAND_R" in names and "CHEST" in names
        assert all("group" in r for r in s.roles)
    finally:
        fake.stop()


def test_older_server_without_the_roles_command_leaves_the_list_empty():
    fake = FakeWorkbench(); fake.no_role_list = True; port = fake.start()
    try:
        s = api.WbSession(lambda: client.McpClient(port=port, timeout=2.0))
        assert s.connect(), s.last_error
        assert s.roles == [] and s.connected
    finally:
        fake.stop()


def test_add_hitbox_then_delete_marks_stale_and_refreshes_the_list():
    fake, s = make()
    try:
        s.load_row("jab"); s.refresh_hitboxes()
        before = len(s.hitboxes)
        assert s.add_hitbox(frame=3, bone="HAND_R"), s.last_error
        assert s.stale and fake.stale
        assert len(s.hitboxes) == before + 1
        assert s.last_added == 0                      # frame 3 sorts before the existing frame-5 box
        assert s.hitboxes[0]["start_frame"] == 3 and s.hitboxes[0]["joint"] == "HAND_R"
        assert ("add_hitbox", {"row": "jab", "frame": 3, "bone": "HAND_R"}) in fake.calls
        assert s.delete_hitbox(0), s.last_error
        assert len(s.hitboxes) == before and s.last_added is None
        assert s.rebuild_reload() and not s.stale
    finally:
        fake.stop()


def test_add_hitbox_defaults_to_the_shown_frame_and_lets_the_server_pick_the_bone():
    fake, s = make()
    try:
        s.load_row("jab"); s.refresh_hitboxes()
        s.set_frame(9)
        assert s.add_hitbox(), s.last_error
        sent = [a for t, a in fake.calls if t == "add_hitbox"][-1]
        assert sent == {"row": "jab", "frame": 9}
    finally:
        fake.stop()


def test_add_hitbox_validates_before_sending():
    fake, s = make()
    try:
        s.load_row("jab")
        assert not s.add_hitbox(frame=-1)
        assert not s.add_hitbox(frame=3, size="big")
        assert not s.add_hitbox(frame=3, colour=1) and "Unsupported" in s.last_error
        assert not any(t == "add_hitbox" for t, _ in fake.calls)
    finally:
        fake.stop()


def test_a_server_refusal_leaves_the_session_alone():
    fake, s = make()
    try:
        s.load_row("jab"); s.refresh_hitboxes()
        assert not s.add_hitbox(frame=3, bone="TAIL")
        assert "unknown bone" in s.last_error and not s.stale
        assert not s.delete_hitbox(7) and not s.stale
    finally:
        fake.stop()


def test_role_choices_group_sort_and_keep_a_raw_current_value():
    roles = [
        {"name": "FOOT_R", "group": "legs"}, {"name": "CHEST", "group": "body"},
        {"name": "HAND_R", "group": "arms"}, {"name": "FLOOR", "group": "anchors"},
        {"name": "ODD", "group": "mystery"},
    ]
    groups = props.role_choices(roles, "")
    assert [g for g, _ in groups] == ["body", "arms", "legs", "anchors", "other"]
    assert props.role_choices(roles, "HAND_R") == groups                 # a role: nothing extra
    raw = props.role_choices(roles, "hand.R")                            # an old raw joint still shows
    assert raw[-1] == ("raw", ["hand.R"])
    assert props.role_choices([], "") == []                              # no roles, nothing selected: empty
    assert props.role_choices([], "FOOT_R") == [("raw", ["FOOT_R"])]
