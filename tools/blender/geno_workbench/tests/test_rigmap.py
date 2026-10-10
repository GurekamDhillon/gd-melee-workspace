import rigmap as R

PLAN = {"joints": [
    {"index": 0, "name": "TopN", "parent": None, "synth": True},
    {"index": 1, "name": "b_C_Base", "parent": 0, "synth": False},
    {"index": 2, "name": "b_C_Pelvis", "parent": 1, "synth": False},
    {"index": 3, "name": "b_R_Hand", "parent": 2, "synth": False},
]}


def test_exact_match_skips_synth():
    m = R.build_joint_map(PLAN, ["b_C_Base", "b_C_Pelvis", "b_R_Hand"])
    assert m.by_index == {1: "b_C_Base", 2: "b_C_Pelvis", 3: "b_R_Hand"}
    assert m.skipped_synth == [0] and m.coverage() == 1.0
    assert m.order() == [1, 2, 3]


def test_suffix_and_case_tolerant():
    m = R.build_joint_map(PLAN, ["b_c_base.001", "B_C_Pelvis", "b_R_Hand"])
    assert set(m.by_index) == {1, 2, 3}


def test_unmapped_report():
    m = R.build_joint_map(PLAN, ["b_C_Base", "Extra"])
    assert m.missing_bones == [2, 3] and m.unmapped_bones == ["Extra"]
    assert abs(m.coverage() - 1 / 3) < 1e-9


def test_alias_wins():
    m = R.build_joint_map(PLAN, ["Hand.R", "b_C_Base"], aliases={"b_R_Hand": "Hand.R"})
    assert m.by_index[3] == "Hand.R"


def test_load_plan_roundtrip(tmp_path):
    import json
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(PLAN))
    assert R.load_plan(str(p))["joints"][1]["name"] == "b_C_Base"


def test_order_through_missing_and_synth_parents():
    plan = {"joints": [
        {"index": 2, "name": "Child", "parent": 8, "synth": False},
        {"index": 8, "name": "Middle", "parent": 0, "synth": False},
        {"index": 0, "name": "Bridge", "parent": 9, "synth": True},
        {"index": 9, "name": "Root", "parent": None, "synth": False},
    ]}
    m = R.build_joint_map(plan, ["Child", "Root"])
    assert m.order() == [9, 2]
    assert m.missing_bones == [8] and m.skipped_synth == [0]
    assert abs(m.coverage() - 2 / 3) < 1e-9
