"""Brawl FitMetaknight00 (+ cape article WpnMetaknightMantle) meshes -> DObj list on MK's own joint tree.

No retargeting: every Brawl bone is a Melee joint (skeleton.py), so a vertex keeps its bind-space position and
its bone weights 1:1 (<= 4 weights kept, renormalised, rounded to 1/100 so envelopes dedupe).
The 18 Brawl materials are 9 real ones + 9 '_ExtMtl' metal twins; the twins are not DObjs of their own (Brawl
switches the material when metal) and are dropped: Melee renders metal by swapping every fighter MObj for its
global metal material (ftMaterial: fp->is_metal -> ft_804D6580), so the same DObjs serve both.

DObj order (index = Melee DObj index used by the part-visibility tables):
  0..6  body (Brawl draw calls gated by TopN)      7..8 sword (SwordM)       9 open mantle ball (metaMantleM)
  10    closed cape (MantM)                         11..12 wings (WingM)       13 cape article (merged)
writes model/work/mesh.json
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); MODEL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import skeleton

ORDER = [('body', 'polygon0'), ('body', 'polygon1'), ('body', 'polygon4'), ('body', 'polygon5'), ('body', 'polygon7'),
         ('body', 'polygon10'), ('body', 'polygon16'), ('body', 'polygon12'), ('body', 'polygon13'), ('body', 'polygon15'),
         ('body', 'polygon8'), ('body', 'polygon17'), ('body', 'polygon18'), ('mantle', 'polygon0')]
# Brawl lighting / TEV per material (model/tools/brawl_matdump.exe <pac> node <material> / 'Shader N'), what Melee can use:
#  lit       C1ColorEnabled (False: the colour channel is the unlit material/vertex colour -> Melee RENDER_CONSTANT)
#  spec      channel 1 (C2) enabled with Specular attenuation: its material colour (only 'mask', Shader 3 adds it)
#  env       per EnvCamera ref: the Brawl TEV factor on that sphere map, baked into the Melee reflection texture
#            armer (Shader 1): tex + Color0(189,199,234) * siro, then x lighting;
#            kenn_akai (Shader 2): (tex * K3 0.5 + Color0(25,17,17) * Ref) * raster(vertex 0.5 unlit) * 4
BRAWL_MAT = {
    'medama': {'lit': False},
    'kenn_akai': {'lit': False, 'env': [2 * 25 / 255, 2 * 17 / 255, 2 * 17 / 255]},
    'armer': {'env': [189 / 255, 199 / 255, 234 / 255]},
    'mask': {'spec': [153, 138, 171]},
}
EXTRA_UVS = {'polygon5': 'eye_uvs.json'}        # body object -> brawl_matdump.exe uvs dump (all UV sets)
GROUP = {'TopN': 'body', 'SwordM': 'sword', 'metaMantleM': 'mantle_ball', 'MantM': 'closed_cape', 'WingM': 'wings', None: 'article_cape'}


def main(out):
    J, _ = skeleton.build()
    jidx = {j['name']: i for i, j in enumerate(J)}
    src = {'body': json.load(open(os.path.join(MODEL, 'brawl', 'FitMetaknight00.json'))),
           'mantle': json.load(open(os.path.join(MODEL, 'brawl', 'WpnMetaknightMantle00.json')))}
    mats = {k: {m['name']: m for m in d['materials']} for k, d in src.items()}
    # every UV set of the objects whose material samples more than TexCoord0 (the eyes: body on TexCoord2, one eye per
    # TexCoord0 / TexCoord1 island) - model_export.exe writes two sets only (brawl_matdump.exe uvs, same facepoint order)
    xuv = {}
    for on, fn in EXTRA_UVS.items():
        pth = os.path.join(MODEL, 'brawl', fn)
        if os.path.exists(pth): xuv[on] = json.load(open(pth))['fp']
    objs = {k: {o['name']: o for o in d['objects']} for k, d in src.items()}
    dobjs = []; stats = {'tris': 0, 'verts_trimmed': 0, 'max_weight_dropped': 0.0, 'max_infl_in': 0}
    for di, (sk, on) in enumerate(ORDER):
        o = objs[sk][on]; m = mats[sk][o['material']]
        name = lambda b: b if sk == 'body' else skeleton.ARTICLE_PREFIX + b
        tris = []
        fps = o['tris']
        uvx = xuv.get(on) if sk == 'body' else None
        if uvx is not None: assert len(uvx) == len(fps) and all(abs(a[6] - b[0]) < 1e-6 and abs(a[7] - b[1]) < 1e-6 for a, b in zip(fps, uvx)), on
        for t in range(0, len(fps), 3):
            tri = []
            for fi, fp in enumerate(fps[t:t + 3]):
                lst = sorted(((jidx[name(b)], w) for b, w in fp[14]), key=lambda x: -x[1])
                # merge duplicates (same joint listed twice)
                acc = {}
                for j, w in lst: acc[j] = acc.get(j, 0) + w
                lst = sorted(acc.items(), key=lambda x: -x[1])
                stats['max_infl_in'] = max(stats['max_infl_in'], len(lst))
                if len(lst) > 4:
                    stats['verts_trimmed'] += 1; stats['max_weight_dropped'] = max(stats['max_weight_dropped'], sum(x[1] for x in lst[4:]))
                    lst = lst[:4]
                s = sum(x[1] for x in lst); lst = [(j, w / s) for j, w in lst]
                r = [(j, round(w, 2)) for j, w in lst]; r = [(j, w) for j, w in r if w > 0]
                r[0] = (r[0][0], round(1.0 - sum(w for _, w in r[1:]), 2))
                v = {'p': fp[0:3], 'n': fp[3:6], 'uv': fp[6:8], 'w': r}
                if uvx is not None:
                    u = uvx[t + fi]; v['uvs'] = [u[k:k + 2] for k in range(0, len(u), 2)]
                tri.append(v)
            tris.append(tri)
        stats['tris'] += len(tris)
        dobjs.append({'index': di, 'source': sk, 'object': on, 'material': o['material'], 'visbone': o['visbone'],
                      'group': GROUP[o['visbone']] if sk == 'body' else 'article_cape',
                      'textures': [r['texture'] for r in m['refs']], 'palettes': [r['palette'] for r in m['refs']],
                      'wrap': [(r['u'], r['v']) for r in m['refs']], 'coords': [r['coord'] for r in m['refs']],
                      'maps': [r['map'] for r in m['refs']],
                      'lit': BRAWL_MAT.get(o['material'], {}).get('lit', True), 'spec': BRAWL_MAT.get(o['material'], {}).get('spec'),
                      'env': BRAWL_MAT.get(o['material'], {}).get('env'),
                      'cull': m['cull'], 'xlu': m['xlu'], 'tris': tris})
    joints = []
    for i, j in enumerate(J):
        W = np.array(j['world']); I = np.linalg.inv(W)
        joints.append({'name': j['name'], 'parent': j['parent_index'], 'scale': j['scale'],
                       'rot': [float(np.radians(x)) for x in j['rot_deg']], 'trans': j['trans'],
                       'ibm': I[:3, :].reshape(-1).tolist()})
    res = {'joints': joints, 'dobjs': dobjs, 'stats': stats}
    json.dump(res, open(out, 'w'))
    for d in dobjs:
        js = sorted({w[0] for t in d['tris'] for v in t for w in v['w']})
        print('DObj %2d %-7s %-9s %-13s %-12s tris %4d joints %d %s' % (d['index'], d['source'], d['object'], d['material'], d['group'], len(d['tris']), len(js), d['textures']))
    print(stats)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(MODEL, 'work', 'mesh.json'))
