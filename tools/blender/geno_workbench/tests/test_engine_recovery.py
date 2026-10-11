"""A row the engine refuses, and a dead engine: the session stays connected, falls back to the wait row and restarts."""
import api
import client
import launch
import rigmap
from fake_engine import FakeWorkbench


def make():
    fake = FakeWorkbench(); port = fake.start()
    s = api.WbSession(lambda: client.McpClient(port=port, timeout=2.0))
    s.connect(); s.refresh_rows()
    return fake, s


def test_refused_row_falls_back_to_wait():
    fake, s = make()
    try:
        fake.refused_rows = {"jab"}
        assert s.load_row("jab")
        assert s.loaded_row == "wait" and "revival platform" in s.status and s.connected
    finally:
        fake.stop()


def test_refused_row_without_fallback_reports():
    fake, s = make()
    try:
        fake.refused_rows = {"jab"}
        assert s.load_row("jab", fallback=False) is False
        assert s.connected and "revival platform" in s.last_error
    finally:
        fake.stop()


def test_dead_engine_keeps_the_server_link_and_restarts():
    fake, s = make()
    try:
        s.load_row("jab")
        fake.dead = True
        assert s.set_frame(5) is False and "engine connection lost" in s.last_error
        assert s.connected, "an engine death must not drop the link to the server (Restart engine needs it)"
        assert s.engine_restart() and not fake.dead
    finally:
        fake.stop()


def test_next_row_pick_restarts_a_dead_engine():
    fake, s = make()
    try:
        fake.dead = True
        assert s.load_row("dair") and not fake.dead and s.loaded_row == "dair"
    finally:
        fake.stop()


def test_previewable_and_reference_choice():
    rows = [{"name": "rebirth", "motions": [12], "clip": "Wait1"}, {"name": "rebirth_wait", "motions": [13], "clip": "Wait1"},
            {"name": "other", "motions": [3], "clip": "Wait1", "previewable": True}, {"name": "wait", "motions": [14], "clip": "Wait1"}]
    assert [rigmap.row_previewable(r) for r in rows] == [False, False, True, True]
    assert rigmap.row_previewable({"name": "x", "motions": [14], "previewable": False}) is False
    assert rigmap.wait_row_name(rows) == "wait"
    ref, clip = rigmap.pick_reference_row(rows[:2] + rows[2:3], lambda c: True)
    assert ref["name"] == "other"


def test_choose_engine(tmp_path):
    build = tmp_path / "_build"; build.mkdir()
    old = tmp_path / "old.exe"; old.write_bytes(b"x")
    new = build / "melee-pc.exe"; new.write_bytes(b"y")
    import os
    os.utime(old, (1000, 1000)); os.utime(new, (5000, 5000))
    chosen, notes = launch.choose_engine(tmp_path, str(old))
    assert chosen == str(new) and notes
    chosen, notes = launch.choose_engine(tmp_path, str(old), explicit=True)
    assert chosen == str(old) and notes[0].startswith("WARNING")


def test_project_action_offset(tmp_path):
    import json
    (tmp_path / "workbench.json").write_text(json.dumps({"schema": "workbench/1", "art": {"calibration_action_offset": 0}}))
    assert api.set_project(str(tmp_path)) and api.session().calibration_action_offset == 0
    (tmp_path / "workbench.json").write_text(json.dumps({"schema": "workbench/1", "art": {}}))
    assert api.set_project(str(tmp_path)) and api.session().calibration_action_offset == 1


def test_unpreviewable_list_matches_the_launcher_header():
    import re
    from pathlib import Path
    header = (Path(__file__).resolve().parents[3] / "release/launcher/qt/workbench/geno_data.h").read_text(encoding="utf-8")
    listed = re.search(r"kUnpreviewable\[\] = \{([^}]*)\}", header).group(1)
    assert {int(x) for x in listed.split(",")} == set(rigmap.UNPREVIEWABLE_MOTIONS)
