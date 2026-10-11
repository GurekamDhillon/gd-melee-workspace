"""hand_layer.py: format validation and how a hand clip is applied to a converted row (pure Python)."""
import copy
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from tools.geno.artist.blender import hand_layer as HL  # noqa: E402


def quat(deg, axis=(0, 0, 1)):
    return R.from_rotvec(np.radians(deg) * np.asarray(axis, float)).as_quat()


def converted(count=6):
    rest = {"A": quat(10), "B": quat(0, (1, 0, 0))}
    rots = {k: np.tile(v, (count, 1)) for k, v in rest.items()}
    return rest, rots, np.tile([0., 1., 0.], (count, 1))


def clip(mode="layer", frames=6, bone="A", deg=30):
    return {"mode": mode, "frames": frames, "bones": {bone: {"rot": [quat(deg).tolist()] * frames, "loc": [[0, .5, 0]] * frames}}}


def doc(**clips):
    d = HL.empty("T")
    d["clips"].update(clips)
    return d


def apply(c, count=6, rots=None, hips=None, root=None, rest=None):
    r0, r1, h = converted(count)
    rest = rest or r0
    return HL.apply_clip(c, count=count, rotations=r1 if rots is None else rots, rest_q=rest, hips=h if hips is None else hips, root=root,
                         hips_bone="A", root_bone="Z", rest_hips=[0, 1, 0])


def test_layer_adds_on_top_of_the_converted_row():
    rest, rots, hips = converted()
    hips2, root, rep = apply(clip("layer", deg=30), rots=rots, hips=hips)
    assert np.isclose(R.from_quat(rots["A"][0]).magnitude(), np.radians(40), atol=1e-6)   # 10 deg converted + 30 deg hand
    assert np.allclose(rots["B"], quat(0, (1, 0, 0)))                                       # untouched bone untouched
    assert np.allclose(hips2[:, 1], 1.5) and root is None and rep["rotated"] == ["A"]


def test_replace_starts_from_rest_and_ignores_the_converted_row():
    rest, rots, hips = converted()
    rots["B"] = np.tile(quat(90), (6, 1))                         # converted motion that must vanish
    hips2, _, _ = apply(clip("replace", deg=30), rots=rots, hips=hips + 9)
    assert np.isclose(R.from_quat(rots["A"][0]).magnitude(), np.radians(40), atol=1e-6)
    assert np.allclose(rots["B"], quat(0, (1, 0, 0))) and np.allclose(hips2[:, 1], 1.5)


def test_length_mismatch_is_held_or_cropped_and_reported():
    rest, rots, hips = converted(8)
    _, _, rep = apply(clip("layer", frames=4), count=8, rots=rots, hips=hips)
    assert rep["notes"] and "held" in rep["notes"][0]
    assert np.isclose(R.from_quat(rots["A"][7]).magnitude(), np.radians(40), atol=1e-6)


def test_translation_on_other_bones_is_reported_not_applied():
    _, _, rep = apply(clip("layer", bone="B"))
    assert rep["translation_dropped"] == ["B"]


def test_root_translation_creates_the_root_track():
    c = {"mode": "layer", "frames": 6, "bones": {"Z": {"loc": [[1, 0, 0]] * 6}}}
    rest, rots, hips = converted()
    rots["Z"] = np.tile([0., 0, 0, 1], (6, 1))
    _, root, _ = apply(c, rots=rots, hips=hips)
    assert np.allclose(root[:, 0], 1)


def test_validation_rejects_bad_files():
    good = doc(Jab=clip())
    HL.validate(good)

    def nan(d):
        d["clips"]["Jab"]["bones"]["A"]["rot"][0] = [0, 0, float("nan"), 1]

    for mutate in (lambda d: d.update(schema="x"), lambda d: d["clips"]["Jab"].update(mode="add"),
                   lambda d: d["clips"]["Jab"].update(frames=0), lambda d: d["clips"]["Jab"]["bones"]["A"].update(rot=[[0, 0, 0, 1]]),
                   nan, lambda d: d["clips"].update({"x" * 32: clip()})):
        bad = copy.deepcopy(good)
        mutate(bad)
        with pytest.raises(ValueError):
            HL.validate(bad)


def test_sparse_bones_keeps_only_what_moved_and_save_is_stable(tmp_path):
    ident = np.tile([0., 0, 0, 1], (4, 1))
    moved = np.tile(quat(20), (4, 1))
    noise = np.tile(R.from_rotvec([0, 0, 1e-7]).as_quat(), (4, 1))
    out = HL.sparse_bones({"a": moved, "b": ident, "c": noise}, {"a": np.zeros((4, 3)), "d": np.full((4, 3), .5)})
    assert sorted(out) == ["a", "d"] and "loc" not in out["a"]
    path = tmp_path / "anim" / "hand.json"
    d = doc(Jab={"mode": "layer", "frames": 4, "bones": out})
    HL.save(path, d)
    stamp = path.stat().st_mtime_ns
    HL.save(path, d)
    assert path.stat().st_mtime_ns == stamp                # unchanged content: no rewrite, no spurious Stage A rebuild
    assert HL.load(path)["clips"]["Jab"]["frames"] == 4 and HL.load(tmp_path / "none.json") is None
