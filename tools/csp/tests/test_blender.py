"""Opt-in local integration, automatically skipped when the runtime cache is absent."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from PIL import Image

from tools.csp.fetch_csproject import load_tools
from tools.csp.project import generated_path

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('art_type', ['glb', 'blend'])
def test_blender351_appends_template_and_renders_synthetic_fighter(art_type):
    root = Path(os.environ.get('GW_ROOT', ROOT)).resolve()
    try:
        tools = load_tools(root)
    except (OSError, ValueError) as exc:
        pytest.skip('Blender 3.5.1/CSProject absent: ' + str(exc))
    version = subprocess.run([tools['blender'], '--version'], check=True, capture_output=True, text=True).stdout
    if not version.startswith('Blender 3.5.1\n'):
        pytest.skip('exact Blender 3.5.1 absent')
    import tempfile
    with tempfile.TemporaryDirectory(prefix='check-', dir=_test_dir(root)) as temporary:
        out = Path(temporary)
        env = dict(os.environ, BLENDER_USER_SCRIPTS=tools['scripts'])
        worker = ROOT / 'tools/csp/blender_render.py'
        common = [tools['blender'], '--background', '--factory-startup', '--python-exit-code', '1']
        subprocess.run(common + ['--python', str(worker), '--', '--inspect-template', tools['template'], '--out', str(out / 'inventory.json')], env=env, check=True)
        inventory = json.loads((out / 'inventory.json').read_text())
        names = [c['name'] for c in inventory['cameras']]
        assert len(names) == 9
        subprocess.run(common + ['--python', str(Path(__file__).with_name('blender_fixture.py')), '--', str(out / 'fighter.glb')], check=True)
        job = {'template': tools['template'], 'scripts': tools['scripts'], 'art': str(out / ('fighter.' + art_type)),
               'retail': False, 'action': 'Wait', 'frame': 8, 'frame_offset': 0,
               'costumes': [{'index': 0, **({'collections': ['CostumeDefault']} if art_type == 'blend' else {})}], 'scene_config': {'cameras': {n: {'width': 64, 'height': 64} for n in names}},
               'work': str(out), 'root': str(root)}
        (out / 'job.json').write_text(json.dumps(job))
        subprocess.run(common + ['--python', str(worker), '--', '--job', str(out / 'job.json')], env=env, check=True)
        result = json.loads((out / 'renders.json').read_text())
        assert set(result['enabled_addons']) == {'loom', 'render_button'}
        assert len(result['renders']['0']) == 10 and 'Results_SD' in result['renders']['0']  # nine template cameras + the results-card camera
        for name, path in result['renders']['0'].items():
            with Image.open(path) as image:
                assert image.size == ((208, 296) if name == 'Results_SD' else (64, 64))
        assert any(Image.open(path).getchannel('A').getbbox() for path in result['renders']['0'].values())


def _test_dir(root):
    path = generated_path(root / '_build/csp-render/tests', root)
    path.mkdir(parents=True, exist_ok=True)
    return path
