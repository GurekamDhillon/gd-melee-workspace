"""Package publication tests: invented pixels, staged failures, real png2gx when local."""
import json
import os
from pathlib import Path
import struct

import pytest
from PIL import Image

from tools.csp.render_ui import publish_package, convert_png
from tools.csp.outputs import OUTPUTS


def fake_convert(source, destination, spec):
    # Only the external encoder is doubled; transforms, naming, header validation
    # and declaration publication are the real production implementation.
    with Image.open(source) as image:
        assert image.size == spec.size and image.mode == 'RGBA'
    w, h = spec.size
    block = 4
    payload = ((w + block - 1) // block) * ((h + block - 1) // block) * (64 if spec.format == 'rgba8' else 32)
    fmt = 6 if spec.format == 'rgba8' else 5
    Path(destination).write_bytes(struct.pack('>4s10I', b'GXTX', 1, fmt, w, h,
                                              0xFFFFFFFF, 0, payload, 0, 64, 64 + payload)
                                 + bytes(20) + bytes(payload))


@pytest.fixture
def package_job(tmp_path):
    package = tmp_path / '_build/package'
    (package / 'files').mkdir(parents=True)
    (package / 'geno.json').write_text(json.dumps({'geno': 10, 'fighters': [{
        'define': {'key': 'synthetic'}, 'fighter': {'costumes': [{}]},
        'attributes': {'unchanged': 7},
    }]}))
    renders = {0: {}}
    for name in ('CSP_HD', 'CSP_SD', 'Stock_HD', 'Stock_SD', 'extra1', 'extra2', 'extra3', 'extra4', 'extra5'):
        image = package / (name + '.png')
        Image.new('RGBA', (64, 64), (255, 0, 0, 128)).save(image)
        renders[0][name] = str(image)
    job = {'root': str(tmp_path), 'package': str(package), 'entry_index': 0, 'count': 1, 'key': 'synthetic',
           'fields': {}, 'effects': {}, 'costumes': [{'index': 0}], 'emblem': None}
    return job, renders


def test_publication_writes_valid_files_and_preserves_fighter_data(package_job):
    job, renders = package_job
    result = publish_package(job, renders, convert=fake_convert)
    package = Path(job['package'])
    doc = json.loads((package / 'geno.json').read_text())
    assert doc['fighters'][0]['attributes'] == {'unchanged': 7}
    assert set(result) == {'icon', 'portrait', 'stock', 'results'}
    assert isinstance(result['icon'], str)
    for field in ('portrait', 'stock', 'results'):
        assert isinstance(result[field], list) and len(result[field]) == 1
    for name in [result['icon'], result['portrait'][0], result['stock'][0], result['results'][0]]:
        assert (package / 'files' / name).is_file()
        assert len(name) <= 63 and ' ' not in name
    assert doc['fighters'][0]['presentation'] == result


def test_failed_conversion_keeps_declaration_and_old_file(package_job):
    job, renders = package_job
    package = Path(job['package'])
    before = (package / 'geno.json').read_bytes()
    old = package / 'files/old.gxtex'
    old.write_bytes(b'old art')
    def fail(source, destination, spec):
        if spec.size == (24, 24):
            raise RuntimeError('encoder failed')
        fake_convert(source, destination, spec)
    with pytest.raises(RuntimeError, match='encoder failed'):
        publish_package(job, renders, convert=fail)
    assert (package / 'geno.json').read_bytes() == before
    assert old.read_bytes() == b'old art'
    assert list((package / 'files').iterdir()) == [old]


def test_authored_emblem_is_converted_separately(package_job):
    job, renders = package_job
    emblem = Path(job['package']) / 'original-emblem.png'
    Image.new('RGBA', (4, 3), (255, 255, 255, 255)).save(emblem)
    job['emblem'] = str(emblem)
    result = publish_package(job, renders, convert=fake_convert)
    assert isinstance(result['emblem'], str)
    assert (Path(job['package']) / 'files' / result['emblem']).is_file()


def test_real_converter_handles_odd_retail_size(tmp_path):
    root = Path(__file__).resolve().parents[3]
    game = Path(os.environ.get('GW_MELEE', root / 'melee'))
    tool = game / 'pc/tools/png2gx.py'
    if not tool.is_file():
        pytest.skip('local game png2gx.py absent; set GW_MELEE')
    source, dest = tmp_path / 'results.png', tmp_path / 'results.gxtex'
    Image.new('RGBA', (52, 74), (80, 140, 230, 128)).save(source)
    convert_png(source, dest, OUTPUTS['results'], tool=tool)
    assert dest.read_bytes()[:4] == b'GXTX'


def test_cancel_file_stops_only_owned_blender(tmp_path, monkeypatch):
    from tools.csp import render_ui
    cancel = tmp_path / 'cancel'
    cancel.touch()
    class OwnedProcess:
        returncode = None
        terminated = False
        def poll(self):
            return self.returncode
        def terminate(self):
            self.terminated = True
            self.returncode = -1
        def wait(self, timeout=None):
            return self.returncode
        def kill(self):
            self.returncode = -2
    process = OwnedProcess()
    monkeypatch.setattr(render_ui.subprocess, 'Popen', lambda *a, **kw: process)
    with pytest.raises(RuntimeError, match='cancelled'):
        render_ui.run_blender({'blender': 'external-blender', 'scripts': 'external-scripts'},
                              ['--job', 'fixture'], tmp_path / 'log', cancel_file=cancel)
    assert process.terminated


@pytest.mark.parametrize('repair_zero', [True, False])
def test_subset_keeps_existing_zero_art_unless_zero_was_requested(package_job, repair_zero):
    job, renders = package_job
    package = Path(job['package'])
    doc = json.loads((package / 'geno.json').read_text())
    entry = doc['fighters'][0]
    entry['fighter']['costumes'] = [{}, {}, {}]
    old = {'icon': 'old-icon.gxtex', 'portrait': ['old-portrait.gxtex'] * 3, 'stock': ['old-stock.gxtex'] * 3}
    entry['presentation'] = old
    for name in ('old-icon.gxtex', 'old-portrait.gxtex', 'old-stock.gxtex'):
        (package / 'files' / name).write_bytes(b'previous art')
    (package / 'geno.json').write_text(json.dumps(doc))
    job.update(count=3, costumes=[{'index': 0}, {'index': 2}],
               fallback_zero_fields=['results'] if repair_zero else [])
    renders[2] = renders[0]
    result = publish_package(job, renders, convert=fake_convert)
    if repair_zero:
        assert result['icon'] == old['icon']
        assert result['portrait'][:2] == old['portrait'][:2]
        assert result['stock'][:2] == old['stock'][:2]
    else:
        assert result['icon'] != old['icon']
        assert result['portrait'][0] != old['portrait'][0]
        assert result['stock'][0] != old['stock'][0]
    assert result['portrait'][2] != old['portrait'][2]
    assert result['results'][0].startswith('GnUi_')
    assert result['results'][1] == result['results'][0]


def test_publication_rejects_files_directory_link(package_job):
    job, renders = package_job
    package = Path(job['package'])
    outside = Path(job['root']) / 'outside'
    outside.mkdir()
    (package / 'files').rmdir()
    try:
        (package / 'files').symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip('directory symlinks unavailable')
    before = (package / 'geno.json').read_bytes()
    with pytest.raises(ValueError, match='outside'):
        publish_package(job, renders, convert=fake_convert)
    assert (package / 'geno.json').read_bytes() == before
    assert list(outside.iterdir()) == []
