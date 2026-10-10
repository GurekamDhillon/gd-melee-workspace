"""Opt-in: the own backend end to end in background Blender (skips without a current Blender)."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

import pytest
from PIL import Image

from tools.csp.render_ui import OWN_BLENDER_DEFAULTS

ROOT = Path(__file__).resolve().parents[3]


def blender():
    for candidate in (os.environ.get('GW_BLENDER'), *OWN_BLENDER_DEFAULTS):
        if candidate and Path(candidate).is_file():
            return candidate
    pytest.skip('no current Blender (GW_BLENDER)')


def test_own_backend_renders_ten_framed_cameras():
    exe = blender()
    root = Path(os.environ.get('GW_ROOT', ROOT)).resolve()
    base = root / '_build/csp-render'
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='own-check-', dir=base) as temporary:
        out = Path(temporary)
        common = [exe, '--background', '--factory-startup', '--python-exit-code', '1']
        fixture = Path(__file__).with_name('blender_fixture.py')
        subprocess.run(common + ['--python', str(fixture), '--', str(out / 'fighter.glb')], check=True,
                       capture_output=True)
        job = {'art': str(out / 'fighter.glb'), 'retail': False, 'action': 'Wait', 'frame': 0, 'frame_offset': 0,
               'costumes': [{'index': 0}], 'scene_config': {}, 'roles': {}, 'work': str(out), 'root': str(root)}
        (out / 'job.json').write_text(json.dumps(job))
        subprocess.run(common + ['--python', str(ROOT / 'tools/csp/own_render.py'), '--', '--job', str(out / 'job.json')],
                       check=True, capture_output=True)
        result = json.loads((out / 'renders.json').read_text())
        views = result['renders']['0']
        assert len(views) == 10 and 'Results_SD' in views
        sizes = {name: Image.open(path).size for name, path in views.items()}
        assert sizes['Results_SD'] == (208, 296) and sizes['STC_HD'] == (144, 144) and sizes['Render'] == (1000, 1500)
        for path in views.values():
            assert Image.open(path).getchannel('A').getbbox(), path   # something drawn in every view
        cameras = result['scenes'][0]['cameras']
        assert cameras['STC_HD']['height'] < cameras['CSP_HD']['height'] < cameras['Render']['height']
