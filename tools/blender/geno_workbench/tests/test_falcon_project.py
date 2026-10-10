"""Falcon metadata and build contracts. Fixtures are authored, never extracted."""
import copy
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from falcon import metadata, project_build

TEMPLATE = ROOT / "tools/blender/geno_workbench/falcon/project"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def synthetic_plan():
    # Deliberately different from Falcon's numbering to catch a hardcoded joint map.
    return {"joints": [{"index": i, "name": f"j{i}", "parent": None} for i in range(64)],
            "parts": {"part_to_joint": [i + 4 for i in range(54)]},
            "bank": {"clips": {"Idle": {"frames": 30}, "Punch": {"frames": 12},
                               "Kick": {"frames": 19}}},
            "row_clips": ["Idle", "Punch", "Kick", None],
            "row_flags": [0, 0, 0, None], "row_blend": [[0, 0]] * 4}


def test_enums_resolve_symbolic_bases_and_motion_rows():
    enums = metadata.enum_values("typedef enum ftCo_Submotion { ftCo_SM_None = -1, "
                                 "ftCo_SM_Idle, ftCo_SM_Punch, ftCo_SM_Count } ftCo_Submotion;",
                                 "ftCo_Submotion")
    enums.update(metadata.enum_values("typedef enum ftCa_Submotion { "
        "ftCa_SM_Kick = ftCo_SM_Count, ftCa_SM_Count, "
        "ftCa_SM_SelfCount = ftCa_SM_Count - ftCo_SM_Count } ftCa_Submotion;",
        "ftCa_Submotion", enums))
    rows = metadata.state_entries("MotionState table[] = { { // ftCo_MS_Wait = 14\n"
        "ftCo_SM_Idle, flags }, { // ftCo_MS_Attack11 = 44\nftCo_SM_Punch, flags }, "
        "{ // ftCa_MS_SpecialN = 347\nftCa_SM_Kick, flags } };", enums)
    assert rows == [{"motion": 14, "state": "Wait", "subaction": 0},
                    {"motion": 44, "state": "Attack11", "subaction": 1},
                    {"motion": 347, "state": "SpecialN", "subaction": 2}]
    with pytest.raises(ValueError, match="Unknown"):
        metadata.state_entries("{ // ftCo_MS_Wait = 14\nftCo_SM_Unknown, flags }", enums)


def test_rows_use_subactions_not_motion_ids_and_keep_clipless_states(synthetic_plan):
    states = [{"motion": 14, "state": "Wait", "subaction": 0},
              {"motion": 44, "state": "Attack11", "subaction": 1},
              {"motion": 45, "state": "Attack12", "subaction": 1},
              {"motion": 347, "state": "SpecialN", "subaction": 2},
              {"motion": 11, "state": "Sleep", "subaction": -1},
              {"motion": 99, "state": "Unavailable", "subaction": 3}]
    rows = metadata.make_rows(synthetic_plan, states, {1: "moves/001.genoasm"},
                              [{"name": "jab1", "motions": [44], "tag": "jab"}])
    by = {r["motions"][0]: r for r in rows}
    assert set(by) == {11, 14, 44, 45, 99, 347}
    assert by[44]["name"] == "jab1"
    assert by[44]["pick"]["clip"] == "Punch"
    assert by[347]["pick"]["clip"] == "Kick"
    assert by[44]["script"] == by[45]["script"] == "moves/001.genoasm"
    assert by[11]["pick"]["clip"] == ""
    assert by[11]["availability"] == "no-fixed-animation"
    assert by[99]["availability"] == "missing-clip"
    assert len({r["name"] for r in rows}) == len(rows)


def test_roles_use_retail_parts_order_and_omit_missing_parts(synthetic_plan):
    table = read_json(TEMPLATE / "role_map.json")
    roles, tokens = metadata.resolve_roles(synthetic_plan, table)
    assert roles["chest"] == [21]  # BustN is slot 17, not the decomp enum's slot 16.
    assert roles["head"] == [39]
    assert tokens["HAND_L"] == 26
    assert tokens["HAND_R"] == 44
    assert tokens["HIPS"] == 8
    assert tokens["FOOT_L"] == 14
    synthetic_plan["parts"]["part_to_joint"][5] = 255
    roles, _ = metadata.resolve_roles(synthetic_plan, table)
    assert roles["spine"] == [20]  # documented WaistB fallback, not joint 255
    synthetic_plan["parts"]["part_to_joint"][35] = 255
    roles, tokens = metadata.resolve_roles(synthetic_plan, table)
    assert "head" not in roles and "HEAD" not in tokens
    synthetic_plan["parts"]["part_to_joint"][17] = 1000
    with pytest.raises(ValueError, match="joint"):
        metadata.resolve_roles(synthetic_plan, table)


@pytest.fixture
def codec():
    from tools.test_support import require_game
    require_game("pc/geno/geno.h")
    from tools.geno import script
    return script


@pytest.fixture
def prepared(tmp_path, synthetic_plan, codec):
    work = tmp_path / "_build" / "falcon"
    package = work / "mods/geno-falcon"
    project = work / "project"
    (package / "files").mkdir(parents=True)
    (package / "files/body.dat").write_bytes(b"synthetic costume")
    (package / "files/bank.dat").write_bytes(b"synthetic bank")
    (package / "moves").mkdir()
    (package / "moves/punch.words").write_text("0x08000005 0x2C00D008 0x04000000 "
        "0x00000000 0xB498C011 0x0F800487 0x04000002 0x40000000 0x00000000")
    plan = copy.deepcopy(synthetic_plan)
    plan["bank"]["file"] = "bank.dat"
    write_json(package / "files/plan.json", plan)
    write_json(package / "mod.json", {"id": "geno-falcon"})
    document = {"geno": 10, "fighters": [{"define": {"key": "geno-falcon", "template": "captain"},
        "fighter": {"plan": "plan.json", "animation": "bank.dat", "costumes": [{"file": "body.dat"}]},
        "attributes": {"walk_speed": 1.25}, "subactions": [
            {"index": 0, "words": [0]}, {"index": 1, "file": "moves/punch.words", "move_tag": "jab"},
            {"index": 2, "words": [5 << 26, 3, 0, (1 << 26) | 2, 6 << 26]}]}]}
    write_json(package / "geno.json", document)
    states = [{"motion": 14, "state": "Wait", "subaction": 0},
              {"motion": 44, "state": "Attack11", "subaction": 1},
              {"motion": 45, "state": "Attack12", "subaction": 1},
              {"motion": 347, "state": "SpecialN", "subaction": 2}]
    project_build.prepare(project, package, states, TEMPLATE, root=ROOT)
    return project, package, document


def test_rebuild_changes_words_preserves_assets_and_does_not_extract(prepared, monkeypatch, codec):
    project, package, original = prepared
    def forbidden(*args, **kwargs):
        raise AssertionError("a complete package must not invoke extraction or copy assets")
    monkeypatch.setattr(project_build.subprocess, "run", forbidden)
    assets = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in (package / "files").glob("*.dat")}
    row = next(r for r in read_json(project / "gameplay.json")["moves"] if r["motions"] == [44])
    path = project / row["script"]
    text = path.read_text()
    assert "raw=" not in text
    path.write_text(text.replace("damage=8 ", "damage=12 ").replace("joint=26 ", "joint=@HAND_R@ "))
    result = project_build.rebuild(project)
    assert result == "gameplay-only"
    doc = read_json(package / "geno.json")
    assert doc["fighters"][0]["attributes"] == original["fighters"][0]["attributes"]
    overlay = next(o for o in doc["fighters"][0]["subactions"] if o["index"] == 1)
    words = codec.read_words((package / overlay["file"]).read_text())
    assert words[1] & 1023 == 12
    assert words[1] >> 11 & 255 == 44
    assert words[4] & 31 == 17
    assert read_json(package / "files/plan.json")["roles"]["chest"] == [21]
    for path, expected in assets.items():
        assert (path.read_bytes(), path.stat().st_mtime_ns) == expected


def test_preparation_preserves_source_and_gameplay_edits(prepared):
    project, package, _ = prepared
    row = next(r for r in read_json(project / "gameplay.json")["moves"] if r["motions"] == [44])
    source = project / row["script"]
    source.write_text(source.read_text() + "# keep my edit\n")
    gp = read_json(project / "gameplay.json")
    gp["moves"][0]["note"] = "keep my row"
    write_json(project / "gameplay.json", gp)
    before = {p: p.read_bytes() for p in project.rglob("*") if p.is_file()}
    project_build.prepare(project, package, [], TEMPLATE, root=ROOT)
    assert {p: p.read_bytes() for p in before} == before


def test_bad_source_does_not_publish_any_partial_overlay(prepared):
    project, package, _ = prepared
    rows = read_json(project / "gameplay.json")["moves"]
    first = project / rows[0]["script"]
    first.write_text("wait 7\nend\n")
    last = project / rows[-1]["script"]
    last.write_text("not_an_opcode\n")
    before = {p: p.read_bytes() for p in package.rglob("*") if p.is_file()}
    with pytest.raises(ValueError):
        project_build.rebuild(project)
    assert {p: p.read_bytes() for p in before} == before


def test_missing_script_is_not_silently_regenerated(prepared):
    project, package, _ = prepared
    row = read_json(project / "gameplay.json")["moves"][0]
    (project / row["script"]).unlink()
    with pytest.raises((FileNotFoundError, ValueError)):
        project_build.prepare(project, package, [], TEMPLATE, root=ROOT)


def test_shared_clip_conflict_is_rejected_before_publish(prepared):
    project, package, _ = prepared
    gp = read_json(project / "gameplay.json")
    next(r for r in gp["moves"] if r["motions"] == [44])["pick"]["clip"] = "Kick"
    write_json(project / "gameplay.json", gp)
    before = (package / "geno.json").read_bytes()
    with pytest.raises(ValueError, match="share"):
        project_build.rebuild(project)
    assert (package / "geno.json").read_bytes() == before


def test_generated_output_is_confined_to_build_directory(tmp_path):
    with pytest.raises(ValueError, match="_build"):
        project_build.prepare(tmp_path / "tracked", tmp_path / "package", [], TEMPLATE, root=ROOT)


def test_source_path_cannot_escape_project(prepared):
    project, package, _ = prepared
    manifest = read_json(project / "falcon_sources.json")
    manifest["overlays"][0]["source"] = "../../escape.genoasm"
    write_json(project / "falcon_sources.json", manifest)
    with pytest.raises(ValueError, match="path"):
        project_build.rebuild(project)


def test_local_package_has_every_state_and_every_overlay(tmp_path, codec):
    from tools.test_support import GAME
    package = Path(os.environ.get("GW_FALCON_PACKAGE", str(ROOT / "_build/falcon-look/geno-falcon")))
    if not (package / "geno.json").is_file():
        pytest.skip("local Geno Falcon package missing (set GW_FALCON_PACKAGE)")
    plan = read_json(package / "files/plan.json")
    states = metadata.load_states(GAME)
    assert [s["motion"] for s in states] == list(range(364))
    doc = read_json(package / "geno.json")
    scripts = {o["index"]: f"moves/{o['index']:03}.genoasm" for o in doc["fighters"][0]["subactions"]}
    rows = metadata.make_rows(plan, states, scripts, read_json(TEMPLATE / "gameplay.json")["moves"])
    assert len(rows) == 364
    by = {r["motions"][0]: r for r in rows}
    assert by[44]["pick"]["clip"] == "Attack11"
    assert by[347]["pick"]["clip"] == "SpecialN"
    roles, tokens = metadata.resolve_roles(plan, read_json(TEMPLATE / "role_map.json"))
    assert all(k in tokens for k in ("CHEST", "HEAD", "HIPS", "HAND_L", "HAND_R", "FOOT_L", "FOOT_R"))
    staged = tmp_path / "_build/falcon/mods/geno-falcon"
    shutil.copytree(package, staged)
    project = staged.parents[1] / "project"
    project_build.prepare(project, staged, states, TEMPLATE, root=ROOT)
    manifest = read_json(project / "falcon_sources.json")
    assert len(manifest["overlays"]) == len(doc["fighters"][0]["subactions"])
    for entry, overlay in zip(manifest["overlays"], doc["fighters"][0]["subactions"]):
        original = project_build.overlay_words(package, overlay)
        text = (project / entry["source"]).read_text()
        assert codec.assemble(text) == original, entry["index"]
    project_build.rebuild(project)
    built = read_json(staged / "geno.json")
    for before, after in zip(doc["fighters"][0]["subactions"], built["fighters"][0]["subactions"]):
        assert project_build.overlay_words(package, before) == project_build.overlay_words(staged, after)


def test_missing_package_recovers_from_seed_without_losing_edits(prepared, tmp_path, monkeypatch):
    project, package, _ = prepared
    seed = tmp_path / "_build/seed"
    shutil.copytree(package, seed)
    manifest = read_json(project / "falcon_sources.json")
    manifest["seed_package"] = str(seed)
    write_json(project / "falcon_sources.json", manifest)
    row = next(r for r in read_json(project / "gameplay.json")["moves"] if r["motions"] == [44])
    source = project / row["script"]
    source.write_text(source.read_text().replace("damage=8 ", "damage=15 "))
    saved = source.read_bytes()
    shutil.rmtree(package)
    def forbidden(*args, **kwargs):
        raise AssertionError("available seed should avoid extraction")
    monkeypatch.setattr(project_build.subprocess, "run", forbidden)
    assert project_build.rebuild(project) == "restaged"
    assert source.read_bytes() == saved
    assert (package / "files/body.dat").read_bytes() == b"synthetic costume"
    overlay = next(o for o in read_json(package / "geno.json")["fighters"][0]["subactions"] if o["index"] == 1)
    assert project_build.overlay_words(package, overlay)[1] & 1023 == 15


def test_build_cli_reports_mode(prepared, capsys):
    from falcon import build
    project, _, _ = prepared
    assert build.main(["--project", str(project)]) == 0
    import re
    assert re.search(r"BUILD_MODE: gameplay-only [0-9]+\.[0-9]+s", capsys.readouterr().out)


def test_launch_prepares_before_art_and_uses_staged_package(tmp_path, monkeypatch):
    import launch_falcon
    work = tmp_path / "workspace"
    project = work / "_build/geno-falcon-art/project"
    staged = work / "_build/geno-falcon-art/mods/geno-falcon"
    calls = []
    monkeypatch.setattr(launch_falcon.make_falcon_art, "root_dir", lambda: work)
    def prepare(argv):
        assert "--prepare" in argv
        calls.append("prepare")
        write_json(project / "workbench.json", {"art_blend": str(work / "falcon.blend")})
        return 0
    def art():
        assert calls == ["prepare"]
        assert Path(os.environ["GW_FALCON_PACKAGE"]) == staged
        calls.append("art")
        return 0
    def launch(argv, **kwargs):
        assert calls == ["prepare", "art"]
        assert argv[argv.index("--project") + 1] == str(project)
        assert "--row" in argv and argv[-1] == "jab1"
        calls.append("launch")
        return 0
    monkeypatch.setattr(launch_falcon.falcon_build, "main", prepare)
    monkeypatch.setattr(launch_falcon.make_falcon_art, "main", art)
    monkeypatch.setattr(launch_falcon.subprocess, "call", launch)
    monkeypatch.setenv("GW_FALCON_PACKAGE", "owner-seed")
    assert launch_falcon.main(["--row", "jab1"]) == 0
    assert calls == ["prepare", "art", "launch"]
    assert os.environ["GW_FALCON_PACKAGE"] == "owner-seed"


def test_aerial_specials_request_workbench_lift():
    assert metadata.move_tag("SpecialAirN") == "aerial"
    assert metadata.move_tag("SpecialAirLwEnd") == "aerial"
    assert metadata.move_tag("SpecialN") == "special"
