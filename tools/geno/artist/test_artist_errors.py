"""Artist error regressions: synthetic inputs, no Blender, game or disc required."""
import json
import os
import shlex
import struct
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tools.geno.artist import model, pipeline, validate
from tools.geno.artist.__main__ import main


def project(tmp_path, *, blend=False, glb=False):
    cfg = tmp_path / "fighter.json"
    art = {"glb": "art/fighter.glb"}
    if blend:
        art["blend"] = "fighter.blend"
        (tmp_path / "fighter.blend").write_bytes(b"synthetic blend placeholder")
    cfg.write_text(json.dumps({"key": "test-fighter", "art": art}), encoding="utf-8")
    if glb:
        data = json.dumps({"asset": {"version": "2.0"}, "nodes": [], "meshes": [], "animations": []}).encode()
        data += b" " * (-len(data) % 4)
        dest = tmp_path / art["glb"]
        dest.parent.mkdir()
        dest.write_bytes(b"glTF" + struct.pack("<II", 2, 28 + len(data))
                         + struct.pack("<II", len(data), 0x4E4F534A) + data
                         + struct.pack("<II", 0, 0x004E4942))
    return cfg


def test_validate_directory_finds_fighter_json(tmp_path):
    cfg = project(tmp_path, glb=True)
    file_report, _ = validate.validate(cfg, measure=False)
    directory_report, fighter = validate.validate(tmp_path, measure=False)
    assert fighter is not None
    assert fighter.cfg_path == str(cfg)
    assert directory_report.items == file_report.items
    assert not any(i["code"] == "LOAD" for i in directory_report.items)


def test_empty_directory_names_the_missing_config(tmp_path):
    report, _ = validate.validate(tmp_path, measure=False)
    finding = report.items[0]
    assert "fighter.json" in finding["message"]
    assert "Permission denied" not in finding["message"]
    assert finding["fix"].strip()


def test_new_starter_validate_gives_runnable_build_command(tmp_path):
    dest = tmp_path / "a fighter with spaces"

    def starter(cmd, **kwargs):
        Path(cmd[cmd.index("--out") + 1]).write_bytes(b"synthetic blend placeholder")
        return subprocess.CompletedProcess(cmd, 0, "GENO STARTER ready\n", "")

    with patch.object(pipeline, "blender_exe", return_value="blender"), patch.object(pipeline.subprocess, "run", side_effect=starter):
        pipeline.new_character(dest, "test-fighter", "Test fighter", log=lambda _: None)
    report, _ = validate.validate(dest, measure=False)
    finding = report.items[0]
    assert finding["code"] == "LOAD"
    assert finding["fix"].startswith("run: python -m tools.geno.artist build ")
    assert shlex.split(finding["fix"][5:]) == ["python", "-m", "tools.geno.artist", "build", (dest / "fighter.json").as_posix()]


def test_missing_glb_without_blend_does_not_prescribe_build(tmp_path):
    report, _ = validate.validate(project(tmp_path), measure=False)
    assert "glTF Binary" in report.items[0]["fix"]
    assert "run: python" not in report.items[0]["fix"]


def test_unreadable_json_does_not_prescribe_export(tmp_path):
    cfg = tmp_path / "fighter.json"
    cfg.write_text("{invalid", encoding="utf-8")
    report, _ = validate.validate(cfg, measure=False)
    assert "fighter.json" in report.items[0]["fix"]
    assert "run: python" not in report.items[0]["fix"]


@pytest.mark.parametrize("returncode", [1, 7])
def test_export_failure_surfaces_blender_stderr(tmp_path, returncode):
    cfg = project(tmp_path, blend=True)
    logs = []
    result = subprocess.CompletedProcess([], returncode, "GENO BLOCKER TEST rig: bad | fix: repair\n", "Traceback: exporter exploded\n")
    with patch.object(pipeline, "blender_exe", return_value="blender"), patch.object(pipeline.subprocess, "run", return_value=result):
        assert pipeline.export_from_blend(cfg, log=logs.append) is False
    text = "\n".join(logs)
    assert "GENO BLOCKER" in text
    assert "Traceback: exporter exploded" in text
    assert str(returncode) in text


def test_export_zero_exit_without_output_is_a_failure(tmp_path):
    cfg = project(tmp_path, blend=True)
    logs = []
    result = subprocess.CompletedProcess([], 0, "export skipped\n", "export warning\n")
    with patch.object(pipeline, "blender_exe", return_value="blender"), patch.object(pipeline.subprocess, "run", return_value=result):
        assert pipeline.export_from_blend(cfg, log=logs.append) is False
    assert "art/fighter.glb" in "\n".join(logs).replace("\\", "/")
    assert "export warning" in "\n".join(logs)


def test_blender_launch_oserror_is_actionable(tmp_path):
    cfg = project(tmp_path, blend=True)
    with patch.object(pipeline, "blender_exe", return_value="missing-blender"), patch.object(pipeline.subprocess, "run", side_effect=OSError("cannot execute")):
        with pytest.raises(model.ArtistError, match="GW_BLENDER"):
            pipeline.export_from_blend(cfg)


def test_starter_failure_retains_stderr_even_after_long_stdout(tmp_path):
    result = subprocess.CompletedProcess([], 1, "verbose output\n" * 400, "starter traceback\n")
    with patch.object(pipeline, "blender_exe", return_value="blender"), patch.object(pipeline.subprocess, "run", return_value=result):
        with pytest.raises(model.ArtistError, match="starter traceback"):
            pipeline.new_character(tmp_path, "test-fighter", "Test")


def test_cli_artist_error_prints_message_without_traceback(capsys):
    with patch.object(pipeline, "new_character", side_effect=model.ArtistError("Blender stderr: fixture failure")):
        assert main(["new", "unused", "--key", "test-fighter"]) == 1
    output = capsys.readouterr()
    assert "fixture failure" in output.err
    assert "Traceback" not in output.err


def test_all_emitted_findings_have_nonempty_fixes(tmp_path):
    cfg = project(tmp_path, glb=True)
    report, _ = validate.validate(cfg, measure=False)
    assert report.items
    assert all(isinstance(i["fix"], str) and i["fix"].strip() for i in report.items)
    assert "No action needed." not in validate.format_report(report, verbose=True)


@pytest.mark.parametrize("severity", [validate.B, validate.W])
def test_missing_actionable_fix_is_rejected(severity):
    with pytest.raises(ValueError, match="fix"):
        validate.Report().add(severity, "FIXTURE", "fixture", "problem")


def test_material_warnings_give_specific_repairs(tmp_path):
    report = validate.Report()
    fighter = SimpleNamespace(g={"meshes": [{"primitives": [{}]}], "materials": [{}, {}]}, cfg={}, costumes=[])
    validate._materials(fighter, report)
    fixes = {i["code"]: i["fix"] for i in report.items}
    assert "material" in fixes["NO_MATERIAL"].lower()
    assert "costumes" in fixes["MULTI_MATERIAL"]


def test_hurtbox_blockers_give_specific_repairs():
    report = validate.Report()
    fighter = SimpleNamespace(hurtboxes_given=[{"id": "body", "bone": "hips", "radius": 0, "height": "bad"}], bone_by_name={"hips": object()}, hurtbox_src="fighter.json")
    validate._hurt(fighter, report)
    fixes = {i["code"]: i["fix"] for i in report.items}
    assert "radius" in fixes["HURTBOX_RADIUS"]
    assert "high" in fixes["HURTBOX_HEIGHT"]


def test_placeholder_warning_explains_how_to_replace_it():
    report = validate.Report()
    fighter = SimpleNamespace(rows=[{"status": "placeholder", "row": "Attack11"}], served={"Wait": "Wait"}, legacy=None, padded=[])
    validate._rows(fighter, report)
    finding = next(i for i in report.items if i["code"] == "PLACEHOLDERS")
    assert "clip" in finding["fix"].lower()
    assert "build report" in finding["fix"].lower()


def test_artist_blender_uses_shared_local_config(tmp_path, monkeypatch):
    exe = tmp_path / "author-tools/blender.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"fixture")
    cache = tmp_path / "_build/tools.json"
    cache.parent.mkdir()
    cache.write_text(json.dumps({"schema": 1, "paths": {"GW_BLENDER": "author-tools/blender.exe"}}), encoding="utf-8")
    monkeypatch.setattr(pipeline.os, "environ", {"GW_ROOT": str(tmp_path), "PATH": ""})
    assert pipeline.blender_exe() == str(exe)


def test_export_command_makes_python_failures_change_exit_status(tmp_path):
    cfg = project(tmp_path, blend=True)

    def export(cmd, **kwargs):
        assert cmd[cmd.index("--python-exit-code") + 1] == "1"
        assert cmd.index("--python-exit-code") < cmd.index("--python")
        output = Path(cmd[cmd.index("--out") + 1])
        output.parent.mkdir()
        output.write_bytes(b"synthetic output")
        return subprocess.CompletedProcess(cmd, 0, "GENO EXPORTED fixture\n", "")

    with patch.object(pipeline, "blender_exe", return_value="blender"), patch.object(pipeline.subprocess, "run", side_effect=export):
        assert pipeline.export_from_blend(cfg, log=lambda _: None) is True


def test_blender_preflight_findings_follow_same_fix_contract(monkeypatch):
    import importlib.util
    import sys
    from types import ModuleType

    monkeypatch.setitem(sys.modules, "bpy", ModuleType("bpy"))
    path = Path(pipeline.__file__).parent / "blender/export_fighter.py"
    spec = importlib.util.spec_from_file_location("error_test_exporter", path)
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    exporter.add("INFO", "FIXTURE", "fixture", "count")
    assert exporter.OUT[0][-1].strip()
    for severity in ("BLOCKER", "WARNING"):
        with pytest.raises(ValueError, match="fix"):
            exporter.add(severity, "FIXTURE", "fixture", "problem")
