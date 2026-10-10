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
    assert L.find_blender({"GW_BLENDER": "B"}, settings_value="S") == "S"
    assert L.find_blender({"GW_BLENDER": "B"}) == "B"
    assert L.find_blender({"PATH": ""}) is None


def test_start_serve_reads_port(tmp_path):
    s = tmp_path / "s.py"
    s.write_text("import time,sys\nprint('hello', flush=True)\nprint('WB_SERVE port=4321', flush=True)\ntime.sleep(5)\n")
    p, port = L.start_serve(["python", str(s)], timeout=10)
    try:
        assert port == 4321
    finally:
        p.kill()
