"""The launch scripts and add-on helper consume the same local tool config."""
import importlib.util
import json
from pathlib import Path
import sys

import launch


HERE = Path(__file__).resolve().parents[1]


def config(tmp_path):
    paths = {"GW_BLENDER": "tools/blender.exe", "GW_BLENDER_351": "tools/blender351.exe", "GW_LAUNCHER": "tools/launcher.exe", "GW_ENGINE_EXE": "tools/engine.exe", "GW_QT_BIN": "qt/bin", "GW_ISO_VANILLA": "discs/vanilla.iso"}
    path = tmp_path / "_build/tools.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"schema": 1, "paths": paths}), encoding="utf-8")
    return paths


def test_addon_discovery_and_serve_environment_share_config(tmp_path, monkeypatch):
    config(tmp_path)
    monkeypatch.setattr(launch.os, "environ", {"GW_ROOT": str(tmp_path), "PATH": ""})
    assert launch.find_blender() == str(tmp_path / "tools/blender.exe")
    assert launch.find_launcher() == str(tmp_path / "tools/launcher.exe")
    argv, env = launch.serve_launch("launcher", "project")
    assert argv[argv.index("--engine-exe") + 1] == str(tmp_path / "tools/engine.exe")
    assert env["MELEE_ISO"] == str(tmp_path / "discs/vanilla.iso")
    assert env["PATH"].startswith(str(tmp_path / "qt/bin"))


def test_falcon_art_uses_same_root_and_disc(tmp_path, monkeypatch):
    config(tmp_path)
    monkeypatch.setenv("GW_ROOT", str(tmp_path))
    monkeypatch.delenv("GW_ISO_VANILLA", raising=False)
    spec = importlib.util.spec_from_file_location("config_test_falcon_art", HERE / "falcon/make_falcon_art.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.root_dir() == tmp_path
    assert module.iso_path(tmp_path) == str(tmp_path / "discs/vanilla.iso")


def test_goku_missing_paths_report_every_required_item(tmp_path, monkeypatch, capsys):
    config(tmp_path)
    monkeypatch.setattr(launch.os, "environ", {"GW_ROOT": str(tmp_path), "PATH": ""})
    monkeypatch.setattr(sys, "argv", ["launch_goku.py"])
    spec = importlib.util.spec_from_file_location("config_test_launch_goku", HERE / "launch_goku.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == 2
    output = capsys.readouterr().out
    for label in ("Blender", "launcher", "engine exe", "project", "mods dir", "art", "disc image"):
        assert "missing " + label in output


def test_fresh_script_import_finds_its_resolver_when_gw_root_is_other_checkout(tmp_path):
    import os
    import shutil
    import subprocess

    source = tmp_path / "source"
    addon = source / "tools/blender/geno_workbench"
    addon.mkdir(parents=True)
    shared = tmp_path / "shared"
    shared.mkdir()
    config(shared)
    for name in ("launch.py", "client.py"):
        shutil.copy2(HERE / name, addon / name)
    resolver = source / "tools/port/tools_config.py"
    resolver.parent.mkdir()
    shutil.copy2(HERE.parents[2] / "tools/port/tools_config.py", resolver)
    script = addon / "probe.py"
    script.write_text('import launch\nprint(launch.find_blender())\n', encoding="utf-8")
    env = {"GW_ROOT": str(shared), "PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}
    if "SystemRoot" in os.environ:
        env["SystemRoot"] = os.environ["SystemRoot"]
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path, env=env,
                            capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(shared / "tools/blender.exe")


def test_special_rows_resolve_by_input_name():
    import rigmap
    names = ["jab1", "dair", "side_b (Rush)", "up_b (Flight)", "RushCombo (special)"]
    assert rigmap.resolve_row_name(names, "side_b") == "side_b (Rush)"
    assert rigmap.resolve_row_name(names, "side_b (Rush)") == "side_b (Rush)"
    assert rigmap.resolve_row_name(names, "dair") == "dair"
    assert rigmap.resolve_row_name(names, "RushCombo") == "RushCombo (special)"
    assert rigmap.resolve_row_name(names, "nope") == "nope"
