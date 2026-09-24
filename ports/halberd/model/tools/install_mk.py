"""Install Meta Knight's own model + animations (Phases 2 and 3) into a metaknight-slot mod folder.

    python model/tools/install_mk.py <mod dir>        e.g. a COPY of mods-slot/metaknight-slot (never the original
                                                       while Phase 1 owns it; this script edits files/ in place)

Needs (built by model/tools/build_model.py and anim/tools/mk_anim.py):
  model/out/PlBm{Nr,Ye,Bu,Re,Gr,Wh}.dat   costumes: 105-joint tree, 14 DObjs, matanim (public symbols
                                           PlyMetaknight5K_Share_joint / PlyMetaknight5K_Share_matanim_joint)
  anim/out/PlBmAJ.dat + motion_rows.json  MK clips only (one figatree per distinct clip)

What it does to <mod>/files (append-only writers, as the Brawl Kirby tools: existing bytes and offsets stay put):
 1. copies the six costume files and PlBmAJ.dat in.
 2. PlBm.dat (Phase 1's Kirby-clone fighter data), ftData fields that name joints are rewritten for MK's tree:
      x8   model-part visibility (2 models: cape 0 closed/1 wings/2 article cape; body 0 body/1 mantle ball;
           sword DObjs always drawn), costume TObj list [3,3] (eye TexAnim), part bytes item 40 / shield 74 / head 8 /
           feet 68, 72
      x1C  3 part-anim slots, all on HeadItmN (8, a mesh-less leaf) with still AnimJoints: Kirby's clone code
           (item pickup, mouth) keeps working without twisting MK's hand/sword
      x20  shield pose = MK's Brawl Guard frame 0 (105-joint HSD_Joint tree)
      x30  MK's 9 Brawl hurtboxes (bone ids are MK joints = Brawl bone ids; Brawl stretch = Melee 2nd point)
      x34/x38/x44/x54/x58  centre bubble, coin spheres, ECB bones, GFX body-part bones, leg IK: Kirby's roles on
           MK's joints
      x5C  metal/parts model = MK's tree with no DObjs (metal draws the normal DObjs with Melee's metal MObj)
      motion table: every Kirby row with an animation -> its MK clip's offset/size in PlBmAJ.dat; rows that share a
           clip get the clip's symbol as their name (motion_rows.json rename_rows)
 3. PlCo.dat: parts table of the slot's internal id -> MK's (105 joints, roles below); insert-slot table [5] -> NULL
    (Kirby's copy-hat slots must not reserve parts in MK's tree).
 4. MxDt.dat: the slot row's anim file -> PlBmAJ.dat, costumes -> PlBm<cc>.dat + MK symbols (brawl-kirby's
    mxdt_clone.py, run with source = destination row, on this MxDt).
Writes <mod>/files/../MK_INSTALL.json (what was changed).
"""
import os, sys, json, struct, shutil, subprocess, io, contextlib, runpy, math
HERE = os.path.dirname(os.path.abspath(__file__)); MODEL = os.path.dirname(HERE); MK = os.path.dirname(MODEL)
EXP = os.path.join(os.path.dirname(os.path.dirname(MK)), "experiment"); ANIM = os.path.join(MK, 'anim'); ROOT = os.path.dirname(EXP)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'mex_port')); sys.path.insert(0, os.path.join(EXP, 'brawl-kirby', 'tools'))
import mex_hsd
ISO = "C:/iso/SSBM ACE Build v2.0.0.iso"
COLORS = ['Nr', 'Ye', 'Bu', 'Re', 'Gr', 'Wh']
SCRIPTS_MODE = 'phase1'
VIS = True
JOINT_SYM = 'PlyMetaknight5K_Share_joint'; MAT_SYM = 'PlyMetaknight5K_Share_matanim_joint'

# ------------------------------------------------------------------ MK roles (PlCo parts table)
# role (Melee common-part id, naming of brawl-kirby/analysis/melee_model.json) -> MK joint. 255 = none. Every role
# Kirby maps is mapped here too (Kirby-clone code only asks for roles Kirby has); the 'A' pre-joints MK lacks share
# the main joint. joint_to_part holds each joint's primary role (used when another fighter's thrown animation is
# remapped onto MK).
ROLES = ['Top', 'Trans', 'XRot', 'YRot', 'Hip', 'Waist', 'LLegA', 'LLeg', 'LKnee', 'LFootA', 'LFoot', 'RLegA', 'RLeg',
         'RKnee', 'RFootA', 'RFoot', 'WaistB', 'Bust', 'LClavicle', 'LShoulderA', 'LShoulder', 'LArm', 'LHand',
         'LIndex1', 'LIndex2', 'LMiddle1', 'LMiddle2', 'LRing1', 'LRing2', 'LPinky1', 'LPinky2', 'LHave', 'LThumb1',
         'LThumb2', 'NeckN', 'HeadN', 'RClavicle', 'RShoulderA', 'RShoulder', 'RArm', 'RHand', 'RIndex1', 'RIndex2',
         'RMiddle1', 'RMiddle2', 'RRing1', 'RRing2', 'RPinky1', 'RPinky2', 'RHave', 'RThumb1', 'RThumb2', 'Throw', 'Extra']
ROLE2BONE = {'Top': 'TopN', 'Trans': 'TransN', 'XRot': 'XRotN', 'YRot': 'YRotN', 'Hip': 'HipN', 'Waist': 'BodyN',
             'LLegA': 'LLegJ', 'LLeg': 'LLegJ', 'LKnee': 'LKneeJ', 'LFootA': 'LFootJ', 'LFoot': 'LFootJ',
             'RLegA': 'RLegJ', 'RLeg': 'RLegJ', 'RKnee': 'RKneeJ', 'RFootA': 'RFootJ', 'RFoot': 'RFootJ',
             'LClavicle': 'LShoulderN', 'LShoulderA': 'LShoulderJ', 'LShoulder': 'LShoulderJ', 'LArm': 'LArmJ',
             'LHand': 'LHandN', 'LHave': 'LHaveN', 'HeadN': 'BodyBN',
             'RClavicle': 'RShoulderN', 'RShoulderA': 'RShoulderJ', 'RShoulder': 'RShoulderJ', 'RArm': 'RArmJ',
             'RHand': 'RHandN', 'RHave': 'RHaveN', 'Throw': 'ThrowN', 'Extra': 'TransN2'}
PRIMARY_SKIP = {'LLegA', 'LFootA', 'RLegA', 'RFootA', 'LShoulderA', 'RShoulderA'}   # not the joint's primary role


class Writer:
    """Append-only HSD archive editor: data section grows at the end, relocation table rebuilt, tail kept."""
    def __init__(self, raw):
        self.ar = mex_hsd.Archive(raw); self.data = bytearray(self.ar.data); self.relocs = set(self.ar.reloc_offsets)
    def u32(self, o): return struct.unpack('>I', self.data[o:o + 4])[0]
    def put(self, o, v): self.data[o:o + 4] = struct.pack('>I', v & 0xFFFFFFFF)
    def ptr(self, o, target):
        if target: self.put(o, target); self.relocs.add(o)
        else: self.put(o, 0); self.relocs.discard(o)
    def alloc(self, b, align=4):
        while len(self.data) % align: self.data.append(0)
        at = len(self.data); self.data.extend(b); return at
    def cstr(self, s): return self.alloc(s.encode() + b'\0', 4)
    def str_at(self, o): return self.data[o:self.data.index(b'\0', o)].decode('latin1')
    def save(self, path):
        while len(self.data) % 4: self.data.append(0)
        rel = sorted(self.relocs); tail = self.ar.raw[self.ar.o_public:]
        body = bytes(self.data) + b''.join(struct.pack('>I', r) for r in rel) + tail
        hdr = struct.pack('>5I', 0x20 + len(body), len(self.data), len(rel), self.ar.nb_public, self.ar.nb_extern) + self.ar.raw[0x14:0x20]
        open(path, 'wb').write(hdr + body)


def skeleton():
    return json.load(open(os.path.join(MODEL, 'work', 'skeleton.json')))['joints']


def joint_tree(w, J, pose=None):
    """Write an HSD_Joint tree (0x40 per joint, DFS order = J order). pose: {name: [sx,sy,sz, rx,ry,rz(deg), tx,ty,tz]}."""
    offs = [w.alloc(bytes(0x40), 4) for _ in J]
    for i, j in enumerate(J):
        o = offs[i]
        v = (pose or {}).get(j['name']) or (list(j['scale']) + list(j['rot_deg']) + list(j['trans']))
        w.put(o + 4, 1 << 3)                                    # JOBJ_CLASSICAL_SCALING
        if j['children']: w.ptr(o + 8, offs[j['children'][0]])
        sib = [c for c in J[j['parent_index']]['children']] if j['parent_index'] >= 0 else [0]
        k = sib.index(i)
        if k + 1 < len(sib): w.ptr(o + 0xC, offs[sib[k + 1]])
        rot = [math.radians(x) for x in v[3:6]]
        w.data[o + 0x14:o + 0x38] = struct.pack('>9f', *rot, *v[0:3], *v[6:9])
    return offs[0]


def parts_table(J):
    idx = {j['name']: i for i, j in enumerate(J)}
    p2j = [idx[ROLE2BONE[r]] if r in ROLE2BONE else 255 for r in ROLES]
    j2p = [255] * len(J)
    for ri, r in enumerate(ROLES):
        if r in ROLE2BONE and r not in PRIMARY_SKIP: j2p[idx[ROLE2BONE[r]]] = ri
    return j2p, p2j


def patch_ftdata(path, report):
    J = skeleton(); idx = {j['name']: i for i, j in enumerate(J)}
    w = Writer(open(path, 'rb').read())
    ftsym = [s for s, _ in w.ar.publics if s.startswith('ftData')][0]
    fd = w.ar.public(ftsym)
    rep = report.setdefault('PlBm.dat', {'ftData': ftsym})
    # ---- x8: model-part visibility ------------------------------------------------------------------
    body, sword, ball, cape, wings, art = list(range(0, 7)), [7, 8], [9], [10], [11, 12], [13]
    # States of one model must not share DObjs: ftParts_80074B6C shows the current state's list and HIDES every other
    # state's, in state order, so an overlapping later state re-hides what was just shown (first in-game run: Brawl's
    # 'body+sword+ball' group hid the body). The sword (7, 8) is in no list: always drawn (Brawl hides it only for the
    # Lose pose). Kirby's clone OnDeath sets both models to state 0 at spawn.
    # model 0 state 3 is EMPTY: no cape at all (Brawl hides the cape article while the cape switch is on it: up taunt,
    # the cape vanish, Win1's end) - anim/tools/mk_vis.py emits ModelVis(0, 3) for those frames
    models = [[cape, wings, art, []],                                      # model 0: cape switch (Brawl BoneSwitch2)
              [body, ball]]                                                # model 1: body / mantle ball (Brawl BoneSwitch1)
    def lookups():
        arr = bytearray(8 * len(models)); at = w.alloc(arr)
        for m, states in enumerate(models):
            st = w.alloc(bytes(8 * len(states)))
            for s, dl in enumerate(states):
                lst = w.alloc(bytes(dl) + bytes((-len(dl)) % 4))
                w.put(st + 8 * s, len(dl)); w.ptr(st + 8 * s + 4, lst)
            w.put(at + 8 * m, len(states)); w.ptr(at + 8 * m + 4, st)
        return at
    hi = lookups()
    NROWS = 8                                                   # costume rows (6 used; spare rows -> row 0)
    vt = w.alloc(bytes(16 * NROWS))
    w.ptr(vt + 0, hi); w.ptr(vt + 4, hi); w.ptr(vt + 12, hi)     # hi, lo, (metal parts model: none), metal main = hi
    # costume TObj list = the two eye layers (global TObj indices written by mkbuild: [Texture0 eye, Texture1 eye]); the
    # eye-state SetTexAnim commands (tools/build_mk_visuals.py) set tex-anim 0 and 1 together
    eye = json.load(open(os.path.join(MODEL, 'work', 'PlBmNr_build.json'))).get('eye_tobjs', [3, 3])
    tl = w.alloc(struct.pack('>HH', *eye))
    tt = w.alloc(bytes(4 * NROWS)); w.ptr(tt, tl)
    x8 = w.alloc(bytes(0x18))
    w.put(x8, len(models)); w.ptr(x8 + 4, vt); w.put(x8 + 8, 2); w.ptr(x8 + 0xC, tt)
    w.data[x8 + 0x10:x8 + 0x15] = bytes([idx['RHaveN'], idx['ThrowN'], idx['HeadItmN'], idx['LFootJ'], idx['RFootJ']])
    w.ptr(fd + 8, x8)
    rep['x8'] = {'model_num': 2, 'models': models, 'costume_rows': NROWS, 'lo': 'same as hi', 'metal_parts': None,
                 'metal_main': 'same as hi', 'costume_tobjs': eye,
                 'parts_item_shield_head_lfoot_rfoot': list(w.data[x8 + 0x10:x8 + 0x15])}
    # ---- x1C: part anims -> HeadItmN, still AnimJoints -------------------------------------------------
    still = []
    for _ in range(4):
        aobj = w.alloc(struct.pack('>IfII', 0, 1.0, 0, 0))
        aj = w.alloc(bytes(0x14)); w.ptr(aj + 8, aobj); still.append(aj)
    x1c = w.alloc(bytes(12))
    for e in range(3):
        lst = w.alloc(bytes([idx['HeadItmN'], 0, 0, 0]))
        an = w.alloc(bytes(16))
        for k in range(4): w.ptr(an + 4 * k, still[k])
        ent = w.alloc(struct.pack('>HH', idx['HeadItmN'], 1) + bytes(8))
        w.ptr(ent + 4, lst); w.ptr(ent + 8, an); w.ptr(x1c + 4 * e, ent)
    w.ptr(fd + 0x1C, x1c)
    rep['x1C'] = '3 part-anim slots on HeadItmN (%d), 4 still AnimJoints each' % idx['HeadItmN']
    # ---- x20 shield pose (Brawl Guard frame 0), x5C metal/parts model --------------------------------------
    sys.path.insert(0, os.path.join(ANIM, 'tools')); import mk_anim
    g = mk_anim.merged('Guard'); pose = {bn: bd['baked'][0] for bn, bd in g['bones'].items()}
    sp = joint_tree(w, J, pose)
    x20 = w.alloc(bytes(8)); w.ptr(x20, sp)
    w.ptr(fd + 0x20, x20)
    w.ptr(fd + 0x5C, joint_tree(w, J))
    rep['x20'] = 'shield pose: %d-joint tree, Brawl Guard frame 0 (incl. cape article bones)' % len(J)
    rep['x5C'] = 'metal/parts model: %d-joint tree, no DObjs' % len(J)
    # ---- x30 hurtboxes ------------------------------------------------------------------------------------
    B = json.load(open(os.path.join(MK, 'analysis', 'brawl_metaknight.json')))
    ZONE = {'low': 0, 'mid': 1, 'high': 2}
    hb = bytearray()
    for h in B['hurtboxes']:
        hb += struct.pack('>3i7f', h['bone'], ZONE[h['zone']], 1, *h['offset'], *h['stretch'], h['radius'])
    arr = w.alloc(bytes(hb)); x30 = w.alloc(bytes(8)); w.put(x30, len(B['hurtboxes'])); w.ptr(x30 + 4, arr)
    w.ptr(fd + 0x30, x30)
    rep['x30'] = [{'bone': h['bone'], 'name': h['bone_name'], 'type': h['zone'], 'p1': h['offset'], 'p2': h['stretch'], 'r': h['radius']} for h in B['hurtboxes']]
    # ---- in-place joint fields (Kirby roles -> MK joints) -------------------------------------------------
    x34 = w.u32(fd + 0x34); w.put(x34, idx['HipN'])
    x38 = w.u32(fd + 0x38); w.put(x38, idx['HipN'])          # coin sphere 0 (Kirby: Hip); sphere 1 stays on TopN (0)
    x44 = w.u32(fd + 0x44)
    w.data[x44:x44 + 12] = struct.pack('>6h', idx['BodyBN'], idx['RHaveN'], idx['RHaveN'], idx['RToeN'], idx['LToeN'], 0)
    x54 = w.u32(fd + 0x54)
    w.data[x54:x54 + 20] = struct.pack('>5i', idx['BodyBN'], idx['RArmJ'], idx['LKneeJ'], idx['RKneeJ'], idx['LArmJ'])
    x58 = w.u32(fd + 0x58)
    for o, (r, l) in zip((0, 8, 0x10, 0x1C, 0x24), (('RLegJ', 'LLegJ'), ('RKneeJ', 'LKneeJ'), ('RFootJ', 'LFootJ'),
                                                     ('RShoulderJ', 'LShoulderJ'), ('RArmJ', 'LArmJ'))):
        w.data[x58 + o] = idx[r]; w.data[x58 + o + 1] = idx[l]
    L = lambda n: math.dist([0, 0, 0], J[idx[n]]['trans'])
    w.data[x58 + 4:x58 + 8] = struct.pack('>f', L('LKneeJ')); w.data[x58 + 0xC:x58 + 0x10] = struct.pack('>f', L('LFootJ'))
    rep['in_place'] = {'x34_center': idx['HipN'], 'x38_coin0': idx['HipN'],
                       'x44_ecb': [idx['BodyBN'], idx['RHaveN'], idx['RHaveN'], idx['RToeN'], idx['LToeN'], 0],
                       'x54_gfx_parts': [idx['BodyBN'], idx['RArmJ'], idx['LKneeJ'], idx['RKneeJ'], idx['LArmJ']],
                       'x58_ik': 'legs/knees/feet/shoulders/arms R,L = MK joints; leg %.3f knee %.3f (other IK floats Kirby\'s)' % (L('LKneeJ'), L('LFootJ'))}
    # ---- motion table -----------------------------------------------------------------------------------
    mr = json.load(open(os.path.join(ANIM, 'out', 'motion_rows.json')))
    kr = {r['index']: r for r in json.load(open(os.path.join(EXP, 'brawl-kirby', 'analysis', 'melee_kirby.json')))['motion_table']}
    mt = w.u32(fd + 0xC)
    pointed = renamed = 0; mism = []
    sym_str = {}
    for c in mr['clips']:
        for r in c['rows']:
            o = mt + r * 0x18
            name = w.str_at(w.u32(o)) if o in w.relocs else None
            if name != kr[r]['figatree']: mism.append((r, name, kr[r]['figatree']))
            if name != c['symbol']:
                if c['symbol'] not in sym_str: sym_str[c['symbol']] = w.cstr(c['symbol'])
                w.ptr(o, sym_str[c['symbol']]); renamed += 1
            w.put(o + 4, c['offset']); w.put(o + 8, c['size']); pointed += 1
    patch_scripts(w, fd, SCRIPTS_MODE, rep)
    if VIS: apply_vis(w, fd, rep)
    # ---- demo table (x14): the port counts an m-ex fighter's demo motions up to the first entry with no script
    # (ftdata.c, "kind %d has %d demo motions"); Kirby's table has a script-less hole at entry 4, so every Kirby
    # clone ended up with 4 demo motions and the results screen asserted "Demo Status error" (Win3 = 5, Lose = 9).
    # Give the holes an End-only script (they have no figatree either, so nothing plays them).
    x14 = w.u32(fd + 0x14); end = None; holes = []
    for i in range(18):
        o = x14 + i * 0x18 + 0xC
        if o not in w.relocs:
            if end is None: end = w.alloc(bytes(4))
            w.ptr(o, end); holes.append(i)
    rep['demo_table_holes_given_end_script'] = holes
    # ---- results screen: MK's own demo motions (anim/out/GmRstMBm.dat, mk_anim.build_demo) on rows 0-3, 5-9 of x14, each
    # with a script of its Brawl visibility (vis_events.json 'demo': explicit frame-0 states, a Wait loop restates the end
    # of its intro) and eye states (SetTexAnim, eye_states.json), then End. Kirby's demo scripts (his voice, his eye
    # frames) are replaced. MxDt's result file / demo strings are pointed at the new file in patch_mxdt_demo.
    dr = os.path.join(ANIM, 'out', 'demo_rows.json')
    if os.path.exists(dr):
        D = json.load(open(dr)); V = {x['index']: x for x in json.load(open(os.path.join(ANIM, 'vis_events.json'))).get('demo', [])}
        E = json.load(open(os.path.join(ANIM, 'out', 'eye_states.json')))['clips']
        MV = lambda i, v: (31 << 26) | ((i & 0x7F) << 19) | (v & 0x7FFFF)
        TA = lambda st: (40 << 26) | (1 << 25) | (0 << 18) | (1 << 11) | st
        drep = []
        for r in D['rows']:
            o = x14 + r['index'] * 0x18
            w.put(o + 4, r['offset']); w.put(o + 8, r['size'])
            ev = [(e['frame'], 0, MV(e['index'], e['value'])) for e in V.get(r['index'], {}).get('melee_modelvis', [])]
            ev += [(f, 1, TA(st)) for f, st in E.get(r['brawl_clip'], {}).get('events', []) if f < r['frames']]
            ev.sort(); words = []; cur = 0
            for f, _, wd in ev:
                if f > cur: words.append((2 << 26) | f); cur = f
                words.append(wd)
            sc = w.alloc(b''.join(struct.pack('>I', x) for x in words + [0]))
            w.ptr(o + 0xC, sc)
            drep.append({'index': r['index'], 'name': w.str_at(w.u32(o)) if o in w.relocs else None, 'clip': r['brawl_clip'],
                         'offset': r['offset'], 'size': r['size'], 'frames': r['frames'], 'script_words': len(words) + 1,
                         'modelvis': len([e for e in ev if e[1] == 0]), 'eye_events': len([e for e in ev if e[1] == 1])})
        rep['demo_motions'] = {'file': D['file'], 'symbol': D['symbol'], 'rows': drep}
    rep['motion_table'] = {'offset': hex(mt), 'rows_pointed': pointed, 'rows_renamed': renamed,
                           'rows_not_kirby_named_before': mism[:20], 'n_mismatch': len(mism)}
    w.save(path)
    return rep


# ------------------------------------------------------------------ scripts: Kirby joint spaces -> MK joints
FLOW_LEN = [1, 1, 1, 1, 1, 2, 1, 2, 1, 1]            # ops 0..9 (5 subroutine and 7 goto carry a pointer)
OP_LEN = [5, 5, 1, 1, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1, 1, 7, 4, 1, 1, 1, 1,
          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 2, 1, 4]   # ops 10..58 (ftaction.c ftAction_803C0870)


def kirby_spaces():
    """Kirby's two joint numberings, both -> MK joint:
    slot  = Kirby PART SLOT (fp->parts index: 46 JObjs + 13 copy-hat placeholders) - what Kirby's own scripts use
    joint = Kirby JObj index (brawl-kirby/phase2/bone_map.json melee_joint) - what Phase 1 wrote into hitboxes"""
    J = skeleton(); idx = {j['name']: i for i, j in enumerate(J)}
    _, p2j = parts_table(J)
    raw = mex_hsd.Gcm(ISO).read('PlCo.dat'); ar = mex_hsd.Archive(raw); r = ar.public('ftLoadCommonData')
    kt = ar.u32(ar.u32(r + 16) + 4 * 4); j2p = ar.data[ar.u32(kt):ar.u32(kt) + ar.u32(kt + 8)]
    k5 = ar.u32(ar.u32(r + 20) + 4 * 4); skips = sorted(ar.data[ar.u32(k5) + 4 * i] for i in range(ar.u32(k5 + 4)))
    bm = {m['melee_joint']: m['brawl_bone'] for m in json.load(open(os.path.join(EXP, 'brawl-kirby', 'phase2', 'bone_map.json')))['map']}
    def by_name(kj):
        n = bm.get(kj)
        return idx[n] if n in idx else (idx['BodyBN'] if n and n.startswith(('Mouth', 'Cheek', 'Hukumi')) else 0)
    joint = {kj: by_name(kj) for kj in bm}
    slot = {}
    for s_ in range(len(j2p)):
        if s_ in skips: continue
        role = j2p[s_]
        mj = p2j[role] if role != 255 and p2j[role] != 255 else None
        if mj is None: mj = joint.get(s_ - sum(1 for k in skips if k < s_), 0)
        slot[s_] = mj
    return slot, joint


def patch_scripts(w, fd, mode, rep):
    """mode 'phase1': hitbox bones are Kirby JObj indices (Phase 1's writer), GFX / hurtbox-state / wind bones are
    Kirby part slots (inherited Kirby events). 'mk': scripts already use MK joints - nothing to do."""
    if mode == 'mk': rep['scripts'] = 'mode mk: left as is'; return
    slot, joint = kirby_spaces()
    J = skeleton(); hurt = {h['bone'] for h in json.load(open(os.path.join(MK, 'analysis', 'brawl_metaknight.json')))['hurtboxes']}
    def to_hurt(j):
        while j not in hurt and j > 0: j = J[j]['parent_index']
        return j if j in hurt else 6
    mt = w.u32(fd + 0xC)
    targets = sorted({w.u32(r) for r in w.ar.reloc_offsets} | {len(w.ar.data)})
    n = (min(t for t in targets if t > mt) - mt) // 0x18                   # rows up to the next pointed-to struct
    starts = [w.u32(mt + r * 0x18 + 0xC) for r in range(n) if (mt + r * 0x18 + 0xC) in w.relocs]
    done = set(); stats = {'hitbox': 0, 'gfx': 0, 'hurt_state': 0, 'wind': 0, 'unmapped': []}
    def walk(o):
        while o not in done and o + 4 <= len(w.data):
            done.add(o); word = w.u32(o); op = word >> 26
            if op < 10:
                if op in (0, 6): return
                if op in (5, 7):
                    t = w.u32(o + 4) if (o + 4) in w.relocs else 0
                    if t: walk(t)
                    if op == 7: return
                o += 4 * FLOW_LEN[op]; continue
            if op - 10 >= len(OP_LEN): return
            if op == 11 and not (word >> 10) & 1:
                b = (word >> 11) & 0xFF; nb = joint.get(b, b)
                w.put(o, (word & ~(0xFF << 11)) | (nb << 11)); stats['hitbox'] += 1
            elif op == 10 and not (word >> 17) & 1 and not (word >> 15) & 1:
                b = (word >> 18) & 0xFF; nb = slot.get(b)
                if nb is None: stats['unmapped'].append(('gfx', b)); nb = 0
                w.put(o, (word & ~(0xFF << 18)) | (nb << 18)); stats['gfx'] += 1
            elif op == 28:
                b = (word >> 18) & 0xFF; nb = to_hurt(slot.get(b, 6))
                w.put(o, (word & ~(0xFF << 18)) | (nb << 18)); stats['hurt_state'] += 1
            elif op == 58:
                b = word & 0xFF; nb = slot.get(b, 0)
                w.put(o, (word & ~0xFF) | nb); stats['wind'] += 1
            o += 4 * OP_LEN[op - 10]
    for s_ in starts: walk(s_)
    stats['scripts_walked_rows'] = len(starts); stats['commands_seen'] = len(done)
    rep['scripts'] = stats


def apply_vis(w, fd, rep):
    """anim/vis_events.json -> ModelVis commands in the rows' scripts (stopgap until the script translator emits them):
    each row with suggestions gets a COPY of its script with the Brawl Model Changer frames inserted (timers split
    where needed), its own ModelVis(0/1, *) commands dropped, and the row pointed at the copy. Frames after a
    loop / subroutine / 'wait for animation' in the script are placed approximately; frames after a Goto are dropped."""
    vis = json.load(open(os.path.join(ANIM, 'vis_events.json')))
    mt = w.u32(fd + 0xC)
    cache = {}; out = {'rows': 0, 'approx_rows': [], 'dropped': []}
    MV = lambda i, v: (31 << 26) | ((i & 0x7F) << 19) | (v & 0x7FFFF)
    for c in vis['clips']:
        ev = sorted({(e['frame'], e['index'], e['value']) for e in c['melee_modelvis_suggested']})
        if not ev: continue
        idxs = {i for _, i, _ in ev}
        for r in c['rows']:
            po = mt + r * 0x18 + 0xC
            if po not in w.relocs:                                # no script: one made of the events alone
                if ('none', tuple(ev)) not in cache:
                    ws = []; fr = 0
                    for f, i, v in ev:
                        if f > fr: ws.append((2 << 26) | f); fr = f
                        ws.append(MV(i, v))
                    cache[('none', tuple(ev))] = w.alloc(b''.join(struct.pack('>I', x) for x in ws + [0]))
                w.ptr(po, cache[('none', tuple(ev))]); out['rows'] += 1; out.setdefault('rows_given_a_script', []).append(r)
                continue
            src = w.u32(po); key = (src, tuple(ev))
            if key in cache: w.ptr(po, cache[key]); out['rows'] += 1; continue
            words = []; pend = list(ev); frame = 0; approx = False; o = src; seen = 0
            def emit_until(f_lim, timer_async):
                nonlocal frame
                while pend and pend[0][0] < f_lim:
                    f, i, v = pend.pop(0)
                    if f > frame:
                        words.append(((2 << 26) | f, False) if timer_async else ((1 << 26) | (f - frame), False)); frame = f
                    words.append((MV(i, v), False))
            while True:
                seen += 1
                if seen > 4000: break
                word = w.u32(o); op = word >> 26
                while pend and pend[0][0] <= frame:
                    f, i, v = pend.pop(0); words.append((MV(i, v), False))
                if op == 0:
                    emit_until(c['frames'], True); words.append((word, False)); break
                if op == 1:
                    n = word & 0x3FFFFFF; start = frame
                    emit_until(start + n, False)
                    if frame < start + n: words.append(((1 << 26) | (start + n - frame), False))
                    frame = start + n; o += 4; continue
                if op == 2:
                    n = word & 0x3FFFFFF
                    emit_until(n, True)
                    words.append((word, False)); frame = max(frame, n); o += 4; continue
                if op == 7:
                    out['dropped'] += [(r, f, i, v) for f, i, v in pend]; pend = []
                    words.append((word, False)); words.append((w.u32(o + 4), (o + 4) in w.relocs)); break
                if op in (3, 4, 5, 8): approx = True
                if op == 31 and ((word >> 19) & 0x7F) in idxs:
                    o += 4; continue                                  # the row's own ModelVis for that model: replaced
                ln = FLOW_LEN[op] if op < 10 else (OP_LEN[op - 10] if op - 10 < len(OP_LEN) else 1)
                for k in range(ln): words.append((w.u32(o + 4 * k), (o + 4 * k) in w.relocs))
                o += 4 * ln
            at = w.alloc(bytes(4 * len(words)))
            for k, (v, isp) in enumerate(words):
                if isp: w.ptr(at + 4 * k, v)
                else: w.put(at + 4 * k, v)
            cache[key] = at; w.ptr(po, at); out['rows'] += 1
            if approx: out['approx_rows'].append(r)
    rep['modelvis'] = out


def patch_plco(path, kid, report):
    J = skeleton(); j2p, p2j = parts_table(J)
    w = Writer(open(path, 'rb').read())
    r = w.ar.public('ftLoadCommonData')
    t4 = w.u32(r + 16); t5 = w.u32(r + 20)
    a_j2p = w.alloc(bytes(j2p) + bytes((-len(j2p)) % 4))
    a_p2j = w.alloc(bytes(p2j) + b'\xff' * (64 - len(p2j)))
    ent = w.alloc(bytes(12)); w.ptr(ent, a_j2p); w.ptr(ent + 4, a_p2j); w.put(ent + 8, len(J))
    w.ptr(t4 + 4 * kid, ent)
    had5 = (t5 + 4 * kid) in w.relocs
    w.ptr(t5 + 4 * kid, 0)
    w.save(path)
    report['PlCo.dat'] = {'internal_id': kid, 'parts_num': len(J), 'insert_slots_table5': 'NULL (was %s)' % ('set' if had5 else 'NULL'),
                          'part_to_joint': {ROLES[i]: (p2j[i], J[p2j[i]]['name'] if p2j[i] != 255 else None) for i in range(len(ROLES))},
                          'joint_to_part': {J[i]['name']: ROLES[v] for i, v in enumerate(j2p) if v != 255}}


def find_row(mxdt, pl):
    ar = mex_hsd.Archive(open(mxdt, 'rb').read()); d = ar.data
    u = lambda o: struct.unpack('>I', d[o:o + 4])[0]
    base = ar.public('mexData'); ft = u(base + 8); meta = u(base)
    nk, ne = struct.unpack('>ii', d[meta + 4:meta + 12])
    plt = u(ft + 4)
    for k in range(nk):
        p = u(plt + 8 * k)
        if p and d[p:d.index(b'\0', p)].decode('latin1') == pl:
            # external id: the name table entry the clone tool wrote for this row (search by insignia-free rule:
            # ext id = k - 1 for the rows after Kirby in ACE's layout; confirm with the costume_info table shape)
            return k
    raise SystemExit('no MxDt row with pl file %s' % pl)


def patch_mxdt(path, kid, eid, report):
    raw = open(path, 'rb').read()
    class _Gcm:
        def __init__(self, iso): pass
        def read(self, name): return raw if name == 'MxDt.dat' else mex_hsd.Gcm(ISO).read(name)
    real = mex_hsd.Gcm; mex_hsd.Gcm = _Gcm
    ar = mex_hsd.Archive(raw); d = ar.data; u = lambda o: struct.unpack('>I', d[o:o + 4])[0]
    ft = u(ar.public('mexData') + 8)
    name = d[u(u(ft) + 4 * eid):d.index(b'\0', u(u(ft) + 4 * eid))].decode('latin1')
    argv = sys.argv
    sys.argv = ['mxdt_clone.py', '--out', path, '--pl', 'PlBm.dat', '--name', name, '--aj', 'PlBmAJ.dat',
                '--src-k', str(kid), '--src-e', str(eid), '--dst-k', str(kid), '--dst-e', str(eid)]
    for c, cc in enumerate(COLORS):
        sys.argv += ['--costume', '%d:PlBm%s.dat:%s:%s' % (c, cc, JOINT_SYM, MAT_SYM)]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            runpy.run_path(os.path.join(EXP, 'brawl-kirby', 'tools', 'mxdt_clone.py'), run_name='__main__')
    finally:
        sys.argv = argv; mex_hsd.Gcm = real
    log = json.loads(buf.getvalue())
    report['MxDt.dat'] = {'internal': kid, 'external': eid, 'name': name, 'anim_file': 'PlBmAJ.dat', 'costumes': log.get('costumes')}


def patch_mxdt_demo(path, kid, eid, report):
    """MxDt fighter +0x28 result_file[external] -> MK's results file, +0x18 demo strings[internal] -> a copy whose result
    symbol is MK's (intro / ending / vi-wait keep Kirby's: those files are Kirby's)."""
    dr = os.path.join(ANIM, 'out', 'demo_rows.json')
    if not os.path.exists(dr): return
    D = json.load(open(dr))
    w = Writer(open(path, 'rb').read())
    ft = w.u32(w.ar.public('mexData') + 8)
    rf = w.u32(ft + 0x28) + 4 * eid
    old_file = w.str_at(w.u32(rf)) if rf in w.relocs else None
    w.ptr(rf, w.cstr(D['file']))
    ds_tbl = w.u32(ft + 0x18) + 4 * kid; ds = w.u32(ds_tbl)
    new = w.alloc(bytes(16))
    w.ptr(new, w.cstr(D['symbol']))
    for i in range(1, 4):
        if (ds + 4 * i) in w.relocs: w.ptr(new + 4 * i, w.u32(ds + 4 * i))
    old_sym = w.str_at(w.u32(ds)) if ds in w.relocs else None
    w.ptr(ds_tbl, new)
    w.save(path)
    report['MxDt.dat']['result_file'] = {'external': eid, 'was': old_file, 'now': D['file']}
    report['MxDt.dat']['demo_result_symbol'] = {'internal': kid, 'was': old_sym, 'now': D['symbol']}


def main():
    global SCRIPTS_MODE, VIS
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    for a in sys.argv[1:]:
        if a.startswith('--scripts='): SCRIPTS_MODE = a.split('=', 1)[1]
        if a == '--no-vis': VIS = False
    mod = args[0]; f = os.path.join(mod, 'files')
    report = {}
    for cc in COLORS: shutil.copyfile(os.path.join(MODEL, 'out', 'PlBm%s.dat' % cc), os.path.join(f, 'PlBm%s.dat' % cc))
    shutil.copyfile(os.path.join(ANIM, 'out', 'PlBmAJ.dat'), os.path.join(f, 'PlBmAJ.dat'))
    report['copied'] = ['PlBm%s.dat' % cc for cc in COLORS] + ['PlBmAJ.dat']
    if os.path.exists(os.path.join(ANIM, 'out', 'GmRstMBm.dat')):
        shutil.copyfile(os.path.join(ANIM, 'out', 'GmRstMBm.dat'), os.path.join(f, 'GmRstMBm.dat')); report['copied'].append('GmRstMBm.dat')
    kid = find_row(os.path.join(f, 'MxDt.dat'), 'PlBm.dat')
    slot_log = os.path.join(MK, 'build', 'slot_files_log.json')
    eid = json.load(open(slot_log))['row']['external'] if os.path.exists(slot_log) else kid - 1
    patch_ftdata(os.path.join(f, 'PlBm.dat'), report)
    patch_plco(os.path.join(f, 'PlCo.dat'), kid, report)
    patch_mxdt(os.path.join(f, 'MxDt.dat'), kid, eid, report)
    patch_mxdt_demo(os.path.join(f, 'MxDt.dat'), kid, eid, report)
    json.dump(report, open(os.path.join(mod, 'MK_INSTALL.json'), 'w'), indent=1)
    print(json.dumps({k: (v if k != 'PlBm.dat' else {kk: vv for kk, vv in v.items() if kk in ('ftData', 'motion_table', 'x20', 'x5C', 'x1C')})
                      for k, v in report.items() if k != 'PlCo.dat'}, indent=1))
    print('PlCo parts_num', report['PlCo.dat']['parts_num'], report['PlCo.dat']['insert_slots_table5'])


if __name__ == '__main__':
    main()
