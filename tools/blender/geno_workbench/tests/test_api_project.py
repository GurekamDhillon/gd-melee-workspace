import json
import api
import client
from fake_engine import FakeWorkbench


def test_set_project_resolves_paths(tmp_path):
    ws = tmp_path / "ws"
    proj = ws / "ports" / "synth"
    proj.mkdir(parents=True)
    (ws / ".git").write_text("gitdir: x\n")
    (proj / "workbench.json").write_text(json.dumps({
        "schema": "workbench/1", "plan_abs": "_build/synth/plan.json",
        "art_blend": "_build/synth/rig.blend", "art": {"bone_aliases": {"b_R_Hand": "Hand.R"}}}))
    assert api.set_project(str(proj))
    s = api.session()
    assert s.plan_path.replace("\\", "/").endswith("ws/_build/synth/plan.json")
    assert s.art_blend.replace("\\", "/").endswith("ws/_build/synth/rig.blend") and s.art_glb == ""
    assert s.bone_aliases == {"b_R_Hand": "Hand.R"}


def test_set_project_calibration_frame(tmp_path):
    (tmp_path / "workbench.json").write_text(json.dumps({"schema": "workbench/1", "art": {"calibration_frame": 10}}))
    assert api.set_project(str(tmp_path)) and api.session().calibration_frame == 10
    (tmp_path / "workbench.json").write_text(json.dumps({"schema": "workbench/1"}))
    assert api.set_project(str(tmp_path)) and api.session().calibration_frame == 1
    for bad in (0, -3, 2.5, "7", True):
        (tmp_path / "workbench.json").write_text(json.dumps({"schema": "workbench/1", "art": {"calibration_frame": bad}}))
        assert api.set_project(str(tmp_path)) is False, bad


def test_set_project_missing_file_is_false(tmp_path):
    assert api.set_project(str(tmp_path)) is False
    assert api.session().last_error


def test_frame_hooks_run_and_failures_do_not_fail_the_call():
    fake = FakeWorkbench(); port = fake.start()
    try:
        s = api.WbSession(lambda: client.McpClient(port=port, timeout=2.0))
        seen = []
        s.on_frame.append(lambda sess: seen.append(sess.info["frame"]))
        s.connect(); s.refresh_rows()
        assert s.load_row("jab") and s.set_frame(6) and s.step(1)
        assert seen == [1, 6, 7] or seen[-2:] == [6, 7]
        s.on_frame.append(lambda sess: 1 / 0)
        assert s.set_frame(3) is True and "division" in s.status and "division" in s.hook_error
    finally:
        fake.stop()
