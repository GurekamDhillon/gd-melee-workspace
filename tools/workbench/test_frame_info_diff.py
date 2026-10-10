import pytest
import frame_info_diff as D


def info(x=0.0):
    return {"bones": [{"joint": 1, "pos": {"x": x, "y": 0, "z": 0}, "mtx": [1, 0, 0, x, 0, 1, 0, 0, 0, 0, 1, 0]}],
            "root": {"mtx": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]}, "hitboxes": [], "hurtboxes": [],
            "ecb": {"bottom": {"x": 0, "y": 0}}}


def test_equal():
    assert D.diff(info(), info())["max_abs"] == 0 and D.ok(info(), info())


def test_difference_found():
    d = D.diff(info(0.0), info(0.25))
    assert abs(d["max_abs"] - 0.25) < 1e-12 and "bones" in d["worst"] and not D.ok(info(0.0), info(0.25))


def test_bone_count_mismatch():
    b = info(); b["bones"].append(dict(b["bones"][0], joint=2))
    with pytest.raises(ValueError, match="bone count differs"):
        D.diff(info(), b)


def full_info():
    snapshot = info()
    snapshot["frame"] = 1
    snapshot["hitboxes"] = [
        {"slot": 0, "world": {"x": 3, "y": 4, "z": 5}, "radius": 2, "active": True}
    ]
    snapshot["hurtboxes"] = [
        {"a": {"x": 1, "y": 0, "z": 0},
         "b": {"x": 2, "y": 0, "z": 0}, "radius": 1}
    ]
    snapshot["ecb"].update({
        "left": {"x": -1, "y": 1},
        "right": {"x": 1, "y": 1},
        "top": {"x": 0, "y": 2},
    })
    return snapshot


def test_fields_count_scalar_components():
    assert D.diff(info(), info()) == {"max_abs": 0.0, "worst": "", "fields": 29}
    assert D.diff(full_info(), full_info())["fields"] == 44


@pytest.mark.parametrize(("keys", "path"), [
    (("bones", 0, "pos", "x"), "bones[0].pos.x"),
    (("bones", 0, "mtx", 3), "bones[0].mtx[3]"),
    (("root", "mtx", 3), "root.mtx[3]"),
    (("hitboxes", 0, "world", "y"), "hitboxes[0].world.y"),
    (("hurtboxes", 0, "a", "z"), "hurtboxes[0].a.z"),
    (("hurtboxes", 0, "b", "x"), "hurtboxes[0].b.x"),
    (("ecb", "bottom", "y"), "ecb.bottom.y"),
    (("ecb", "left", "x"), "ecb.left.x"),
    (("ecb", "right", "x"), "ecb.right.x"),
    (("ecb", "top", "y"), "ecb.top.y"),
])
def test_every_selected_field_is_compared(keys, path):
    from copy import deepcopy

    a = full_info()
    b = deepcopy(a)
    value = b
    for key in keys[:-1]:
        value = value[key]
    value[keys[-1]] += 0.5
    assert D.diff(a, b) == {"max_abs": 0.5, "worst": path, "fields": 44}


@pytest.mark.parametrize("category", ["hitboxes", "hurtboxes"])
def test_other_collection_count_mismatches_rejected(category):
    from copy import deepcopy

    a = full_info()
    b = deepcopy(a)
    b[category].append(deepcopy(b[category][0]))
    with pytest.raises(ValueError, match="count differs"):
        D.diff(a, b)


def test_missing_component_rejected():
    b = info()
    del b["ecb"]["bottom"]["y"]
    with pytest.raises(ValueError, match="ecb.bottom.y"):
        D.diff(info(), b)


def test_matrix_component_count_mismatch_rejected():
    b = info()
    b["root"]["mtx"].pop()
    with pytest.raises(ValueError, match="component count differs at root.mtx"):
        D.diff(info(), b)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_components_rejected(value):
    b = info()
    b["bones"][0]["pos"]["x"] = value
    with pytest.raises(ValueError, match="non-finite"):
        D.diff(info(), b)


@pytest.mark.parametrize("tol", [-1, float("nan"), float("inf"), -float("inf")])
def test_invalid_tolerance_rejected(tol):
    with pytest.raises(ValueError, match="tol must be finite and nonnegative"):
        D.ok(info(), info(), tol)


def test_tolerance_is_inclusive():
    assert D.ok(info(), info(0.25), tol=0.25)
    assert not D.ok(info(), info(0.25), tol=0.249)


def test_unlisted_metadata_ignored():
    from copy import deepcopy

    a = full_info()
    b = deepcopy(a)
    b["frame"] = 999
    b["root"]["facing"] = -1
    b["hitboxes"][0]["radius"] = 20
    b["hurtboxes"][0]["radius"] = 10
    assert D.ok(a, b)
    assert D.diff(a, b)["fields"] == 44


def test_dictionary_order_does_not_affect_comparison():
    from copy import deepcopy

    a = full_info()
    b = deepcopy(a)
    b["ecb"] = dict(reversed(list(b["ecb"].items())))
    b["ecb"]["bottom"] = {"y": 0, "x": 0}
    assert D.diff(a, b) == {"max_abs": 0.0, "worst": "", "fields": 44}


@pytest.mark.parametrize(("offset", "status", "exit_code"), [
    (0.0, "OK", 0),
    (0.25, "DIFF", 1),
])
def test_cli_output_and_exit_status(tmp_path, offset, status, exit_code):
    import json
    import subprocess
    import sys

    a_path, b_path = tmp_path / "a.json", tmp_path / "b.json"
    a_path.write_text(json.dumps(info()), encoding="utf-8")
    b_path.write_text(json.dumps(info(offset)), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, D.__file__, str(a_path), str(b_path), "--tol", "1e-3"],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == exit_code
    assert result.stderr == ""
    assert result.stdout.strip().endswith(f"fields=29 {status}")
    assert f"max_abs={offset:.12g}" in result.stdout
    expected_path = "bones[0].pos.x" if offset else "-"
    assert f"worst={expected_path}" in result.stdout


def test_cli_count_mismatch_is_input_error(tmp_path):
    import json
    import subprocess
    import sys

    a_path, b_path = tmp_path / "a.json", tmp_path / "b.json"
    b = info()
    b["bones"].append(dict(b["bones"][0], joint=2))
    a_path.write_text(json.dumps(info()), encoding="utf-8")
    b_path.write_text(json.dumps(b), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, D.__file__, str(a_path), str(b_path)],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "bone count differs: 1 vs 2" in result.stderr


def test_cli_invalid_tolerance_is_input_error(tmp_path):
    import json
    import subprocess
    import sys

    a_path, b_path = tmp_path / "a.json", tmp_path / "b.json"
    a_path.write_text(json.dumps(info()), encoding="utf-8")
    b_path.write_text(json.dumps(info()), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, D.__file__, str(a_path), str(b_path), "--tol", "-1"],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "tol must be finite and nonnegative" in result.stderr
