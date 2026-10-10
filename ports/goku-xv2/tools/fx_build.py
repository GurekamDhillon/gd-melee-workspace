"""Original effect packages for Goku (ki aura, ki orb, Kamehameha beams, instant-transmission vanish, dash trail).

python ports/goku-xv2/tools/fx_build.py   -> _build/goku-xv2/fx/<name>/<name>.gfx.json + tex/ki_soft.png
build.py copies them into the package (fx/) and writes fx/fx_bindings.json. Nothing here is XV2 data: fx_emitter_template.json holds
the effect IR's field skeleton (every value below is set here), the texture is a generated soft disc. Names start with P_Trail because
the shared fx_bindings schema (ports/ir/schema) requires that prefix.
"""
import copy
import json
import struct
import zlib
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
OUT = PORT.parents[1] / '_build/goku-xv2/fx'
TEMPLATE = json.loads((PORT / 'tools/fx_emitter_template.json').read_text(encoding='utf-8'))


def png_soft(path, n=64):
    rows = []
    for y in range(n):
        row = bytearray([0])
        for x in range(n):
            d = ((x + .5 - n / 2) ** 2 + (y + .5 - n / 2) ** 2) ** .5 / (n / 2)
            a = max(0.0, 1.0 - d)
            a = a * a * (3 - 2 * a)  # smoothstep falloff
            row += bytes([255, 255, 255, int(a * 255)])
        rows.append(bytes(row))
    raw = zlib.compress(b''.join(rows), 9)

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', n, n, 8, 6, 0, 0, 0)) + chunk(b'IDAT', raw) + chunk(b'IEND', b''))


def emitter(name, *, follow='srt', rate=2.0, duration=0, one_time=False, radius=(1, 1, 1), shape='sphere_fill', life=20, speed=0.0,
            direction=(0, 1, 0), dscale=0.0, gravity=0.0, size=(3.0, 0.3), c0=(0.6, 0.9, 1.0), c1=(1, 1, 1), scale=1.0, blend='add',
            translate=(0, 0, 0), position_random=0.0):
    e = copy.deepcopy(TEMPLATE)
    for k in ('program', 'approx'):
        e.pop(k, None)
    e['mesh'] = None
    e.update(name=name, order=0, kind='particle', follow=follow)
    e['transform']['translate'] = list(translate)
    e['wave']['apply'] = [0, 0, 0]
    em = e['emission']
    em.update(start=0, duration=duration, one_time=one_time, rate=rate, rate_random=0.0, interval=0, interval_random=0.0, position_random=position_random)
    e['shape'].update(type=shape, radius=list(radius))
    p = e['particle']
    p.update(life=life, life_random_pct=30)
    p['velocity'].update(all_direction=speed, direction=list(direction), direction_scale=dscale, random_pct=40.0, inherit=0.0)
    p['forces'].update(gravity=gravity, air_resistance=0.95)
    p['scale'].update(base=[size[0]] * 3, random_pct=[25.0] * 3, keys=[[1.0, 1.0, 1.0, 0.0], [0.7, 0.7, 0.7, 0.5], [size[1] / size[0]] * 3 + [1.0]])
    p['rotation'].update(init=[0.0, 0.0, 0.0], init_random=[0.0, 0.0, 6.28])
    c = e['color']
    c['scale'] = scale
    c['emitter'] = {'color0': list(c0) + [1.0], 'color1': list(c1) + [1.0]}
    c['color0'] = {'kind': 'constant', 'value': list(c0)}
    c['color1'] = {'kind': 'constant', 'value': list(c1)}
    c['alpha0'] = {'kind': 'constant', 'value': 0.85}
    c['alpha1'] = {'kind': 'constant', 'value': 1.0}
    e['samplers'][0].update(texture='ki_soft', wrap=['Clamp', 'Clamp'])
    e['material']['blend'] = blend
    e['material']['bloom'] = {'threshold': 0.8, 'intensity': 1.5}
    e['material']['shader'].update(color_textures=[0], alpha_textures=[0])
    return e


PACKAGES = {
    # continuous ki aura around the body: rising soft sparks, cyan to white
    'P_TrailGokuAura': [emitter('aura', rate=3.0, radius=(3.2, 7.0, 3.2), life=26, dscale=0.45, size=(3.4, 0.4), c0=(0.45, 0.8, 1.0), c1=(1, 1, 1), scale=1.6),
                        emitter('core', rate=0.6, radius=(1.5, 5.0, 1.5), life=12, dscale=0.1, size=(6.0, 3.0), c0=(0.3, 0.6, 1.0), c1=(0.9, 0.97, 1.0), scale=0.9)],
    # the charge orb (article KameOrb is re-spawned every 5 frames; each glows for its 7 frames)
    'P_TrailGokuOrb': [emitter('glow', rate=1.5, radius=(0.3, 0.3, 0.3), life=8, size=(5.5, 3.5), c0=(0.5, 0.85, 1.0), c1=(1, 1, 1), scale=2.2),
                       emitter('sparks', rate=1.0, radius=(2.0, 2.0, 2.0), shape='sphere', life=10, speed=-0.18, size=(1.8, 0.3), c0=(0.7, 0.95, 1.0), c1=(1, 1, 1), scale=2.0)],
    # Kamehameha beams: a bright core glow and a trail that stays behind in the world
    'P_TrailGokuBeam': [emitter('core', rate=2.0, radius=(0.6, 0.6, 0.6), life=8, size=(7.0, 4.0), c0=(0.5, 0.85, 1.0), c1=(1, 1, 1), scale=2.2),
                        emitter('trail', follow='none', rate=2.5, radius=(1.2, 1.2, 1.2), life=16, dscale=0.05, size=(4.5, 0.8), c0=(0.35, 0.7, 1.0), c1=(0.85, 0.95, 1.0), scale=1.4)],
    'P_TrailGokuBeamBig': [emitter('core', rate=2.5, radius=(0.8, 0.8, 0.8), life=8, size=(9.5, 5.5), c0=(0.55, 0.9, 1.0), c1=(1, 1, 1), scale=2.6),
                           emitter('trail', follow='none', rate=3.0, radius=(1.8, 1.8, 1.8), life=20, dscale=0.05, size=(6.5, 1.0), c0=(0.35, 0.7, 1.0), c1=(0.9, 0.97, 1.0), scale=1.6)],
    'P_TrailGokuBeamSuper': [emitter('core', rate=3.0, radius=(1.2, 1.2, 1.2), life=9, size=(15.0, 9.0), c0=(1.0, 0.95, 0.6), c1=(1, 1, 1), scale=3.0),
                             emitter('trail', follow='none', rate=4.0, radius=(3.0, 3.0, 3.0), life=26, dscale=0.05, size=(10.0, 1.5), c0=(0.55, 0.8, 1.0), c1=(1.0, 0.97, 0.8), scale=2.0)],
    # instant transmission / Z-vanish: a short burst at the vanish and the reappear
    'P_TrailGokuVanish': [emitter('burst', follow='none', rate=12.0, duration=4, one_time=True, radius=(2.0, 4.0, 2.0), life=14, speed=0.7, size=(5.5, 0.5), c0=(0.7, 0.9, 1.0), c1=(1, 1, 1), scale=2.2),
                          emitter('flash', follow='none', rate=1.0, duration=2, one_time=True, radius=(0.2, 0.2, 0.2), life=6, size=(14.0, 2.0), c0=(1, 1, 1), c1=(1, 1, 1), scale=2.8)],
    # dragon rush: afterimage streaks left behind while he dashes
    'P_TrailGokuDash': [emitter('streak', follow='none', rate=3.0, radius=(1.0, 4.0, 1.0), life=12, size=(4.0, 0.6), c0=(0.8, 0.9, 1.0), c1=(1, 1, 1), scale=1.8)],
}


def main():
    for name, emitters in PACKAGES.items():
        d = OUT / name
        png_soft(d / 'tex/ki_soft.png')
        doc = {'geno_fx': 1, 'name': name, 'source': {'format': 'original (ports/goku-xv2/tools/fx_build.py)', 'set': name},
               'space': {'forward': [0, 0, 1], 'up': [0, 1, 0]}, 'textures': [{'name': 'ki_soft', 'file': 'tex/ki_soft.png', 'w': 64, 'h': 64, 'source_format': 'rgba8', 'swizzle': 'rgba'}],
               'meshes': [], 'emitters': emitters}
        for i, e in enumerate(doc['emitters']):
            e['order'] = i
        (d / f'{name}.gfx.json').write_text(json.dumps(doc, indent=1), encoding='utf-8')
    print(len(PACKAGES), 'effect packages in', OUT)


if __name__ == '__main__':
    main()
