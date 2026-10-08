"""Offline checks of the environment builders; never import or launch drivers."""
import ast
import os
from pathlib import Path
import pytest

TOOLS = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("driver", ["netplay/np_drive.py", "xplat/envoy_set.py", "xplat/pair.py", "xplat/net_pair.py"])
@pytest.mark.parametrize("inherited,bind,expected", [({}, None, "127.0.0.1"), ({"MELEE_NETPLAY_BIND": "192.0.2.1"}, None, "192.0.2.1"), ({}, "0.0.0.0", "0.0.0.0")])
def test_client_environment(driver, inherited, bind, expected):
    tree = ast.parse((TOOLS / driver).read_text(encoding="utf-8"))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "client_environment"]
    assert functions, "driver needs a testable client environment builder"
    namespace = {"os": os}
    exec(compile(ast.Module(body=functions, type_ignores=[]), driver, "exec"), namespace)
    before = inherited.copy()
    env = namespace["client_environment"](inherited, bind)
    assert env["MELEE_NETPLAY_BIND"] == expected
    assert inherited == before

@pytest.mark.parametrize("override", [None, "0.0.0.0"])
def test_np_drive_passes_bind_to_both_clients_and_local_server(monkeypatch, override):
    import importlib.util
    import sys
    from types import SimpleNamespace
    spec = importlib.util.spec_from_file_location("np_drive", TOOLS / "netplay/np_drive.py")
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    commands = []
    class StopBeforeConsole(Exception):
        pass
    def stop(*args):
        raise StopBeforeConsole
    monkeypatch.delenv("MELEE_NETPLAY_BIND", raising=False)
    if override:
        monkeypatch.setenv("MELEE_NETPLAY_BIND", override)
    monkeypatch.setattr(sys, "argv", ["np_drive", "--local-server"])
    monkeypatch.setattr(driver.subprocess, "Popen", lambda cmd: commands.append(cmd) or SimpleNamespace(terminate=lambda: None))
    monkeypatch.setattr(driver.subprocess, "run", lambda cmd, **kw: commands.append(cmd))
    monkeypatch.setattr(driver.atexit, "register", lambda *args: None)
    monkeypatch.setattr(driver, "Console", stop)
    with pytest.raises(StopBeforeConsole):
        driver.main()
    bind = override or "127.0.0.1"
    assert commands[0][commands[0].index("--bind") + 1] == bind
    assert commands[1][-1].count("MELEE_NETPLAY_BIND='" + bind + "'") == 2
