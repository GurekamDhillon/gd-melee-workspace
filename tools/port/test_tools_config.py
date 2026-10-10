"""Shared path configuration, using temporary files and no external processes."""
import json
from pathlib import Path

import pytest

from tools.port import tools_config as C


KEYS = ("GW_BLENDER", "GW_BLENDER_351", "GW_LAUNCHER", "GW_ENGINE_EXE", "GW_QT_BIN", "GW_ISO_VANILLA", "GW_ISO_AKANEIA", "GW_ISO_ACE")


def cache(root, paths):
    path = root / "_build/tools.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"schema": 1, "paths": paths}), encoding="utf-8")
    return path


def test_precedence_environment_then_dotenv_then_cache(tmp_path):
    cache(tmp_path, {"GW_BLENDER": "cache/blender.exe", "GW_LAUNCHER": "cache/launcher.exe", "GW_ENGINE_EXE": "cache/engine.exe"})
    (tmp_path / ".env").write_text('export GW_BLENDER="dotenv/blender.exe"\nGW_LAUNCHER="dotenv/launcher.exe"\n', encoding="utf-8")
    paths = C.load_config(tmp_path, env={"GW_BLENDER": "env/blender.exe", "PATH": ""}, detect=False)
    assert paths["GW_BLENDER"] == str(tmp_path / "env/blender.exe")
    assert paths["GW_LAUNCHER"] == str(tmp_path / "dotenv/launcher.exe")
    assert paths["GW_ENGINE_EXE"] == str(tmp_path / "cache/engine.exe")
    assert paths["GW_ROOT"] == str(tmp_path)


def test_expansion_quotes_comments_and_spaces(tmp_path):
    (tmp_path / ".env").write_text('export GW_BLENDER="$GW_ROOT/Blender Tools/blender.exe" # author tool\nGW_ISO_VANILLA=discs/vanilla.iso # local only\n', encoding="utf-8")
    paths = C.load_config(tmp_path, env={"PATH": ""}, detect=False)
    assert paths["GW_BLENDER"] == str(tmp_path / "Blender Tools/blender.exe")
    assert paths["GW_ISO_VANILLA"] == str(tmp_path / "discs/vanilla.iso")


def test_legacy_blender_alias_does_not_override_canonical_at_same_layer(tmp_path):
    paths = C.load_config(tmp_path, env={"GW_BLENDER": "new/blender.exe", "BLENDER": "old/blender.exe", "PATH": ""}, detect=False)
    assert paths["GW_BLENDER"] == str(tmp_path / "new/blender.exe")


def test_legacy_environment_alias_beats_cached_canonical(tmp_path):
    cache(tmp_path, {"GW_BLENDER": "cache/blender.exe"})
    paths = C.load_config(tmp_path, env={"BLENDER": "old/blender.exe", "BLENDER_351": "pinned/blender.exe", "PATH": ""}, detect=False)
    assert paths["GW_BLENDER"] == str(tmp_path / "old/blender.exe")
    assert paths["GW_BLENDER_351"] == str(tmp_path / "pinned/blender.exe")


def test_empty_setting_suppresses_cached_or_detected_tool(tmp_path):
    cache(tmp_path, {"GW_BLENDER": "cache/blender.exe"})
    paths = C.load_config(tmp_path, env={"GW_BLENDER": "", "PATH": ""}, detect=True)
    assert paths["GW_BLENDER"] == ""


def test_config_override_and_relative_paths_are_based_on_workspace(tmp_path):
    custom = tmp_path / "local-config.json"
    custom.write_text(json.dumps({"schema": 1, "paths": {"GW_ISO_ACE": "discs/ace.iso"}}), encoding="utf-8")
    paths = C.load_config(tmp_path, env={"GW_TOOLS_CONFIG": "local-config.json", "PATH": ""}, detect=False)
    assert paths["GW_ISO_ACE"] == str(tmp_path / "discs/ace.iso")


@pytest.mark.parametrize("content", ['{bad', '{"schema": 2, "paths": {}}', '{"schema": 1, "paths": []}', '{"schema": 1, "paths": {"GW_BLENDER": 12}}'])
def test_bad_config_fails_with_actionable_file_message(tmp_path, content):
    path = tmp_path / "_build/tools.json"
    path.parent.mkdir()
    path.write_text(content, encoding="utf-8")
    with pytest.raises(C.ToolsConfigError, match="tools.json"):
        C.load_config(tmp_path, env={"PATH": ""}, detect=False)


def test_detect_standard_build_outputs_and_pinned_blender(tmp_path):
    files = {"GW_LAUNCHER": "_build/wb-win/gd-melee-launcher.exe", "GW_ENGINE_EXE": "_build/wb-goku/engine/melee-pc.exe", "GW_BLENDER_351": "_build/tools/blender-3.5.1-windows-x64/blender.exe"}
    for value in files.values():
        path = tmp_path / value
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    paths = C.load_config(tmp_path, env={"PATH": ""}, detect=True)
    for key, value in files.items():
        assert paths[key] == str(tmp_path / value)


def test_detect_uses_blender_on_supplied_path(tmp_path, monkeypatch):
    exe = tmp_path / "bin/blender.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"fixture")
    monkeypatch.setattr(C.shutil, "which", lambda name, path=None: str(exe) if name == "blender" and path == "fixture-path" else None)
    paths = C.load_config(tmp_path, env={"PATH": "fixture-path"}, detect=True)
    assert paths["GW_BLENDER"] == str(exe)
    assert not paths["GW_BLENDER_351"]  # modern Blender is never used as the pinned exporter


def test_check_lists_all_missing_tools_and_bad_qt_kind(tmp_path):
    paths = {key: "" for key in KEYS}
    paths["GW_QT_BIN"] = str(tmp_path / "qt-file")
    Path(paths["GW_QT_BIN"]).write_bytes(b"fixture")
    messages = C.missing_tools(paths)
    assert len(messages) == len(KEYS)
    assert all(any(key in message for message in messages) for key in KEYS)
    assert any("GW_QT_BIN" in message and "directory" in message for message in messages)


def test_detect_cli_writes_only_tool_paths_and_check_reports_all(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(C.os, "environ", {"PATH": "", "PRIVATE_TOKEN": "never write this"})
    assert C.main(["--root", str(tmp_path), "--detect"]) == 0
    document = json.loads((tmp_path / "_build/tools.json").read_text(encoding="utf-8"))
    assert document["schema"] == 1
    assert not document["paths"]  # unresolved discoveries must remain discoverable later
    assert "PRIVATE_TOKEN" not in json.dumps(document)
    assert C.main(["--root", str(tmp_path), "--check"]) == 1
    output = capsys.readouterr().out
    assert all(key in output for key in KEYS)


def test_short_qt_cmake_path_does_not_crash_discovery(tmp_path):
    paths = C.load_config(tmp_path, env={"Qt6_DIR": "Qt6", "PATH": ""}, detect=True)
    assert paths["GW_QT_BIN"] == ""


def test_explicit_missing_config_is_an_error(tmp_path):
    with pytest.raises(C.ToolsConfigError, match="missing.json"):
        C.load_config(tmp_path, env={"GW_TOOLS_CONFIG": "missing.json", "PATH": ""}, detect=False)


def test_detect_does_not_cache_unresolved_tools_and_finds_later_install(tmp_path, monkeypatch):
    monkeypatch.setattr(C.os, "environ", {"PATH": "fixture-path"})
    found = []
    monkeypatch.setattr(C.shutil, "which", lambda name, path=None: found[0] if found and name == "blender" else None)
    assert C.main(["--root", str(tmp_path), "--detect"]) == 0
    assert "GW_BLENDER" not in json.loads((tmp_path / "_build/tools.json").read_text(encoding="utf-8"))["paths"]
    exe = tmp_path / "bin/blender.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"fixture")
    found.append(str(exe))
    assert C.main(["--root", str(tmp_path), "--detect"]) == 0
    paths = json.loads((tmp_path / "_build/tools.json").read_text(encoding="utf-8"))["paths"]
    assert paths["GW_BLENDER"] == str(exe)


def test_detect_preserves_explicit_empty_settings_from_every_layer(tmp_path, monkeypatch):
    cache(tmp_path, {"GW_ISO_ACE": ""})
    (tmp_path / ".env").write_text("GW_ISO_AKANEIA=\n", encoding="utf-8")
    monkeypatch.setattr(C.os, "environ", {"PATH": "", "BLENDER_351": ""})
    assert C.main(["--root", str(tmp_path), "--detect"]) == 0
    paths = json.loads((tmp_path / "_build/tools.json").read_text(encoding="utf-8"))["paths"]
    assert paths == {"GW_ISO_ACE": "", "GW_ISO_AKANEIA": "", "GW_BLENDER_351": ""}


def test_modern_blender_discovery_does_not_choose_only_legacy_install(tmp_path):
    program_files = tmp_path / "Program Files"
    legacy = program_files / "Blender Foundation/Blender 3.5.1/blender.exe"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"fixture")
    paths = C.load_config(tmp_path, env={"PATH": "", "PROGRAMFILES": str(program_files)}, detect=True)
    assert paths["GW_BLENDER"] == ""
    assert paths["GW_BLENDER_351"] == str(legacy)


@pytest.fixture
def steam_libraries(tmp_path):
    steam = tmp_path / "Program Files (x86)/Steam"
    libraries = [steam, tmp_path / "SteamLibrary é", tmp_path / "SteamGames"]
    vdf = steam / "steamapps/libraryfolders.vdf"
    vdf.parent.mkdir(parents=True)
    entries = []
    for index, library in enumerate(libraries):
        escaped_path = str(library).replace("\\", "\\\\")
        entries.append(
            f'    "{index}"\n    {{\n'
            f'        "path" "{escaped_path}"\n'
            '        "label" ""\n'
            '        "contentid" "123456789"\n'
            '        "totalsize" "0"\n'
            '        "apps"\n        {\n            "365670" "1024"\n        }\n'
            '    }\n'
        )
    vdf.write_text('"libraryfolders"\n{\n' + "".join(entries) + '}\n', encoding="utf-8")
    return steam.parent, libraries, vdf


@pytest.mark.parametrize("env_key", ["PROGRAMFILES(X86)", "ProgramFiles(x86)"])
@pytest.mark.parametrize("library_index", [0, 1, 2])
def test_detect_blender_in_each_steam_library(tmp_path, steam_libraries, env_key, library_index):
    program_files, libraries, _ = steam_libraries
    exe = libraries[library_index] / "steamapps/common/Blender/blender.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"fixture")
    paths = C.load_config(tmp_path, env={"PATH": "", env_key: str(program_files)})
    assert paths["GW_BLENDER"] == str(exe.resolve())
    assert paths["GW_BLENDER_351"] == ""  # Steam Blender is never the pinned exporter.


@pytest.mark.parametrize("override", ["custom/blender.exe", ""])
def test_explicit_blender_override_wins_over_steam_libraries(tmp_path, steam_libraries, override):
    program_files, libraries, _ = steam_libraries
    exe = libraries[1] / "steamapps/common/Blender/blender.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"fixture")
    paths = C.load_config(tmp_path, env={
        "PATH": "", "PROGRAMFILES(X86)": str(program_files), "GW_BLENDER": override,
    })
    assert paths["GW_BLENDER"] == (str(tmp_path / override) if override else "")


@pytest.mark.parametrize("vdf_state", ["missing", "invalid_utf8"])
def test_steam_vdf_failure_keeps_default_library_fallback(tmp_path, steam_libraries, vdf_state):
    program_files, libraries, vdf = steam_libraries
    if vdf_state == "missing":
        vdf.unlink()
    else:
        vdf.write_bytes(b"\xff\xfe\xff")
    exe = libraries[0] / "steamapps/common/Blender/blender.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"fixture")
    paths = C.load_config(tmp_path, env={"PATH": "", "PROGRAMFILES(X86)": str(program_files)})
    assert paths["GW_BLENDER"] == str(exe.resolve())


def test_detect_cli_caches_blender_from_secondary_steam_library(tmp_path, steam_libraries, monkeypatch):
    program_files, libraries, _ = steam_libraries
    exe = libraries[1] / "steamapps/common/Blender/blender.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"fixture")
    monkeypatch.setattr(C.os, "environ", {"PATH": "", "PROGRAMFILES(X86)": str(program_files)})
    assert C.main(["--root", str(tmp_path), "--detect"]) == 0
    paths = json.loads((tmp_path / "_build/tools.json").read_text(encoding="utf-8"))["paths"]
    assert paths["GW_BLENDER"] == str(exe.resolve())
