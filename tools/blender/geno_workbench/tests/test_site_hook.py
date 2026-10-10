import importlib.util
import sys
from pathlib import Path

_init = Path(__file__).resolve().parents[1] / "__init__.py"


def _load():
    spec = importlib.util.spec_from_file_location("gw_pkg_init", _init)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gw_site_added_to_path(tmp_path, monkeypatch):
    mod = _load()
    monkeypatch.setenv("GW_SITE", str(tmp_path))
    monkeypatch.setattr(sys, "path", list(sys.path))
    assert mod.add_site_dirs() == [str(tmp_path)]
    assert sys.path[0] == str(tmp_path)
    assert mod.add_site_dirs() == []
