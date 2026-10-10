"""Maintained source overrides survive Stage B without entering Stage A."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

PORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT / "tools"))


def build_module():
    spec = importlib.util.spec_from_file_location("goku_attribute_build", PORT / "tools/build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_overrides_replace_design_defaults_and_update_evidence():
    build = build_module()
    source = {"attributes": {"weight": 81.5, "gravity": 0.2}}
    attrs = {"weight": 73.25, "walk_max_vel": 1.25}
    evidence = [{"field": "weight", "value": 73.25, "basis": "synthetic starting design"}]
    result, records = build.apply_attribute_overrides(attrs, evidence, source)
    assert result == {"weight": 81.5, "walk_max_vel": 1.25, "gravity": 0.2}
    assert next(e for e in records if e["field"] == "weight")["value"] == 81.5
    assert next(e for e in records if e["field"] == "gravity")["classification"] == "authored override"
    assert attrs == {"weight": 73.25, "walk_max_vel": 1.25} and evidence[0]["value"] == 73.25


@pytest.mark.parametrize("attrs", [[], {"unknown": 1}, {"weight": True}, {"weight": "80"},
                                   {"weight": float("inf")}, {"rapid_jab_window": 4.5}])
def test_bad_source_overrides_are_rejected_by_geno_schema(attrs):
    with pytest.raises(ValueError):
        build_module().apply_attribute_overrides({}, [], {"attributes": attrs})


def test_source_edit_keeps_stage_a_signature_current(tmp_path):
    build = build_module()
    fighter = tmp_path / "fighter.json"
    fighter.write_text(json.dumps({"key": "synthetic"}), encoding="utf-8")
    before = build.stage_a_signature(fighter)
    original_port = build.PORT
    build.PORT = tmp_path
    try:
        (tmp_path / "gameplay.json").write_text(json.dumps({"attributes": {"weight": 81.5}}), encoding="utf-8")
        first = build.stage_a_signature(fighter)
        (tmp_path / "gameplay.json").write_text(json.dumps({"attributes": {"weight": 82.5}}), encoding="utf-8")
        assert build.stage_a_signature(fighter) == first
    finally:
        build.PORT = original_port
    assert build.stage_a_signature(fighter) == before
