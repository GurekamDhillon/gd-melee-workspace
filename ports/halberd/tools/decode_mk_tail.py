# Executed at the end of decode_mk.py (shares its globals). Writes analysis/brawl_kirby.json + brawl_model.json.
import json, os, struct, collections

# ---------- motion data (FitKirbyMotionEtc.pac): CHR0 frame counts, PAT0, ATKD (AI attack ranges)
me = json.load(open(os.path.join(O, 'motionetc.json'), encoding='utf-8'))
chr0 = collections.OrderedDict()
pat0 = []
atkd = []


def walk_me(n, path):
    t = n['t']
    if t == 'CHR0Node':
        chr0.setdefault(n['n'], dict(frames=n['p'].get('FrameCount'), loop=n['p'].get('Loop'), brres=path))
    elif t == 'PAT0Node':
        pat0.append(dict(name=n['n'], frames=n['p'].get('FrameCount'), brres=path))
    elif t == 'ATKDEntryNode':
        q = n['p']
        atkd.append(dict(subaction=q.get('SubActionName'), start=int(q.get('StartFrame'), 16), end=int(q.get('EndFrame'), 16),
                         x=[q.get('XMinRange'), q.get('XMaxRange')], y=[q.get('YMinRange'), q.get('YMaxRange')], unk=q.get('Unknown1')))
    for c in n.get('c', []):
        walk_me(c, path + '/' + n['n'] if t in ('ARCNode', 'BRRESNode') else path)


walk_me(me, '')

# ---------- subaction classification
names = [s['name'] for s in subs]
i_bitten = names.index('SpecialNBittenStart')
i_appeal = names.index('AppealHi')
i_spy = names.index('Spycloak')
i_final_end = len(names) - 1


def klass(i):
    if i < i_bitten:
        return 'common'
    if i < i_appeal:
        return 'common_victim'  # bitten / captured / thrown-by-specific-fighter poses
    if i <= i_spy:
        return 'common'
    if i <= i_final_end:
        return 'fighter_special'
    return 'copy_ability'


def summarize_hitboxes(ch):
    hb = []
    for e in ch.get('main', []):
        if 'hitbox' in e:
            h = dict(e['hitbox'])
            h['frame'] = e.get('frame')
            h['kind'] = HITBOX_IDS.get(int(e['id'], 16))
            hb.append(h)
    return hb


def iasa(ch):
    for e in ch.get('main', []):
        if e['name'] and e['name'].lower().startswith('allow interrupt'):
            return e.get('frame')
    return None


def timeline(ch):
    """compact list of (frame, event name) for the main channel"""
    return [[e.get('frame'), e['name']] for e in ch.get('main', [])]


SUBS = {s['name']: s['events'] for s in subroutines}


def named(e):
    info = evdict.get(e['id'])
    a = e.get('args', [])
    if not info or not a:
        return a
    ps = info['params']
    return {(ps[i] if i < len(ps) else 'arg%d' % i) + ('' if (ps[i] if i < len(ps) else '') not in ps[:i] else '#%d' % i): v for i, v in enumerate(a)}


def simulate(evs, max_frame=600):
    """Unroll one PSA channel: timers, Set Loop/Execute Loop (finite counts; -1 = infinite, run once),
    local Subroutine/Goto (inlined), If/Else (true branch taken; flagged). Returns timed event list + hitbox windows."""
    out, windows, open_hb, notes = [], [], {}, set()
    state = dict(f=0.0, iasa=None, steps=0)

    def close(hid, f):
        h = open_hb.pop(hid, None)
        if h:
            h['end'] = f
            windows.append(h)

    def run(evs, depth):
        loops = []
        pos = 0
        skip_else = 0
        cond = 0
        while pos < len(evs):
            state['steps'] += 1
            if state['steps'] > 20000 or state['f'] > max_frame:
                notes.add('truncated')
                return 'stop'
            e = evs[pos]
            eid = int(e['id'], 16)
            a = e.get('args', [])
            f = state['f']
            if eid == 0x00010100 and a:
                state['f'] += float(a[0])
            elif eid == 0x00020100 and a:
                state['f'] = max(f, float(a[0]))
            elif eid == 0x00040100:
                n = a[0] if a else 1
                if n is None or n < 0:
                    notes.add('infinite_loop_run_once')
                    n = 1
                loops.append([pos + 1, int(n)])
            elif eid == 0x00050000:
                if loops:
                    loops[-1][1] -= 1
                    if loops[-1][1] > 0:
                        pos = loops[-1][0]
                        continue
                    loops.pop()
            elif eid in (0x00070100, 0x00090100):
                tgt = a[0] if a else None
                if isinstance(tgt, dict) and tgt.get('sub') in SUBS and depth < 8:
                    out.append(dict(frame=f, id=e['id'], name=e['name'], args=a))
                    r = run(SUBS[tgt['sub']], depth + 1)
                    if r == 'stop' or eid == 0x00090100:
                        return 'stop'
                    pos += 1
                    continue
                notes.add('external_or_unresolved_call')
                if eid == 0x00090100:
                    out.append(dict(frame=f, id=e['id'], name=e['name'], args=a))
                    return 'stop'
            elif eid == 0x00080000:
                return 'ret'
            elif (eid >> 16) == 0x000A:
                cond += 1
                notes.add('conditional_true_branch_taken')
            elif eid == 0x000E0000 or (eid >> 16) == 0x000D:
                # skip else/else-if bodies up to End If of the same depth
                depth_if = 0
                pos += 1
                while pos < len(evs):
                    i2 = int(evs[pos]['id'], 16)
                    if (i2 >> 16) == 0x000A:
                        depth_if += 1
                    elif i2 == 0x000F0000:
                        if depth_if == 0:
                            break
                        depth_if -= 1
                    pos += 1
                cond -= 1
                pos += 1
                continue
            elif eid == 0x000F0000:
                cond -= 1
            if eid in HITBOX_IDS and 'hitbox' in e:
                h = dict(e['hitbox'])
                close(h['id'], f)
                h.update(start=f, kind=HITBOX_IDS[eid], conditional=cond > 0)
                open_hb[h['id']] = h
            elif eid == 0x06040000:
                for k in list(open_hb):
                    close(k, f)
            elif eid == 0x06030100 and a:
                close(a[0], f)
            elif eid == 0x64000000 and state['iasa'] is None:
                state['iasa'] = f
            if eid not in (0x00010100, 0x00020100, 0x00040100, 0x00050000, 0x000F0000, 0x000E0000):
                ev = dict(frame=f, id=e['id'], name=e['name'])
                if a:
                    ev['args'] = named(e)
                out.append(ev)
            pos += 1
        return 'end'

    run(evs, 0)
    for k in list(open_hb):
        h = open_hb.pop(k)
        h['end'] = None  # still active at script end (ends with the action / anim)
        windows.append(h)
    windows.sort(key=lambda h: (h['start'], h['id']))
    return dict(events=out, hitbox_windows=windows, iasa=state['iasa'], end_frame=state['f'], notes=sorted(notes))


sub_full = []
for s, sc in zip(subs, sub_scripts):
    ch = sc['channels']
    anim = chr0.get(s['name'])
    sim = {k: simulate(v) for k, v in ch.items()}
    m = sim.get('main', {})
    throws = [dict(frame=e['frame'], name=e['name'], args=e.get('args')) for e in m.get('events', []) if e['id'] in ('060E1100', '060F0500')]
    grabs = [dict(frame=e['frame'], name=e['name'], args=e.get('args')) for e in m.get('events', []) if e['id'].startswith('060A')]
    sub_full.append(dict(
        index=s['index'], hex=s['hex'], name=s['name'], klass=klass(s['index']),
        anim=s['name'] if anim else None, anim_frames=anim['frames'] if anim else None,
        anim_note=None if anim else ('n/a' if klass(s['index']) == 'copy_ability' else 'no CHR0 of this name in FitMetaknightMotionEtc.pac'),
        flags=s['flags'], in_translation_time=s['in_translation_time'],
        iasa_frame=m.get('iasa'), script_end_frame=m.get('end_frame'), sim_notes=m.get('notes'),
        hitboxes=m.get('hitbox_windows', []),
        throws=throws, grabs=grabs,
        gfx=[[e['frame'], e['name'], e.get('args')] for e in sim.get('gfx', {}).get('events', [])],
        sfx=[[e['frame'], e['name'], e.get('args')] for e in sim.get('sfx', {}).get('events', [])],
        other=[[e['frame'], e['name'], e.get('args')] for e in sim.get('other', {}).get('events', [])],
        main_timeline=[[e['frame'], e['name'], e.get('args')] for e in m.get('events', []) if e['id'] not in ('06000D00', '06150F00', '062B0D00')],
        channels_raw=ch))

# ---------- misc section extras (multijump / glide / crawl / tether raw)
def raw_block(off, n):
    if not off:
        return None
    b = rd(off, n)
    out = []
    for k in range(len(b) // 4):
        w = b[4 * k:4 * k + 4]
        i = struct.unpack('>i', w)[0]
        out.append(i if -100000 < i < 100000 else float('%.6g' % struct.unpack('>f', w)[0]))
    return dict(offset=hex(off), words=out)


misc_clean = {k: v for k, v in misc.items() if k not in NOISE and not k.startswith('_')}
misc_blocks = dict(
    multijump=raw_block(misc.get('MultiJumpOffset'), 0x24),
    glide=raw_block(misc.get('GlideOffset'), 0x58),
    crawl=raw_block(misc.get('CrawlOffset'), 0x08),
    tether=raw_block(misc.get('TetherOffset'), 0x08),
)

# ---------- all param-ish nodes in the data section (raw words)
param_blocks = []
for c in data['c']:
    if c['t'] == 'MoveDefSectionParamNode' and c.get('raw'):
        param_blocks.append(dict(name=c['n'], node=c['t'], size=c['p'].get('Size'), words=floats(c['raw']), raw=c['raw']))
    elif c['t'] in ('MoveDefRawDataNode', 'MoveDefKirbyParamList5152Node', 'MoveDefKirbyParamList49Node'):
        parts = []
        for x in c.get('c', []):
            if x.get('raw'):
                parts.append(dict(name=x['n'], words=floats(x['raw']), raw=x['raw']))
            else:
                parts.append(dict(name=x['n'], node=x['t'], props={k: v for k, v in x.get('p', {}).items() if k not in NOISE and not k.startswith('_')}))
        param_blocks.append(dict(name=c['n'], node=c['t'], size=c['p'].get('Size'), parts=parts))

attrs_named = []
for a in attrs:
    a = dict(a)
    a['description'] = attrdesc.get(a['index'])
    attrs_named.append(a)
sse_diff = [dict(index=a['index'], name=a['name'], vs=a['value'], sse=b['value']) for a, b in zip(attrs, sse_attrs) if a['value'] != b['value']]

cls_counts = collections.Counter(s['klass'] for s in sub_full)
own_attack = [s['name'] for s in sub_full if s['klass'] in ('common', 'fighter_special') and s['hitboxes']]

out = dict(
    note=("Vanilla Brawl Meta Knight (fighter/metaknight/FitMetaknight.pac, MoveDef_FitMetaknight) decoded with BrawlLib's MoveDef parser "
          "(experiment/BrawlCrate BrawlLib net472, x86, ParseMoveDef=true) via tools/brawl_dump/mdump.exe + decode_mk.py. "
          "Per event: off = data offset, id = event id hex (NNIICC00), name (BrawlLib event dictionary), args decoded per parameter type, "
          "frame = PSA frame counter (sync timer adds, async timer sets; omitted after the first Goto/Set Loop), "
          "hitbox = semantic view of Offensive / Special Offensive Collision (bone index -> MDL0 bone of FitMetaknight00). "
          "Brawl units: hitbox size/offset are in model units (Brawl MK model scale ~ Melee units need checking), angles degrees, "
          "kbg/wdsk/bkb same meaning as Melee. anim_frames from CHR0 FrameCount in FitKirbyMotionEtc.pac. "
          "Per subaction: hitboxes = unrolled hitbox windows [start,end) in PSA frames (0-based: start 2 = first active on game frame 3; end None = still out when the script ends); "
          "iasa_frame = first Allow Interrupt (None = no IASA event, interruptible at anim end); bone ids in hitboxes/gfx are PSA ids = 400 + MDL0 bone index; "
          "loops unrolled (infinite loops run once), local subroutines inlined, If takes the true branch (sim_notes flags it); channels_raw keeps the undecoded-order events with data offsets."),
    source=dict(pac='C:/iso/brawl-extract/files/fighter/metaknight/FitMetaknight.pac', motion='FitMetaknightMotionEtc.pac', costume='FitMetaknight00.pac'),
    attributes=attrs_named,
    sse_attributes_diff=sse_diff,
    misc_section=misc_clean,
    misc_blocks=misc_blocks,
    hurtboxes=hurt, ledge_grab=ledge, bone_references=bone_refs,
    hand_bones=[dict(bone=b, bone_name=bone_name(b)) for b in hand_bones],
    bone_floats=bone_floats,
    actions=dict(count=len(actions), common=0x112, special=len(actions) - 0x112, list=actions, entry_exit=action_entry_exit),
    action_overrides=overrides,
    subactions=dict(count=len(sub_full), class_counts=dict(cls_counts),
                    class_ranges=dict(common='0..0x%X (+ appeal/entry/win 0x%X..0x%X)' % (i_bitten - 1, i_appeal, i_spy),
                                      common_victim='0x%X..0x%X' % (i_bitten, i_appeal - 1),
                                      fighter_special='0x%X..0x%X' % (i_spy + 1, i_final_end),
                                      copy_ability='0x%X..0x%X' % (i_final_end + 1, len(sub_full) - 1)),
                    own_attacking_subactions=own_attack,
                    list=sub_full),
    subroutines=subroutines,
    external_references=ext_names,
    articles=articles,
    param_blocks=param_blocks,
    ai_attack_data=atkd,
    event_dictionary=evdict,
    event_stats=dict(total_events=sum(len(v) for s in sub_scripts for v in s['channels'].values()),
                     hitboxes=sum(len(s['hitboxes']) for s in sub_full), hitboxes_own=sum(len(s['hitboxes']) for s in sub_full if s['klass'] != 'copy_ability'),
                     unknown_events=dict(collections.Counter(e['id'] for s in sub_scripts for v in s['channels'].values() for e in v
                                                            if e['id'] not in evdict).most_common(40))),
)
json.dump(out, open(os.path.join(OUT, 'brawl_metaknight.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------- model/anim scope
cos = json.load(open(os.path.join(O, 'cos00.json'), encoding='utf-8'))
cnt = collections.Counter()
mdls = []


def walk_c(n):
    cnt[n['t']] += 1
    if n['t'] == 'MDL0Node':
        mdls.append(n['n'])
    for c in n.get('c', []):
        walk_c(c)


walk_c(cos)
model = dict(
    note='FitMetaknight00.pac (costume 0) MDL0 skeleton; FitMetaknightMotionEtc.pac animation set.',
    costume=dict(file='FitMetaknight00.pac', models=mdls, bone_count=len(bones), bones=bones,
                 node_counts={k: v for k, v in cnt.items() if k.startswith('MDL0') or k in ('TEX0Node', 'PLT0Node')}),
    motion=dict(file='FitMetaknightMotionEtc.pac', chr0_count=len(chr0), pat0_count=len(pat0),
                fighter_motion_chr0=[k for k, v in chr0.items() if '/FitMetaknightMotion/' in v['brres'] + '/'],
                other_chr0={k: v['brres'] for k, v in chr0.items() if '/FitMetaknightMotion/' not in v['brres'] + '/'},
                frames={k: v['frames'] for k, v in chr0.items()},
                pat0=pat0),
)
json.dump(model, open(os.path.join(OUT, 'brawl_metaknight_model.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print('subactions', len(sub_full), dict(cls_counts), 'actions', len(actions), 'subroutines', len(subroutines), 'articles', len(articles))
print('events', out['event_stats']['total_events'], 'hitboxes', out['event_stats']['hitboxes'], 'unknown', out['event_stats']['unknown_events'])
print('chr0', len(chr0), 'pat0', len(pat0), 'atkd', len(atkd), 'bones', len(bones))
print([(a['name'], a['value']) for a in attrs[:12]])
