import api, client
from fake_engine import FakeWorkbench


def make():
    fake = FakeWorkbench(); port = fake.start()
    s = api.WbSession(lambda: client.McpClient(port=port, timeout=2.0))
    s.connect(); s.refresh_rows()
    return fake, s


def test_problems_and_goto():
    fake, s = make()
    try:
        assert s.run_checks() and s.problems[0]["kind"] == "wrong_limb"
        assert s.goto_problem(0)
        assert s.row == "jab" and s.info["frame"] == 5      # first active frame of hitbox 0
    finally:
        fake.stop()


def test_edit_marks_stale_until_reload():
    fake, s = make()
    try:
        s.load_row("jab"); s.refresh_hitboxes()
        assert not s.stale
        assert s.edit_hitbox(row="jab", ordinal=0, bone="FOOT_R")
        assert s.stale and fake.stale
        assert s.rebuild_reload()
        assert not s.stale and not fake.stale and s.row == "jab"
    finally:
        fake.stop()


def test_failed_rebuild_keeps_stale():
    fake, s = make()
    try:
        s.load_row("jab"); s.refresh_hitboxes(); s.edit_hitbox(row="jab", ordinal=0, size=3.5)
        fake.fail_next = "build failed"
        assert s.rebuild_reload() is False and s.stale and "build failed" in s.last_error
    finally:
        fake.stop()


def test_only_changed_fields_are_sent():
    fake, s = make()
    try:
        s.load_row("jab"); s.refresh_hitboxes()
        s.edit_hitbox(row="jab", ordinal=0, size=3.5)
        name, args = [c for c in fake.calls if c[0] == "edit_hitbox"][-1]
        assert args == {"row": "jab", "ordinal": 0, "size": 3.5}
    finally:
        fake.stop()


def test_scrub_is_coalesced():
    fake, s = make()
    try:
        s.load_row("jab")
        for n in (3, 4, 5, 9):
            s.coalesced_set_frame(n)
        assert s.flush_pending() and s.info["frame"] == 9
        sets = [c for c in fake.calls if c[0] == "set_frame"]
        assert len(sets) == 1
    finally:
        fake.stop()
