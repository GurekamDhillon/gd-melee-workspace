"""falcon/hand_apply.py on a synthetic bank (no disc data): the retail clip keeps every untouched track byte for byte, the moved joint
carries the hand pose, the rebuild is repeatable and a missing hand file restores the pristine bank."""
import copy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parent))
from tools.geno.artist.blender import hand_layer as HL  # noqa: E402
from tools.geno.artist.model import AF  # noqa: E402
from falcon import hand_apply as H  # noqa: E402

N = 12


def clip_archive(name, offset):
    tracks = []
    for ji in range(3):
        jt = []
        if ji >= 1:
            for k, ty in enumerate((1, 2, 3)):
                vals = np.sin(np.arange(N) / 3.0 + ji + k) * 0.3
                body, fv, fs = AF._encode_channel(vals, AF.FRAC_ROT)
                jt.append((ty, body, fv, fs))
        tracks.append(jt)
    return AF.F.build_tree_archive("PlyTest_Share_ACTION_%s_figatree" % name, N - 1, tracks)


@pytest.fixture
def bank(tmp_path):
    blob = bytearray()
    clips = {}
    for name in ("Wait", "Attack11"):
        arc = clip_archive(name, len(blob))
        clips[name] = {"symbol": "s_" + name, "offset": len(blob), "bytes": len(arc), "frames": float(N - 1)}
        blob += arc
        while len(blob) % 0x20:
            blob.append(0)
    path = tmp_path / "files" / "GnTestAJ.dat"
    path.parent.mkdir()
    path.write_bytes(bytes(blob))
    plan = {"bank": {"file": "GnTestAJ.dat", "bytes": len(blob), "clips": clips}}
    return tmp_path, path, plan, bytes(blob)


def hand_doc(project, with_abs=True):
    q = np.array([[0, 0, np.sin(a / 2), np.cos(a / 2)] for a in np.linspace(0, 1.2, N)])
    clip = {"mode": "layer", "frames": N, "bones": {"JOBJ_1": {"rot": q.tolist()}}}
    if with_abs:
        clip["abs"] = {"JOBJ_1": {"rot": q.tolist()}}
    doc = HL.empty("Falcon")
    doc["clips"]["Attack11"] = clip
    HL.save(Path(project) / "anim" / "hand.json", doc)
    return q


def test_moved_joint_replaced_and_other_tracks_untouched(bank):
    project, path, plan, pristine = bank
    q = hand_doc(project)
    report = H.apply_hand(project, path, plan)
    assert report[0]["replaced"] == ["JOBJ_1"] and plan["bank"]["pristine_bytes"] == len(pristine)
    info = plan["bank"]["clips"]["Attack11"]
    assert info["offset"] >= len(pristine) and info["offset"] % 0x20 == 0
    data = path.read_bytes()
    assert data[:len(pristine)] == pristine                      # nothing already in the bank moved
    new = data[info["offset"]:info["offset"] + info["bytes"]]
    old = pristine[plan["bank"]["clips"]["Wait"]["offset"]:][:0]   # (shape check only)
    sym, typ, flags, frames, joints = H.parse_raw(new)
    _, _, _, _, orig = H.parse_raw(clip_archive("Attack11", 0))
    assert frames == N - 1 and len(joints) == 3
    assert joints[2] == orig[2] and joints[0] == orig[0]         # untouched joints: identical tracks
    assert joints[1] != orig[1]
    # decode the moved joint: euler (0, 0, angle) and the angle follows the hand pose
    _, tree = AF.F.parse_archive(new)
    trk = {t["type"]: t for t in tree["joints"][1]}
    got = np.array([AF.F.evaluate(trk[3]["keys"], f) for f in range(N)])
    want = np.linspace(0, 1.2, N)
    assert np.max(np.abs(got - want)) < 2e-3
    assert abs(AF.F.evaluate(trk[1]["keys"], 5)) < 2e-3


def test_rebuild_is_repeatable_and_restores_without_a_hand_file(bank):
    project, path, plan, pristine = bank
    hand_doc(project)
    p1 = copy.deepcopy(plan)
    H.apply_hand(project, path, p1)
    first = path.read_bytes()
    p2 = copy.deepcopy(plan)                                     # a rebuild starts again from the manifest plan
    H.apply_hand(project, path, p2)
    assert path.read_bytes() == first and p1 == p2               # appended once, not twice
    (Path(project) / "anim" / "hand.json").unlink()
    p3 = copy.deepcopy(plan)
    assert H.apply_hand(project, path, p3) == []
    assert path.read_bytes() == pristine and p3["bank"]["clips"] == plan["bank"]["clips"]


def test_unknown_row_is_skipped_and_missing_abs_is_an_error(bank):
    project, path, plan, pristine = bank
    doc = HL.empty("Falcon")
    doc["clips"]["NoSuchClip"] = {"mode": "layer", "frames": 2, "bones": {}}
    HL.save(Path(project) / "anim" / "hand.json", doc)
    assert H.apply_hand(project, path, copy.deepcopy(plan))[0]["skipped"]
    hand_doc(project, with_abs=False)
    with pytest.raises(ValueError, match="abs"):
        H.apply_hand(project, path, copy.deepcopy(plan))
