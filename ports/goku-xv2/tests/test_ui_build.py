"""The optional UI step belongs only to the full build, never Stage B."""
import importlib.util
from pathlib import Path
import sys
import types

import pytest

PORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT / 'tools'))
sys.path.insert(0, str(PORT.parents[1]))


def load_build():
    spec = importlib.util.spec_from_file_location('goku_build_ui', PORT / 'tools/build.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ui_is_off_by_default_and_propagates_failure(monkeypatch):
    build = load_build()
    calls = []
    monkeypatch.setattr(build, 'apply', lambda p, a: p)
    monkeypatch.setattr(build, 'finish_checks', lambda *a, **kw: 0)
    audit = types.ModuleType('audit_gameplay')
    audit.audit = lambda *a, **kw: []
    monkeypatch.setitem(sys.modules, 'audit_gameplay', audit)
    monkeypatch.setattr(build, 'render_presentation', lambda *a: calls.append(a) or 9)
    args = ['--package', str(build.ROOT / '_build/ui-test'), '--art-build', str(build.ROOT / '_build/ui-test/build')]
    assert build.main(args) == 0
    assert calls == []
    assert build.main(args + ['--ui']) == 9
    assert len(calls) == 1
    assert calls[0][0] == build.ROOT / '_build/ui-test'


def test_explicit_gameplay_only_with_ui_is_rejected():
    build = load_build()
    with pytest.raises(SystemExit) as exc:
        build.main(['--gameplay-only', '--ui', '--fighter', 'unused.json'])
    assert exc.value.code == 2


def test_auto_ui_forces_full_artist_build(monkeypatch):
    build = load_build()
    monkeypatch.setattr(build, 'stage_a_stale', lambda *a: None)
    monkeypatch.setattr(build, 'generated', lambda p: p)
    calls = []
    pipeline = types.ModuleType('tools.geno.artist.pipeline')
    pipeline.build = lambda *a: (calls.append(a) or 7, None)
    import tools.geno.artist as pkg
    monkeypatch.setattr(pkg, 'pipeline', pipeline, raising=False)
    monkeypatch.setitem(sys.modules, 'tools.geno.artist.pipeline', pipeline)
    assert build.main(['--auto', '--ui', '--fighter', 'unused.json']) == 7
    assert len(calls) == 1


def test_gameplay_reapply_preserves_completed_csp_art(tmp_path):
    build = load_build()
    (tmp_path / 'files').mkdir()
    presentation = {'icon': 'GnUi_goku_icon.gxtex', 'portrait': ['GnUi_goku_portrait.gxtex'],
                    'stock': ['GnUi_goku_stock.gxtex'], 'results': ['GnUi_goku_results.gxtex'], 'emblem': 'OriginalEmblem.gxtex'}
    for value in presentation.values():
        for name in value if isinstance(value, list) else [value]:
            (tmp_path / 'files' / name).write_bytes(b'synthetic existing asset')
    fighter = {'presentation': presentation}
    build.write_presentation(tmp_path, fighter)
    assert fighter['presentation'] == presentation
