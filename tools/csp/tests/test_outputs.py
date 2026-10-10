"""Synthetic pixels catch wrong aspect, alpha, camera choice and costume indices."""
from pathlib import Path

import pytest
from PIL import Image

from tools.csp.outputs import (
    OUTPUTS, camera_outputs, enumerate_costumes, select_costumes,
    fit_rgba, postprocess, merge_presentation, validate_gxtex,
)


def test_dimensions_formats_and_no_palettes():
    want = {
        'icon': ((64, 56), 'rgb5a3'), 'portrait': ((136, 188), 'rgb5a3'),
        'stock': ((24, 24), 'rgba8'), 'results': ((52, 74), 'rgb5a3'),
        'emblem': ((80, 64), 'rgba8'),
    }
    for field, (size, fmt) in want.items():
        spec = OUTPUTS[field]
        # Assert the consuming transform as well as the conversion contract.
        image = fit_rgba(Image.new('RGBA', (7, 13), (220, 30, 10, 128)), spec.size)
        assert image.size == size
        assert image.mode == 'RGBA'
        assert spec.format == fmt
        assert not spec.palette
        assert image.getpixel((size[0] // 2, size[1] // 2))[3] == 128


def test_fit_preserves_aspect_and_transparent_padding():
    result = fit_rgba(Image.new('RGBA', (12, 6), (200, 10, 30, 255)), (24, 24))
    assert result.getchannel('A').getbbox() == (0, 6, 24, 18)
    assert result.getpixel((0, 0)) == (0, 0, 0, 0)


def test_palette_input_becomes_rgba():
    image = Image.new('P', (4, 4), 0)
    image.putpalette([255, 0, 0] + [0] * 765)
    image.info['transparency'] = 0
    assert fit_rgba(image, (24, 24)).getchannel('A').getbbox() is None


def test_postprocess_outline_and_shadow_keep_transparency():
    image = Image.new('RGBA', (9, 9))
    image.putpixel((4, 4), (255, 0, 0, 255))
    outline = postprocess(image, outline=1)
    assert outline.getpixel((4, 4)) == (255, 0, 0, 255)
    assert outline.getpixel((3, 4)) == (0, 0, 0, 255)
    assert outline.getpixel((0, 0))[3] == 0
    shadow = postprocess(image, shadow=(2, 1), shadow_alpha=100)
    assert shadow.getpixel((6, 5)) == (0, 0, 0, 100)
    assert shadow.getpixel((4, 4)) == (255, 0, 0, 255)


def test_camera_mapping_uses_sd_portrait_and_stock_head_for_icon():
    names = ['CSP_HD', 'CSP_SD', 'Stock_HD', 'Stock_SD', 'other']
    assert camera_outputs(names) == {
        'icon': 'Stock_HD', 'portrait': 'CSP_SD', 'stock': 'Stock_SD', 'results': 'CSP_SD',
    }
    assert camera_outputs(names, {'icon': 'other'})['icon'] == 'other'


@pytest.mark.parametrize('names, overrides', [
    (['CSP_SD'], None),
    (['CSP_SD', 'Stock_SD'], {'portrait': 'missing'}),
    (['CSP_SD', 'Stock_SD', 'stock-sd'], None),
])
def test_missing_or_ambiguous_camera_is_not_silently_chosen(names, overrides):
    with pytest.raises(ValueError):
        camera_outputs(names, overrides)


def test_costumes_follow_package_order_and_source_textures(tmp_path):
    entry = {'fighter': {'costumes': [{'name': 'Default'}, {'name': 'Red'}]}}
    source = {'costumes': [
        {'name': 'default', 'texture': 'atlas.png'}, {'name': 'red', 'texture': 'red.png'},
    ]}
    values = enumerate_costumes(entry, source, tmp_path)
    assert [(c['index'], c['name']) for c in values] == [(0, 'Default'), (1, 'Red')]
    assert values[1]['texture'] == str((tmp_path / 'red.png').resolve())
    assert [c['index'] for c in select_costumes(values, 'all')] == [0, 1]
    assert [c['index'] for c in select_costumes(values, '1')] == [1]


@pytest.mark.parametrize('selection', ['-1', '2', 'one', '1.0'])
def test_invalid_costume_selection(selection):
    with pytest.raises(ValueError):
        select_costumes([{'index': 0}, {'index': 1}], selection)


def test_source_count_mismatch_and_empty_declared_list_fail(tmp_path):
    with pytest.raises(ValueError):
        enumerate_costumes({'fighter': {'costumes': []}}, {}, tmp_path)
    with pytest.raises(ValueError):
        enumerate_costumes({'fighter': {'costumes': [{}, {}]}}, {'costumes': [{}]}, tmp_path)


def test_partial_render_preserves_indices_and_emblem():
    old = {'portrait': ['a.gxtex', 'b.gxtex', 'c.gxtex'], 'stock': 's.gxtex',
           'results': ['r0.gxtex', 'r1.gxtex', 'r2.gxtex'], 'emblem': 'e.gxtex'}
    rendered = {2: {'portrait': 'new.gxtex', 'stock': 'newstock.gxtex', 'results': 'res.gxtex'}}
    result = merge_presentation(old, rendered, 3)
    assert result['portrait'] == ['a.gxtex', 'b.gxtex', 'new.gxtex']
    assert result['stock'] == ['s.gxtex', 's.gxtex', 'newstock.gxtex']
    assert result['results'] == ['r0.gxtex', 'r1.gxtex', 'res.gxtex']
    assert result['emblem'] == 'e.gxtex'
    assert old['portrait'][2] == 'c.gxtex'


def test_partial_without_zero_fallback_is_rejected():
    with pytest.raises(ValueError, match='zero'):
        merge_presentation({}, {1: {'portrait': 'new.gxtex'}}, 2)


def test_art_name_and_gxtx_palette_validation(tmp_path):
    import struct
    def container(name, fmt=6, palette=0):
        path = tmp_path / name
        path.write_bytes(struct.pack('>4s10I', b'GXTX', 1, fmt, 24, 24,
                                    2 if palette else 0xFFFFFFFF, palette, 2304, 0, 64, 2368)
                         + bytes(20) + bytes(2304))
        return path
    validate_gxtex(container('stock.gxtex'), OUTPUTS['stock'])
    with pytest.raises(ValueError):
        validate_gxtex(container('bad.gxtex', palette=16), OUTPUTS['stock'])
    with pytest.raises(ValueError):
        validate_gxtex(container('wrong.gxtex', fmt=5), OUTPUTS['stock'])


def test_outline_does_not_darken_translucent_foreground():
    image = Image.new('RGBA', (9, 9))
    image.putpixel((4, 4), (255, 0, 0, 128))
    result = postprocess(image, outline=1)
    assert result.getpixel((4, 4)) == (255, 0, 0, 128)


def test_results_repair_uses_results_zero_instead_of_portrait_files():
    # Portraits may be paletted; a declared results file must be non-paletted.
    old = {'portrait': ['portrait0.gxtex', 'portrait1.gxtex', 'portrait2.gxtex']}
    result = merge_presentation(old, {0: {'results': 'results0.gxtex'},
                                      2: {'results': 'results2.gxtex'}}, 3)
    assert result['results'] == ['results0.gxtex', 'results0.gxtex', 'results2.gxtex']
