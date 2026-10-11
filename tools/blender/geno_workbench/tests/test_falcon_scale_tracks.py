import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from falcon import scale_tracks  # noqa: E402


DOC = {"frames": 2, "joints": {"13": [[1, 1, 1], [0.95, 1, 1], [0.9, 1.1, 1]], "7": [[1, 1, 1]] * 3}}


def test_channels_map_each_scale_axis_to_a_pose_bone_curve_sampled_every_frame():
    chans = scale_tracks.channels(DOC)
    assert [(c[0], c[1]) for c in chans[:3]] == [('pose.bones["JOBJ_7"].scale', 0), ('pose.bones["JOBJ_7"].scale', 1),
                                                 ('pose.bones["JOBJ_7"].scale', 2)]          # joints in index order
    j13 = {c[1]: c for c in chans if c[2] == "JOBJ_13"}
    assert j13[0][3] == [(0, 1.0), (1, 0.95), (2, 0.9)]
    assert j13[1][3] == [(0, 1.0), (1, 1.0), (2, 1.1)]
    assert j13[1][0] == 'pose.bones["JOBJ_13"].scale'


def test_a_sidecar_with_the_wrong_row_count_is_refused():
    with pytest.raises(ValueError):
        scale_tracks.channels({"frames": 3, "joints": {"1": [[1, 1, 1]] * 3}})


def test_rest_channels_key_every_joint_the_clip_does_not_animate():
    chans = scale_tracks.rest_channels(DOC["joints"], DOC["frames"], 15)
    bones = {c[2] for c in chans}
    assert "JOBJ_13" not in bones and "JOBJ_7" not in bones and len(bones) == 13
    assert all(c[3] == [(0, 1.0), (2, 1.0)] for c in chans)
    assert len(chans) == 13 * 3
    # animated + rest cover every joint exactly once
    allc = scale_tracks.channels(DOC) + chans
    assert sorted({c[2] for c in allc}) == sorted("JOBJ_%d" % j for j in range(15))


def test_load_round_trips_the_driver_json(tmp_path):
    p = tmp_path / "x.scale.json"
    p.write_text(json.dumps(DOC), encoding="utf-8")
    assert scale_tracks.load(p) == DOC
