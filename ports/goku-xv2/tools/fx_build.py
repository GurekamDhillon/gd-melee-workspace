"""Original effect packages for Goku (ki aura, ki orb, Kamehameha beams, instant-transmission vanish, dash trail).

python ports/goku-xv2/tools/fx_build.py   -> _build/goku-xv2/fx/<name>/<name>.gfx.json + tex/ki_soft.png
build.py copies them into the package (fx/) and writes fx/fx_bindings.json. Nothing here is XV2 data: fx_emitter_template.json holds
the effect IR's field skeleton (every value below is set here), the texture is a generated soft disc. Names start with P_Trail because
the shared fx_bindings schema (ports/ir/schema) requires that prefix.
"""
import copy
import json
import math
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
    e['wave'].update(type=0, amplitude=[0.0, 0.0], phase_random=[0.0, 0.0])   # the template's wave moves the particle POSITION whatever 'apply' says (gw_fx.c fx_visual_update)
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


def cyl_mesh(segs=14, taper=1.0):
    """Unit cylinder along +Z (z 0..1), radius 1 at z 0 and `taper` at z 1; uv u = round, v = length."""
    pos, nor, uv, idx = [], [], [], []
    import math
    for j in range(2):
        for i in range(segs + 1):
            a = 2 * math.pi * i / segs
            r = 1.0 if j == 0 else taper
            pos.append([math.cos(a) * r, math.sin(a) * r, float(j)])
            nor.append([math.cos(a), math.sin(a), 0.0])
            uv.append([i / segs, float(j)])
    for i in range(segs):
        a, b, c, d = i, i + 1, i + segs + 1, i + segs + 2
        idx += [a, b, c, b, d, c]
    return {'name': 'cyl', 'position': pos, 'normal': nor, 'uv0': uv, 'color0': None, 'indices': idx}


def box_mesh(axis, length=14.0, half=0.5):
    """A thin box from 0 to `length` along local axis 0/1/2 (the axis test)."""
    pos, nor, uv, idx = [], [], [], []
    for sx in (0, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                p = [0.0, 0.0, 0.0]
                others = [k for k in range(3) if k != axis]
                p[axis] = sx * length
                p[others[0]] = sy * half
                p[others[1]] = sz * half
                pos.append(p); nor.append([0.0, 0.0, 1.0]); uv.append([sx, 0.5])
    for tri in ([0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]):
        idx += tri
    return {'name': 'box%d' % axis, 'position': pos, 'normal': nor, 'uv0': uv, 'color0': None, 'indices': idx}


def mesh_emitter(name, mesh, *, follow='srt', life=30, base=(1.0, 1.0, 1.0), keys=None, c0=(0.5, 0.85, 1.0), c1=(1, 1, 1), scale=2.0,
                 translate=(0, 0, 0), rotate=(0, 0, 0), start=0, blend='add', fresnel=None, alpha=1.0, bloom=1.5):
    """One mesh particle for `life` frames, scaled per axis by base x keys[[x,y,z,t]...] (z is the length for cyl_mesh)."""
    e = emitter(name, follow=follow, rate=1.0, duration=1, one_time=True, radius=(0.0, 0.0, 0.0), shape='point', life=life, speed=0.0, size=(1.0, 1.0),
                c0=c0, c1=c1, scale=scale, blend=blend, translate=translate)
    e['kind'] = 'mesh'; e['mesh'] = mesh
    e['transform']['rotate'] = list(rotate)
    e['emission']['start'] = start
    p = e['particle']
    p['life_random_pct'] = 0
    p['scale']['base'] = list(base)
    p['scale']['random_pct'] = [0.0, 0.0, 0.0]
    p['scale']['keys'] = keys or [[1, 1, 1, 0.0], [1, 1, 1, 1.0]]
    p['rotation']['init_random'] = [0.0, 0.0, 0.0]
    p['velocity']['random_pct'] = 0.0
    e['color']['alpha0'] = {'kind': 'constant', 'value': alpha}
    if fresnel:
        e['material']['shader']['fresnel'] = True
        e['material']['fresnel_alpha'] = list(fresnel)
    e['material']['bloom'] = {'threshold': 0.7, 'intensity': bloom}
    return e



from kame_geom import ROT as RISE, along, D  # the beam direction in the hand's frame (kame_geom.py)


def beam_package(R, L, life, ramp=4, hot=(1, 1, 1), edge=(0.25, 0.65, 1.0), sparks=2.5, flash=0):
    """A Kamehameha beam from the right hand: soft outer glow + bright core + white hot core (mesh cylinders that grow out to L in `ramp`
    frames and close at the end), a muzzle flare, a tip/impact flare with a spark burst, and sparks streaming along the beam."""
    c = max(1, life - 6)
    grow = lambda r=1.0: [[r, r, 0.04, 0.0], [r, r, 1.0, ramp / life], [r * 1.06, r * 1.06, 1.0, 0.5], [r, r, 1.0, c / life], [0.25 * r, 0.25 * r, 1.0, 1.0]]
    dv = D
    return [
        mesh_emitter('glow', 'cyl', life=life, base=(R * 1.9, R * 1.9, L), keys=grow(), c0=edge, c1=(0.4, 0.8, 1.0), scale=1.2, alpha=0.28, rotate=RISE, bloom=0.8),
        mesh_emitter('body', 'cyl', life=life, base=(R * 1.15, R * 1.15, L), keys=grow(), c0=(0.25, 0.65, 1.0), c1=(0.6, 0.9, 1.0), scale=1.8, alpha=0.75, rotate=RISE, bloom=1.0),
        mesh_emitter('core', 'cyl', life=life, base=(R * 0.42, R * 0.42, L), keys=grow(), c0=hot, c1=hot, scale=2.4, alpha=1.0, rotate=RISE, bloom=1.4),
        emitter('muzzle', rate=1.0, duration=1, one_time=True, radius=(0, 0, 0), shape='point', life=life, size=(R * 4.2, R * 2.6), c0=(0.4, 0.8, 1.0), c1=(0.9, 0.98, 1), scale=1.8, translate=along(2.0)),
        emitter('tip', rate=1.0, duration=1, one_time=True, radius=(0, 0, 0), shape='point', life=life - ramp, size=(R * 5.5, R * 3.5), c0=(0.5, 0.85, 1.0), c1=(0.95, 1, 1), scale=2.0, translate=along(L)),
        emitter('burst', rate=sparks * 2, duration=life - ramp, radius=(R * 0.6, R * 0.6, R * 0.6), shape='sphere', life=9, speed=0.9, size=(R * 1.1, 0.2), c0=(0.7, 0.95, 1.0), c1=(1, 1, 1), scale=2.4, translate=along(L)),
        *([emitter('flash', rate=1.0, duration=1, one_time=True, radius=(0, 0, 0), shape='point', life=flash, size=(R * 11, R * 7), c0=(0.7, 0.95, 1.0), c1=(1, 1, 1), scale=3.0, translate=along(3.0))] if flash else []),
        emitter('sparks', rate=sparks, duration=life, radius=(R * 0.8, R * 0.8, R * 0.8), shape='sphere_fill', life=max(8, int(L / 4.5)), speed=0.0, direction=dv, dscale=4.5, size=(R * 0.9, 0.15), c0=(0.7, 0.95, 1.0), c1=(1, 1, 1), scale=2.4),
    ]


def charge_package(R=5.5):
    """The ki ball between the cupped hands: grows over the 60-frame charge, flashes at each 15-frame step, then holds at full size with
    sparks drawn in; the ball is a pair of billboards (glow + white core)."""
    # one long-lived particle per layer: grows over the 60 charge frames (t = 0 .. 0.1 of its 600-frame life), then holds; the state's exit ends it
    big = lambda a, b: [[a, a, a, 0.0], [(a + b) / 2, (a + b) / 2, (a + b) / 2, 0.05], [b, b, b, 0.1], [b * 1.05, b * 1.05, b * 1.05, 0.2], [b, b, b, 0.3], [b * 1.05, b * 1.05, b * 1.05, 0.4], [b, b, b, 1.0]]
    out = []
    for name, size, c0, sc, a, b in (('ball', R * 2.0, (0.25, 0.65, 1.0), 1.5, 0.12, 1.0), ('white', R * 1.0, (0.85, 0.97, 1.0), 2.2, 0.12, 1.0)):
        e = emitter(name, rate=1.0, duration=1, one_time=True, radius=(0, 0, 0), shape='point', life=600, size=(size, size), c0=c0, c1=(1, 1, 1), scale=sc, translate=(0, 0, 4))
        e['particle']['scale']['keys'] = big(a, b)
        out.append(e)
    for i, start in enumerate((15, 30, 45, 60)):
        fl = emitter('step%d' % (i + 1), rate=1.0, duration=1, one_time=True, radius=(0, 0, 0), shape='point', life=8, size=(R * (3.0 + i * 0.9), R * 0.5), c0=(0.7, 0.95, 1.0), c1=(1, 1, 1), scale=3.2 + i * 0.4, translate=(0, 0, 4))
        fl['emission']['start'] = start
        out.append(fl)
    for i, start in enumerate((0, 20, 40)):
        out.append(emitter('draw%d' % i, rate=1.0 + i, duration=0, radius=(R * 2.4, R * 2.4, R * 2.4), shape='sphere', life=12, speed=-0.2 - 0.05 * i, size=(1.6 + i * 0.4, 0.2),
                           c0=(0.7, 0.95, 1.0), c1=(1, 1, 1), scale=2.4, translate=(0, 0, 4)))
        out[-1]['emission']['start'] = start
    for e in out:
        e['material']['depth_test'] = False   # the hands are behind his body in the cup pose: draw the ball over it
    return out


MESHES = {'cyl': cyl_mesh()}

PACKAGES = {
    # the Kamehameha rework (KAMEHAMEHA.md): charge ball, four beams
    'P_TrailGokuKameCharge': charge_package(),
    'P_TrailGokuKameTap': beam_package(1.2, 22, 18, ramp=3),
    'P_TrailGokuKameMid': beam_package(1.8, 28, 34, ramp=4, sparks=3.0),
    'P_TrailGokuKameFull': beam_package(2.6, 36, 46, ramp=5, sparks=3.5, flash=5),
    'P_TrailGokuKameSuper': beam_package(4.0, 52, 64, ramp=6, hot=(1.0, 0.97, 0.8), edge=(0.45, 0.75, 1.0), sparks=4.5, flash=7),
    # continuous ki aura around the body (owner 2026-10-11: the particles drowned Goku). A thin shell hugging the SILHOUETTE: flat in depth (z 1.0), so almost every
    # particle sits at the sides, top and bottom of the outline rather than in front of the torso; small, dim, depth-tested and soft, so his body hides what is behind it
    'P_TrailGokuAura': [emitter('aura', shape='sphere', rate=1.8, radius=(3.8, 6.2, 1.0), life=26, dscale=0.45, size=(2.6, 0.3), c0=(0.45, 0.8, 1.0), c1=(0.9, 0.97, 1.0), scale=0.7),
                        emitter('core', shape='sphere', rate=0.3, radius=(3.2, 5.4, 0.8), life=14, dscale=0.1, size=(3.4, 1.8), c0=(0.3, 0.6, 1.0), c1=(0.8, 0.95, 1.0), scale=0.45)],
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
    for e, a in zip(PACKAGES['P_TrailGokuAura'], (0.6, 0.35)):   # dim, depth-tested, soft: the body hides what is behind it and nothing glows over the torso
        e['color']['alpha0'] = {'kind': 'constant', 'value': a}
        e['material'].update(depth_test=True, depth_write=False)
        e['material']['soft_particle'] = {'distance': 1.5, 'volume': 1}
    for name, emitters in PACKAGES.items():
        d = OUT / name
        png_soft(d / 'tex/ki_soft.png')
        doc = {'geno_fx': 1, 'name': name, 'source': {'format': 'original (ports/goku-xv2/tools/fx_build.py)', 'set': name},
               'space': {'forward': [0, 0, 1], 'up': [0, 1, 0]}, 'textures': [{'name': 'ki_soft', 'file': 'tex/ki_soft.png', 'w': 64, 'h': 64, 'source_format': 'rgba8', 'swizzle': 'rgba'}],
               'meshes': [], 'emitters': emitters}
        for e in emitters:
            if e.get('kind') == 'mesh' and not any(m['name'] == e['mesh'] for m in doc['meshes']):
                m = MESHES[e['mesh']]
                (d / 'mesh').mkdir(exist_ok=True)
                (d / 'mesh' / (e['mesh'] + '.json')).write_text(json.dumps(m), encoding='utf-8')
                doc['meshes'].append({'name': e['mesh'], 'file': 'mesh/%s.json' % e['mesh'], 'verts': len(m['position']), 'tris': len(m['indices']) // 3})
        for i, e in enumerate(doc['emitters']):
            e['order'] = i
        (d / f'{name}.gfx.json').write_text(json.dumps(doc, indent=1), encoding='utf-8')
    print(len(PACKAGES), 'effect packages in', OUT)


if __name__ == '__main__':
    main()
