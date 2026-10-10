"""Pure framing math: crop rules, aspect fitting, camera placement, backend selection."""
import math

import pytest

from tools.csp import framing
from tools.csp.render_ui import BACKENDS, find_blender, select_backend


def body():
    # A 20-unit-tall column (x -1..1) with joints at plausible heights; vertex density even in z.
    points = [(x * 0.5, y * 0.25, z * 0.1) for x in range(-2, 3) for y in range(-1, 2) for z in range(0, 201)]
    joints = {'hips': (0, 0, 10), 'spine': (0, 0, 12), 'chest': (0, 0, 14), 'neck': (0, 0, 16), 'head': (0, 0, 17)}
    return joints, points


def front():
    return framing.camera_basis((0, -1, 0), 0.0)


def test_crop_order_head_to_full_body():
    joints, points = body()
    anchors = framing.anchor_points(joints, points)
    heights = {a: framing.plan(a, anchors, points, front())['height'] for a in ('stock', 'icon', 'portrait', 'results')}
    assert heights['stock'] < heights['icon'] < heights['portrait'] < heights['results']
    full = framing.plan('results', anchors, points, front())
    assert full['rect'][1] == pytest.approx(0.0)       # floor
    assert full['rect'][3] == pytest.approx(20.0)      # top of mesh
    stock = framing.plan('stock', anchors, points, front())
    assert stock['rect'][1] > anchors['neck'][2] - 1.0  # starts at the neck, not the feet


def test_fit_matches_image_aspect_and_keeps_headroom_side():
    joints, points = body()
    anchors = framing.anchor_points(joints, points)
    for asset, spec in framing.ASSETS.items():
        r = framing.plan(asset, anchors, points, front())
        assert r['width'] / r['height'] == pytest.approx(spec.size[0] / spec.size[1], rel=1e-6)
        assert r['rect'][0] >= r['centre'][0] - r['width'] / 2 - 1e-6
    # grow='down' keeps the top edge: the head stays where the pad put it.
    rect = (-5, 10, 5, 20)
    cu, cv, w, h = framing.fit_rect(rect, (136, 188), 0.0, 'down')
    assert cv + h / 2 == pytest.approx(20.0)
    assert h > 10 and w == pytest.approx(h * 136 / 188)


def test_camera_distance_and_ortho_scale():
    fit = (0.0, 5.0, 4.0, 6.0)
    ortho = framing.camera_for(fit, front())
    assert ortho['ortho_scale'] == 6.0
    persp = framing.camera_for(fit, front(), lens=100, sensor=36)
    assert persp['distance'] == pytest.approx(6.0 * 100 / 36)
    horiz = framing.camera_for(fit, front(), lens=100, sensor=36, fit='HORIZONTAL')
    assert horiz['distance'] == pytest.approx(4.0 * 100 / 36)
    # camera sits in front of the crop centre, looking at it
    assert persp['location'][1] < persp['centre'][1]


def test_facing_and_basis():
    assert framing.facing_from_sides((1, 0, 0), (-1, 0, 0)) == pytest.approx((0, -1, 0))
    assert framing.facing_from_feet([(0, 0, 0)], [(0, -2, 0)]) == pytest.approx((0, -1, 0))
    basis = framing.camera_basis((0, -1, 0), 90.0)
    assert basis['look'][0] == pytest.approx(-1.0) or basis['look'][0] == pytest.approx(1.0)
    assert abs(sum(a * b for a, b in zip(basis['right'], basis['look']))) < 1e-9
    assert basis['up'][2] > 0.99


def test_missing_joints_fall_back_and_are_reported():
    _, points = body()
    anchors = framing.anchor_points({'hips': (0, 0, 10)}, points)
    assert 'neck' in anchors['fallback'] and 'hips' not in anchors['fallback']
    assert anchors['neck'][2] == pytest.approx(0.82 * 20, rel=0.01)


def test_asset_for_camera_names():
    names = {'All-Star_HD': 'allstar', 'CSS Icon_SD': 'icon', 'CSP_HD': 'portrait', 'STC_SD': 'stock',
             'Render': 'render', 'Results_SD': 'results'}
    for name, asset in names.items():
        assert framing.asset_for_camera(name) == asset
    with pytest.raises(ValueError):
        framing.asset_for_camera('Camera.001')


def test_role_bones_from_plan_with_aliases_and_override():
    plan = {'joints': [{'index': 4, 'name': 'j4'}, {'index': 9, 'name': 'b_C_Head'}],
            'roles': {'hips': [4], 'head': [9], 'neck': [77]}}
    assert framing.resolve_role_bones(plan, {'j4': 'JOBJ_4'}) == {'hips': 'JOBJ_4', 'head': 'b_C_Head'}
    assert framing.resolve_role_bones(plan, None, {'hips': 'Pelvis'})['hips'] == 'Pelvis'


def test_backend_selection(tmp_path, monkeypatch):
    assert BACKENDS == ('csproject', 'own')
    assert select_backend('own') == 'own' and select_backend('csproject') == 'csproject'
    with pytest.raises(ValueError):
        select_backend('cycles')
    exe = tmp_path / 'blender.exe'
    exe.write_text('x')
    assert find_blender(str(exe), {}) == str(exe)
    assert find_blender(None, {'GW_BLENDER': str(exe)}) == str(exe)
    monkeypatch.setattr('tools.csp.render_ui.OWN_BLENDER_DEFAULTS', ())
    monkeypatch.setattr('shutil.which', lambda name: None)
    with pytest.raises(ValueError, match='GW_BLENDER'):
        find_blender(None, {})
