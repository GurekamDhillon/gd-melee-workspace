"""Acquisition planning and archive confinement use invented paths/bytes."""
import io
from pathlib import Path
import zipfile

import pytest

from tools.csp.fetch_csproject import choose_scene, safe_extract, validate_tools


def test_scene_selection_prefers_csproject_pose():
    paths = ['Resources/loom.zip', 'Captain Falcon/Melee Pose.blend', 'Captain Falcon/CSProject Pose.blend', 'Mario/CSProject.blend']
    assert choose_scene(paths, 'captain') == 'Captain Falcon/CSProject Pose.blend'


def test_ambiguous_and_wrong_character_scenes_are_rejected():
    with pytest.raises(ValueError):
        choose_scene(['Falcon/a.blend', 'Falcon/b.blend'], 'captain')
    with pytest.raises(ValueError):
        choose_scene(['Mario/CSProject.blend'], 'captain')


def test_extract_keeps_nested_files(tmp_path):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('loom/__init__.py', 'fixture')
    archive.seek(0)
    safe_extract(archive, tmp_path)
    assert (tmp_path / 'loom/__init__.py').read_text() == 'fixture'


@pytest.mark.parametrize('name', ['../outside', '/outside', 'C:/outside', 'loom/../../outside', '..\\outside'])
def test_archive_cannot_escape(tmp_path, name):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr(name, 'fixture')
    archive.seek(0)
    with pytest.raises(ValueError):
        safe_extract(archive, tmp_path / 'local')
    assert not (tmp_path / 'outside').exists()


def test_cached_tools_require_expected_paths_and_version(tmp_path):
    base = tmp_path / '_build/tools-ext'
    base.mkdir(parents=True)
    paths = {}
    for key, name in [('blender', 'blender.exe'), ('template', 'Falcon.blend')]:
        path = base / name
        path.write_bytes(b'fixture')
        paths[key] = str(path)
    scripts = base / 'scripts'
    (scripts / 'addons/loom').mkdir(parents=True)
    (scripts / 'addons/loom/__init__.py').write_text('')
    (scripts / 'addons/render_button.py').write_text('')
    manifest = dict(paths, scripts=str(scripts), blender_version='3.5.1')
    assert validate_tools(manifest, tmp_path) == manifest
    with pytest.raises(ValueError):
        validate_tools(dict(manifest, blender_version='4.0'), tmp_path)
    with pytest.raises(ValueError):
        validate_tools(dict(manifest, template=str(tmp_path / 'elsewhere')), tmp_path)


def directory_link(path, target):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip('directory symlinks unavailable')


def test_extract_rejects_target_link_outside_cache(tmp_path):
    cache, outside = tmp_path / 'cache', tmp_path / 'outside'
    cache.mkdir()
    outside.mkdir()
    directory_link(cache / 'blender', outside)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('blender.exe', 'fixture')
    archive.seek(0)
    with pytest.raises(ValueError, match='outside'):
        safe_extract(archive, cache / 'blender', boundary=cache)
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize('linked_subtree', ['scripts', 'blender', 'CSProject'])
def test_fetch_rejects_existing_external_subtree_before_git(tmp_path, monkeypatch, linked_subtree):
    from tools.csp import fetch_csproject
    cache = tmp_path / '_build/tools-ext/csp'
    cache.mkdir(parents=True)
    outside = tmp_path / 'outside'
    outside.mkdir()
    directory_link(cache / linked_subtree, outside)
    def forbidden(*args, **kwargs):
        pytest.fail('git/network must not start before mutable-path preflight')
    monkeypatch.setattr(fetch_csproject.subprocess, 'run', forbidden)
    monkeypatch.setattr(fetch_csproject.urllib.request, 'urlopen', forbidden)
    with pytest.raises(ValueError, match='outside'):
        fetch_csproject.fetch(tmp_path)
    assert list(outside.iterdir()) == []


def test_install_addons_rejects_linked_destination(tmp_path):
    from tools.csp.fetch_csproject import install_addons
    cache, resources, outside = tmp_path / 'cache', tmp_path / 'resources', tmp_path / 'outside'
    cache.mkdir()
    resources.mkdir()
    outside.mkdir()
    (resources / 'loom.py').write_text('fixture')
    (resources / 'render_button.py').write_text('fixture')
    directory_link(cache / 'scripts/addons', outside)
    with pytest.raises(ValueError, match='outside'):
        install_addons(resources, cache)
    assert list(outside.iterdir()) == []
