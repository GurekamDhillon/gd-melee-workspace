"""Meta Knight's Melee joint tree (PlMk costumes, figatrees, parts table all share it).

Joint order = DFS order of the HSD JObj tree:
  0..76   FitMetaknight00 MDL0 bones, same indices as Brawl (so Brawl hitbox/hurtbox bone ids carry over 1:1)
  77..103 cape article WpnMetaknightMantle merged in: its HaveN/RotN/mantle* bones as a subtree of TopN
          (Brawl roots the article at the fighter origin; its TopN is dropped, HaveN becomes MtHaveN)
  104     TransN2 (Melee's secondary root-motion joint, role 53; MK has none - a still leaf under TopN)
Rest values: BrawlLib bind state (scale, rotation in degrees, translation). Joints get JOBJ_CLASSICAL_SCALING
(Brawl MDL0 'Standard' scaling rule, no segment scale compensation = HSD classical scaling).
Self-check: HSD FK (T * Rz Ry Rx * S) of these rest values vs BrawlLib's bind matrices.

writes model/work/skeleton.json
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(os.path.dirname(HERE))
MODEL = os.path.join(MK, 'model'); ANIM = os.path.join(MK, 'anim')
ARTICLE_PREFIX = 'Mt'          # article bones renamed MtHaveN, MtRotN, MtmantleC1H ... (unique names)


def srt(s, r, t):
    cx, sx, cy, sy, cz, sz = math.cos(r[0]), math.sin(r[0]), math.cos(r[1]), math.sin(r[1]), math.cos(r[2]), math.sin(r[2])
    R = np.array([[cy * cz, sx * sy * cz - cx * sz, cx * sy * cz + sx * sz],
                  [cy * sz, sx * sy * sz + cx * cz, cx * sy * sz - sx * cz],
                  [-sy, sx * cy, cx * cy]])
    M = np.eye(4); M[:3, :3] = R @ np.diag(s); M[:3, 3] = t
    return M


def build():
    body = json.load(open(os.path.join(ANIM, 'brawl', 'bones.json')))
    mant = json.load(open(os.path.join(ANIM, 'brawl_mantle', 'bones.json')))
    bexp = {b['name']: b for b in json.load(open(os.path.join(MODEL, 'brawl', 'FitMetaknight00.json')))['bones']}
    mexp = {b['name']: b for b in json.load(open(os.path.join(MODEL, 'brawl', 'WpnMetaknightMantle00.json')))['bones']}
    J = []
    for b in body:
        J.append({'name': b['name'], 'brawl': b['name'], 'src': 'body', 'parent': b['parent'],
                  'scale': b['scale'], 'rot_deg': b['rot'], 'trans': b['trans'], 'bind': bexp[b['name']]['bind']})
    for b in mant:
        if b['name'] == 'TopN': continue
        par = 'TopN' if b['parent'] == 'TopN' else ARTICLE_PREFIX + b['parent']
        J.append({'name': ARTICLE_PREFIX + b['name'], 'brawl': b['name'], 'src': 'mantle_article', 'parent': par,
                  'scale': b['scale'], 'rot_deg': b['rot'], 'trans': b['trans'], 'bind': mexp[b['name']]['bind']})
    J.append({'name': 'TransN2', 'brawl': None, 'src': 'added', 'parent': 'TopN', 'scale': [1, 1, 1], 'rot_deg': [0, 0, 0],
              'trans': [0, 0, 0], 'bind': None})
    idx = {j['name']: i for i, j in enumerate(J)}
    # DFS order check: children of a joint are listed in order after it -> rebuild DFS and compare
    kids = {i: [] for i in range(len(J))}
    for i, j in enumerate(J):
        j['parent_index'] = idx[j['parent']] if j['parent'] else -1
        if j['parent']: kids[idx[j['parent']]].append(i)
    order = []
    def dfs(i):
        order.append(i)
        for c in kids[i]: dfs(c)
    dfs(0)
    assert order == list(range(len(J))), 'joint list is not in DFS order'
    worst = 0.0; depth = {}
    for i, j in enumerate(J):
        L = srt(j['scale'], [math.radians(x) for x in j['rot_deg']], j['trans'])
        p = j['parent_index']
        j['world'] = (L if p < 0 else np.array(J[p]['world']) @ L).tolist()
        depth[i] = 0 if p < 0 else depth[p] + 1
        j['depth'] = depth[i]
        if j['bind'] is not None:
            B = np.array(j['bind']).reshape(4, 4).T
            e = float(np.abs(B - np.array(j['world'])).max()); j['fk_err'] = e; worst = max(worst, e)
        j['children'] = kids[i]
    return J, worst


if __name__ == '__main__':
    J, worst = build()
    out = {'joint_count': len(J), 'max_depth': max(j['depth'] for j in J), 'fk_vs_brawllib_bind_max_err': worst,
           'order': 'DFS; 0..76 = FitMetaknight00 bone index; 77..103 merged cape article; 104 TransN2',
           'joints': [{k: v for k, v in j.items() if k not in ('bind',)} for j in J]}
    json.dump(out, open(os.path.join(MODEL, 'work', 'skeleton.json'), 'w'), indent=1)
    print('joints', len(J), 'max depth', out['max_depth'], 'FK vs BrawlLib bind max err', worst)
    for i, j in enumerate(J):
        if j.get('fk_err', 0) > 1e-3: print('  mismatch', i, j['name'], j['fk_err'])
