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


def test_status_names_the_build_mode_and_time():
    fake, s = make()
    try:
        s.load_row("jab"); s.refresh_hitboxes(); s.edit_hitbox(row="jab", ordinal=0, size=3.5)
        fake.build_mode = "gameplay-only"
        assert s.rebuild_reload()
        assert "gameplay-only build 1.5 s" in s.status, s.status
        assert s.last_rebuild["mode"] == "gameplay-only" and s.last_rebuild["total_seconds"] >= 0
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


def test_rebuild_and_reload_get_a_long_call_budget():
    seen = {}

    class Conn:
        def call(self, tool, args=None, timeout=None):
            seen[tool] = timeout
            return {}

    api.WbSession._raw_call(Conn(), "rebuild", {})
    api.WbSession._raw_call(Conn(), "list_rows", {})
    assert seen["rebuild"] >= 1800 and seen["list_rows"] is None


def test_requests_send_the_row_name_not_the_engine_clip_label():
    """Owner bug 2026-10-10: edit_hitbox/suggest_hitbox_bone sent 'AttackAirLw' (the clip) and the server said unknown row."""
    fake, s = make()
    try:
        fake.label_rows_by_clip = True
        fake.bare_load_row = True  # the real server's load_row reply has no pose
        assert s.load_row("dair", refresh_hitboxes=True), s.last_error
        assert s.row == "AttackAirLw" and s.source_row == "dair"
        assert s.refresh_hitboxes(), s.last_error
        assert s.suggest_bone(0), s.last_error
        assert s.edit_hitbox(ordinal=0, bone="FOOT_R"), s.last_error
        assert s.edit_hitbox(ordinal=0, size=3.5), s.last_error
        assert s.run_checks(), s.last_error
        assert s.rebuild_reload(), s.last_error
        assert s.source_row == "dair" and s.hitboxes
        if s.problems:
            assert s.goto_problem(0), s.last_error
    finally:
        fake.stop()


def _snapshot(s):
    return (s.row, s.loaded_row, s.frame, dict(s.info or {}), sorted(s.cache.frames))


def test_unconfigured_rebuild_keeps_row_frame_and_cache():
    fake, s = make()
    try:
        s.prefetch = True
        s.load_row("jab"); s.set_frame(7)
        s.start_prefetch()
        end = __import__("time").time() + 5
        while not s.cache_ready() and __import__("time").time() < end:
            __import__("time").sleep(0.01)
        before = _snapshot(s)
        assert before[4], "cache should be filled"
        fake.rebuild_unconfigured = True
        assert s.rebuild_reload() is False
        assert "rebuild not configured" in s.last_error
        assert _snapshot(s) == before and s.connected
        # and it can be done twice in a row without ever losing the row
        assert s.rebuild_reload() is False and _snapshot(s) == before
    finally:
        fake.stop()


def test_failed_build_keeps_row_frame_and_cache():
    fake, s = make()
    try:
        s.load_row("jab"); s.set_frame(7); s.edit_hitbox(row="jab", ordinal=0, size=3.5)
        before = _snapshot(s)
        fake.fail_next = "build failed"
        assert s.rebuild_reload() is False and s.stale
        assert _snapshot(s) == before
        assert s.rebuild_reload() and s.row == "jab" and s.frame == 7 and not s.stale
    finally:
        fake.stop()


def test_failed_reload_keeps_row():
    fake, s = make()
    try:
        s.load_row("jab"); s.set_frame(7)
        before = _snapshot(s)
        real = fake._execute
        def boom(tool, args):
            if tool == "reload":
                raise ValueError("reload timed out")
            return real(tool, args)
        fake._execute = boom
        assert s.rebuild_reload() is False
        assert "reload timed out" in s.last_error and (s.row, s.frame) == ("jab", 7)
    finally:
        fake.stop()


def test_project_without_build_or_roles_is_refused_with_a_status(tmp_path):
    import json
    (tmp_path / "plan.json").write_text(json.dumps({"joints": []}))
    (tmp_path / "workbench.json").write_text(json.dumps(
        {"schema": "workbench/1", "plan": "plan.json", "rebuild": []}))
    fake, s = make()
    try:
        s.load_row("jab")
        assert api.set_project(str(tmp_path))
        sess = api.session()
        assert sess.can_rebuild is False and sess.has_roles is False
        # act on the module session, as the panel does
        sess.client_factory = s.client_factory
        sess.connect(); sess.load_row("jab")
        calls = len(fake.calls)
        assert sess.rebuild_reload() is False
        assert "no build configured" in sess.status and sess.last_error == ""
        assert sess.run_checks() is False and "no role map" in sess.status
        assert sess.suggest_bone(0) is False and "no role map" in sess.status
        assert len(fake.calls) == calls, "refused actions must not call the engine"
        assert sess.row == "jab"
    finally:
        api.session().can_rebuild = api.session().has_roles = True
        fake.stop()
