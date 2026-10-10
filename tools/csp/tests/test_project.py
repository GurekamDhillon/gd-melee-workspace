"""Workbench paths, animation selection and costume input validation; no Blender."""
import json
from pathlib import Path

import pytest

from tools.csp.project import load_project, generated_path


@pytest.fixture
def project(tmp_path):
    root = tmp_path
    source = root / 'ports/test'
    art = root / '_build/author'
    package = root / '_build/mods/test'
    source.mkdir(parents=True)
    art.mkdir(parents=True)
    (package / 'files').mkdir(parents=True)
    (art / 'fighter.json').write_text(json.dumps({'art': {'glb': 'fighter.glb'}, 'costumes': [{'name': 'default'}]}))
    (art / 'fighter.glb').write_bytes(b'glb fixture')
    (art / 'fighter.blend').write_bytes(b'BLENDER-v502' + bytes(32))
    (package / 'geno.json').write_text(json.dumps({'geno': 10, 'fighters': [{
        'define': {'key': 'test', 'base': 'none'},
        'fighter': {'costumes': [{'name': 'Default'}]},
    }]}))
    (package / 'files/plan.json').write_text(json.dumps({'row_clips': ['Wait', 'AttackAirLw']}))
    (source / 'moves').mkdir()
    (source / 'moves/dair.json').write_text(json.dumps({'pick': {'clip': 'AttackAirLw'}}))
    (source / 'workbench.json').write_text(json.dumps({
        'schema': 'workbench/1', 'mod_id': 'test',
        'plan_abs': '_build/mods/test/files/plan.json', 'art_blend': '_build/author/fighter.blend',
        'rebuild': ['python', 'build.py', '--fighter', '_build/author/fighter.json'], 'moves_dir': 'moves',
    }))
    return root, source, package


def test_newer_blend_uses_local_glb_and_named_row(project):
    root, source, package = project
    job = load_project(source, root=root, pose='dair:8')
    assert job['package'] == str(package.resolve())
    assert job['art'].endswith('fighter.glb')
    assert job['action'] == 'AttackAirLw'
    assert job['frame'] == 8
    assert job['costumes'][0]['index'] == 0


def test_numeric_row_and_package_override(project):
    root, source, package = project
    other = root / '_build/other'
    import shutil
    shutil.copytree(package, other)
    job = load_project(source, root=root, package=other, pose='1:3')
    assert job['package'] == str(other.resolve())
    assert job['action'] == 'AttackAirLw'


@pytest.mark.parametrize('pose', ['dair:-1', 'dair:nan', ':8', 'missing:3'])
def test_bad_or_missing_pose_is_actionable(project, pose):
    root, source, _ = project
    with pytest.raises(ValueError):
        load_project(source, root=root, pose=pose)


def test_unknown_alternate_art_fails_before_render(project):
    root, source, package = project
    doc = json.loads((package / 'geno.json').read_text())
    doc['fighters'][0]['fighter']['costumes'].append({'name': 'Red'})
    (package / 'geno.json').write_text(json.dumps(doc))
    (root / '_build/author/fighter.json').write_text(json.dumps({'art': {'glb': 'fighter.glb'}}))
    with pytest.raises(ValueError, match='costume'):
        load_project(source, root=root)


def test_subset_adds_zero_when_package_has_no_fallback(project):
    root, source, package = project
    doc = json.loads((package / 'geno.json').read_text())
    doc['fighters'][0]['fighter']['costumes'].append({'name': 'Red'})
    (package / 'geno.json').write_text(json.dumps(doc))
    cfg = json.loads((source / 'workbench.json').read_text())
    cfg['ui_render'] = {'costumes': {'1': {'material_colors': {'Gi': '#FF0000'}}}}
    (source / 'workbench.json').write_text(json.dumps(cfg))
    (root / '_build/author/fighter.json').write_text(json.dumps({'art': {'glb': 'fighter.glb'}}))
    job = load_project(source, root=root, costume='1')
    assert [c['index'] for c in job['costumes']] == [0, 1]


def test_outputs_cannot_escape_generated_root(tmp_path):
    assert generated_path(tmp_path / '_build/a', tmp_path).name == 'a'
    with pytest.raises(ValueError):
        generated_path(tmp_path / 'tools/a', tmp_path)
    with pytest.raises(ValueError):
        generated_path(tmp_path / '_build/../outside', tmp_path)


def test_unreadable_modern_compressed_blend_still_uses_glb(project):
    root, source, _ = project
    (root / '_build/author/fighter.blend').write_bytes(b'\x28\xb5\x2f\xfd' + bytes(32))
    assert load_project(source, root=root)['art'].endswith('fighter.glb')


def test_subset_repairs_only_missing_zero_fields(project):
    root, source, package = project
    doc = json.loads((package / 'geno.json').read_text())
    entry = doc['fighters'][0]
    entry['fighter']['costumes'].append({'name': 'Red'})
    entry['presentation'] = {'icon': 'icon.gxtex', 'portrait': ['portrait.gxtex'], 'stock': ['stock.gxtex']}
    for name in ('icon.gxtex', 'portrait.gxtex', 'stock.gxtex'):
        (package / 'files' / name).write_bytes(b'previous art')
    (package / 'geno.json').write_text(json.dumps(doc))
    cfg = json.loads((source / 'workbench.json').read_text())
    cfg['ui_render'] = {'costumes': {'1': {'material_colors': {'Gi': '#FF0000'}}}}
    (source / 'workbench.json').write_text(json.dumps(cfg))
    (root / '_build/author/fighter.json').write_text(json.dumps({'art': {'glb': 'fighter.glb'}}))
    job = load_project(source, root=root, costume='1')
    assert [c['index'] for c in job['costumes']] == [0, 1]
    assert job['fallback_zero_fields'] == ['results']
    assert load_project(source, root=root, costume='0')['fallback_zero_fields'] == []


def test_retail_alternate_uses_compatible_scene_and_rejects_glb(project):
    root, source, package = project
    doc = json.loads((package / 'geno.json').read_text())
    entry = doc['fighters'][0]
    entry['define']['base'] = 'captain'
    entry['fighter']['costumes'].append({'name': 'Red'})
    (package / 'geno.json').write_text(json.dumps(doc))
    (root / '_build/author/fighter.json').write_text('{}')
    retail = root / '_build/author/retail.blend'
    red = root / '_build/author/red.blend'
    for path in (retail, red):
        path.write_bytes(b'BLENDER-v305' + bytes(32))
    cfg = json.loads((source / 'workbench.json').read_text())
    cfg['ui_render'] = {'costumes': {'1': {'art': str(red)}}}
    (source / 'workbench.json').write_text(json.dumps(cfg))
    job = load_project(source, root=root, retail_scene=retail)
    assert job['costumes'][1]['art'] == str(red.resolve())
    cfg['ui_render']['costumes']['1']['art'] = str(root / '_build/author/fighter.glb')
    (source / 'workbench.json').write_text(json.dumps(cfg))
    with pytest.raises(ValueError, match='retail.*blend'):
        load_project(source, root=root, retail_scene=retail)


def test_generated_root_rejects_directory_link_outside_workspace(tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    try:
        (tmp_path / '_build').symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip('directory symlinks unavailable')
    with pytest.raises(ValueError):
        generated_path(tmp_path / '_build/escaped', tmp_path)


def test_string_bank_clips_match_the_built_plan_contract(project):
    root, source, package = project
    plan = {'row_clips': ['Wait'], 'bank': {'clips': ['Wait', 'AttackAirLw']}}
    (package / 'files/plan.json').write_text(json.dumps(plan))
    job = load_project(source, root=root, pose='AttackAirLw:3')
    assert job['action'] == 'AttackAirLw'
    assert load_project(source, root=root)['action'] == 'Wait'
