"""decode_mk.py - vanilla Brawl Meta Knight moveset decode (generalised from brawl-kirby/tools/brawl_dump/decode_mk.py).
Inputs: ../dump/fitmk.json (+ .bin), motionetc.json, cos00.json, mk_bones.json (mdump.exe runs). Output: ../analysis/brawl_metaknight.json."""
import json, struct, collections, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, '..', 'analysis'))
os.makedirs(OUT, exist_ok=True)
O = os.path.normpath(os.path.join(HERE, '..', 'dump'))

r = json.load(open(os.path.join(O, 'fitmk.json'), encoding='utf-8'))
evdict = json.load(open(os.path.join(O, 'evdict.json'), encoding='utf-8'))
bones = json.load(open(os.path.join(O, 'mk_bones.json')))
BONE = {b['index']: b['name'] for b in bones}
attrnames = {int(k): v[:2] for k, v in json.load(open(os.path.join(HERE, '..', '..', '..', 'experiment', 'brawl-kirby', 'tools', 'brawl_dump', 'out', 'attrnames.json'))).items()}
attrdesc = {int(k): v[2] for k, v in json.load(open(os.path.join(HERE, '..', '..', '..', 'experiment', 'brawl-kirby', 'tools', 'brawl_dump', 'out', 'attrnames.json'))).items()}
movedef_bin = open(os.path.join(O, 'fitmk.json.MoveDef_FitMetaknight.bin'), 'rb').read()
BASE = 0x20  # data offsets are relative to header + 0x20

movedef = r['c'][0]
assert movedef['t'] == 'MoveDefNode'
subr_list = movedef['c'][0]
sections = [c for c in movedef['c'] if c['t'] == 'MoveDefSectionNode'][0]
refs = [c for c in movedef['c'] if c['t'] == 'MoveDefReferenceNode']
data = sections['c'][0]
D = {c['n']: c for c in data['c']}

# ---------- subroutine offset map
sub_by_off = {}
for s in subr_list.get('c', []):
    sub_by_off[s['p'].get('IntOffset')] = s['n']
ext_names = [c['n'] for c in refs[0]['c']] if refs else []

NOISE = {'Description', 'IntOffset', 'HexOffset', 'Size', 'BaseAddress', 'Model', 'External', 'RealValue', 'References'}


def bone_name(i):
    # Kirby PSA bone ids are 400 + MDL0 bone index (no Wario-style translation table for FitKirby;
    # verified: jab RArmJ, fsmash LFootJ, dair TopN)
    if isinstance(i, int) and i >= 400:
        i -= 400
    return BONE.get(i, None)


def arg(p):
    t = p['t']
    q = p.get('p', {})
    if t == 'MoveDefEventValueNode':
        return q.get('Value')
    if t == 'MoveDefEventScalarNode':
        return q.get('Value')
    if t == 'MoveDefEventBoolNode':
        return q.get('Value')
    if t == 'MoveDefEventValue2HalfNode':
        return [q.get('Value1'), q.get('Value2')]
    if t == 'MoveDefEventValue2HalfGFXNode':
        return {'gfx_file': q.get('GFXFile'), 'efls_index': q.get('EFLSEntryIndex')}
    if t == 'MoveDefEventRequirementNode':
        return {'req': q.get('Requirement'), 'not': q.get('Not')}
    if t == 'MoveDefEventVariableNode':
        return '%s.%s[%s]' % (q.get('MemType'), q.get('VarType'), q.get('Number'))
    if t == 'MoveDefEventOffsetNode':
        off = q.get('RawOffset')
        if q.get('ExternalNode'):
            return {'external': str(q.get('ExternalNode')).replace('node:', '')}
        if off in sub_by_off:
            return {'sub': sub_by_off[off], 'off': hex(off)}
        return {'off': hex(off) if isinstance(off, int) else off}
    if t == 'MoveDefEventValueEnumNode':
        return q.get('Value')
    if t in ('HitboxFlagsNode', 'SpecialHitboxFlagsNode'):
        return {k: v for k, v in q.items() if k not in NOISE and not k.startswith('_')}
    return {k: v for k, v in q.items() if k not in NOISE and not k.startswith('_')}


HITBOX_IDS = {0x06000D00: 'hitbox', 0x06150F00: 'special_hitbox', 0x062B0D00: 'thrown_hitbox'}  # inert collision has a different arg layout; left as generic args


def hitbox(ev, args):
    bi, hid = args[0]
    h = dict(id=hid, bone=bi, bone_name=bone_name(bi), damage=args[1], angle=args[2],
             wdsk=args[3][0], kbg=args[3][1], shield_damage=args[4][0], bkb=args[4][1],
             size=args[5], offset=[args[6], args[7], args[8]], trip_rate=args[9],
             hitlag_mult=args[10], sdi_mult=args[11])
    f = args[12] if isinstance(args[12], dict) else {}
    h.update(element=f.get('Effect'), sfx=f.get('Sound'), sfx_level=None, ground=f.get('Grounded'), air=f.get('Aerial'),
             hit_type=f.get('Type'), clang=f.get('Clang'), direct=f.get('Direct'), flags_hex=f.get('HexValue'))
    if len(args) >= 15:
        h['rehit_rate'] = args[13]
        sf = args[14] if isinstance(args[14], dict) else {}
        h['special_flags'] = {k: v for k, v in sf.items() if not k.startswith('Unk') and not k.startswith('CanHitUnk')}
    return h


def decode_script(act):
    """act: a MoveDefActionNode dict -> list of events"""
    out = []
    frame = 0.0
    exact = True
    for e in act.get('c', []):
        if e['t'] != 'MoveDefEventNode':
            continue
        p = e['p']
        eid = p['EventID'] & 0xFFFFFFFF
        args = [arg(a) for a in e.get('c', [])]
        ev = dict(off=p.get('HexOffset'), id='%08X' % eid, name=e['n'])
        if args:
            ev['args'] = args
        if exact:
            ev['frame'] = round(frame, 3)
        if eid in HITBOX_IDS and len(args) >= 13:
            try:
                ev['hitbox'] = hitbox(ev, args)
            except Exception as ex:
                ev['hitbox_err'] = str(ex)
        out.append(ev)
        # timers
        if eid == 0x00010100 and args:
            frame += float(args[0])
        elif eid == 0x00020100 and args:
            frame = max(frame, float(args[0]))
        elif eid in (0x00090100, 0x00040100, 0x00070100, 0x000D0200):
            # goto / loop / subroutine / concurrent loop: stop claiming exact frames after flow jumps
            if eid in (0x00090100, 0x00040100):
                exact = False
    return out


# ---------- attributes
def attributes(node, count):
    raw = bytes.fromhex(node['raw'])
    res = []
    for i in range(count):
        if 4 * i + 4 > len(raw):
            break
        name, typ = attrnames.get(i, ('0x%03X' % (4 * i), 0))
        word = raw[4 * i:4 * i + 4]
        val = struct.unpack('>i', word)[0] if typ == 1 else struct.unpack('>f', word)[0]
        if isinstance(val, float):
            val = float('%.6g' % val)
        res.append(dict(index=i, offset='0x%03X' % (4 * i), name=name.split(' ', 1)[1] if ' ' in name else name, type='int' if typ == 1 else 'float', value=val))
    return res


attrs = attributes(D['Attributes'], 185)
sse_attrs = attributes(D['SSE Attributes'], 185)

# ---------- subactions
subs = []
sub_scripts = []
for i, g in enumerate(D['SubAction Scripts']['c']):
    q = g.get('p', {})
    chans = {}
    for ch in g.get('c', []):
        evs = decode_script(ch)
        chans[ch['n'].lower()] = evs
    subs.append(dict(index=i, hex='0x%X' % i, name=g['n'], animation=g['n'], flags=q.get('Flags'), in_translation_time=q.get('InTranslationTime'),
                     events={k: len(v) for k, v in chans.items()},
                     hitboxes=sum(1 for v in chans.values() for e in v if 'hitbox' in e)))
    sub_scripts.append(dict(index=i, name=g['n'], channels=chans))

# ---------- actions
pre_names = [c['n'] for c in D['Action Pre']['c']]
common_flags = D['Common Action Flags']['c']
special_flags = D['Action Flags']['c']
action_scripts = D['Action Scripts']['c']
actions = []
for i, n in enumerate(pre_names):
    a = dict(index=i, hex='0x%X' % i, pre_name=None if n.startswith('Action') else n.replace('statusAnimCmdPre_', ''),
             kind='common' if i < 0x112 else 'special')
    fl = common_flags[i] if i < len(common_flags) else (special_flags[i - 0x112] if i - 0x112 < len(special_flags) else None)
    if fl:
        a['flags'] = [fl['p'].get('Flags%di' % k) for k in (1, 2, 3, 4)]
    actions.append(a)
action_entry_exit = []
for g in action_scripts:
    idx = int(g['n'].replace('Action', ''))
    ch = {c['n'].lower(): decode_script(c) for c in g.get('c', [])}
    action_entry_exit.append(dict(index=idx, hex='0x%X' % idx, scripts=ch))
    actions[idx]['entry_events'] = len(ch.get('entry', []))
    actions[idx]['exit_events'] = len(ch.get('exit', []))

overrides = []
for key in D:
    if key.startswith('statusAnimCmd') and 'Disguise' in key:
        for o in D[key].get('c', []):
            scr = [decode_script(c) for c in o.get('c', []) if c['t'] == 'MoveDefActionNode']
            overrides.append(dict(list=key, name=o['n'], scripts=scr))

# ---------- subroutines
subroutines = [dict(name=s['n'], off=s['p'].get('HexOffset'), events=decode_script(s)) for s in subr_list.get('c', [])]

# ---------- misc: hurtboxes, ledge grab, bone refs
misc = D['Misc Section']['p']


def rd(off, n):
    return movedef_bin[BASE + off: BASE + off + n]


hurt = []
for k in range(misc['HurtBoxCount']):
    b = rd(misc['HurtBoxOffset'] + 32 * k, 32)
    ox, oy, oz, sx, sy, sz, rad = struct.unpack('>7f', b[:28])
    d0, d1 = b[28], b[29]
    bi = (((d1 >> 7) & 1) | ((d0 << 1) & 0xFF)) & 0x1FF
    hurt.append(dict(bone=bi, bone_name=bone_name(bi), offset=[round(ox, 4), round(oy, 4), round(oz, 4)], stretch=[round(sx, 4), round(sy, 4), round(sz, 4)],
                     radius=round(rad, 4), enabled=bool(d1 & 1), zone=['low', 'mid', 'high', '?'][(d1 >> 3) & 3], region=(d1 >> 5) & 3))
ledge = []
for k in range(misc['LedgegrabCount']):
    x, y, w, h = struct.unpack('>4f', rd(misc['LedgegrabOffset'] + 16 * k, 16))
    ledge.append(dict(x=round(x, 4), y=round(y, 4), width=round(w, 4), height=round(h, 4)))
boneref_idx = [int(c['n']) for c in D[[k for k in D if k.endswith('Bone References')][0]]['c']]
bone_refs = [dict(slot=i, bone=b, bone_name=bone_name(b)) for i, b in enumerate(boneref_idx)]
hand_bones = [int(c['n']) for c in D['Hand Bones']['c']]
bone_floats = []
for key in ('Bone Floats 1', 'Bone Floats 2'):
    for c in D[key].get('c', []):
        q = c['p']
        bone_floats.append(dict(table=key, bone=int(q['Bone']), bone_name=bone_name(int(q['Bone'])), floats=[q.get('Float%d' % k) for k in range(1, 7)]))

# ---------- articles
articles = []
for key in ('Static Articles', 'Articles'):
    for a in D[key].get('c', []):
        q = a['p']
        art = dict(group=key, name=a['n'], id=q.get('ID'), article_group_id=q.get('ArticleGroupID'), arc_entry_group=q.get('ARCEntryGroup'),
                   bone=q.get('Bone'), string_id=q.get('ArticleStringID'), actions=[], subactions=[], hurtboxes=[], extra_params=[])
        for c in a.get('c', []):
            if c['n'] == 'Actions':
                art['actions'] = [dict(name=x['n'], events=decode_script(x)) for x in c.get('c', [])]
            elif c['n'] == 'SubActions':
                for x in c.get('c', []):
                    xq = x.get('p', {})
                    art['subactions'].append(dict(index=xq.get('ID'), name=x['n'], flags=xq.get('Flags'), in_translation_time=xq.get('InTranslationTime'),
                                                  channels={y['n'].lower(): decode_script(y) for y in x.get('c', []) if y['t'] == 'MoveDefActionNode'}))
            elif c['n'] == 'HitData':
                for x in c.get('c', []):
                    xq = x['p']
                    art['hurtboxes'].append(dict(bone=xq.get('Bone'), offset=xq.get('PosOffset'), stretch=xq.get('Stretch'), radius=xq.get('Radius'), zone=xq.get('Zone'), region=xq.get('Region')))
            elif c['t'] == 'MoveDefSectionParamNode':
                art['extra_params'].append(dict(name=c['n'], raw=c.get('raw')))
        articles.append(art)

# ---------- section params (ftSonic param blocks)
def floats(raw):
    b = bytes.fromhex(raw)
    out = []
    for k in range(len(b) // 4):
        w = b[4 * k:4 * k + 4]
        i = struct.unpack('>i', w)[0]
        f = struct.unpack('>f', w)[0]
        out.append(i if -100000 < i < 100000 else float('%.6g' % f))
    return out


params = [dict(name=c['n'], size=c['p'].get('Size'), words=floats(c['raw']), raw=c['raw']) for c in data['c'] if c['t'] == 'MoveDefSectionParamNode' and c.get('raw')]

exec(open(os.path.join(HERE, 'decode_mk_tail.py'), encoding='utf-8').read())


