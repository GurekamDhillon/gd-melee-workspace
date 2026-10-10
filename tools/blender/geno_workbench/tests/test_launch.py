import launch as L


def test_parse_serve_line():
    assert L.parse_serve_line("WB_SERVE port=51877") == 51877
    assert L.parse_serve_line("garbage") is None


def test_serve_argv():
    a = L.serve_argv("gd.exe", "proj", engine_exe="melee.exe")
    assert a[0] == "gd.exe" and "--serve" in a and a[a.index("--project") + 1] == "proj"
    assert a[a.index("--engine-exe") + 1] == "melee.exe" and "--engine-windowed" not in a
    assert "--engine-windowed" in L.serve_argv("gd.exe", "p", headless=False)


def test_blender_argv():
    a = L.blender_argv("blender", "/x/addon", "proj", 1234)
    assert a[:3] == ["blender", "--python", "/x/addon/bootstrap.py"] and a[-4:] == ["--project", "proj", "--port", "1234"] and "--" in a


def test_find_blender_order(tmp_path):
    assert L.find_blender({"GW_BLENDER": "B"}, settings_value="S", root=tmp_path) == "S"
    assert L.find_blender({"GW_BLENDER": "B"}, root=tmp_path) == str(tmp_path / "B")
    assert L.find_blender({"PATH": ""}, root=tmp_path) is None


def test_start_serve_reads_port(tmp_path):
    s = tmp_path / "s.py"
    s.write_text("import time,sys\nprint('hello', flush=True)\nprint('WB_SERVE port=4321', flush=True)\ntime.sleep(5)\n")
    p, port = L.start_serve(["python", str(s)], timeout=10)
    try:
        assert port == 4321
    finally:
        p.kill()


def test_serve_launch_matches_launch_goku(tmp_path):
    eng = tmp_path / "work" / "engine" / "melee-pc.exe"
    argv, env = L.serve_launch("gd.exe", "proj", engine_exe=str(eng), mods_dir="M", iso="D.iso", env={"PATH": "p"}, root=tmp_path)
    assert argv[argv.index("--engine-exe") + 1] == str(eng)
    assert argv[argv.index("--engine-work-dir") + 1] == str(eng.parent)
    assert argv[argv.index("--mods-dir") + 1] == "M"
    assert argv[argv.index("--wb-dir") + 1] == str(tmp_path / "work" / "payloads")
    assert env["MELEE_ISO"] == "D.iso" and env["MELEE_NETPLAY_BIND"] == "127.0.0.1"


def test_serve_settings_env_fallback(tmp_path):
    e = {"GW_ENGINE_EXE": "E", "GW_MODS_DIR": "M", "GW_ISO_VANILLA": "I"}
    assert L.serve_settings(env=e, root=tmp_path) == {"engine_exe": str(tmp_path / "E"), "mods_dir": "M", "iso": str(tmp_path / "I")}
    assert L.serve_settings("x", "y", "z", env=e, root=tmp_path) == {"engine_exe": "x", "mods_dir": "y", "iso": "z"}
    assert L.serve_settings(env={}, root=tmp_path)["iso"] == ""
    argv, env = L.serve_launch("gd.exe", "proj", env={"GW_QT_BIN": "Q", "PATH": "p"}, root=tmp_path)
    assert "--engine-exe" not in argv and env["PATH"].startswith(str(tmp_path / "Q"))
