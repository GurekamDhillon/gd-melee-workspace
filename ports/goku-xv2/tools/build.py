"""Rebuild artist output, then reapply maintained Goku gameplay through the parity contract.

python ports/goku-xv2/tools/build.py --package _build/.../mods/goku-xv2 --art-build _build/.../build
Or supply --fighter PATH --out _build/PATH to run the artist builder first.
All generated scripts, losses and audit records remain below workspace _build.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

PORT = Path(__file__).resolve().parents[1]
ROOT = PORT.parents[1]
HAND_FILE = Path(os.environ.get('GOKU_HAND', PORT/'anim/hand.json'))   # hand-authored animation deltas (tools/geno/artist/blender/hand_layer.py); a Stage A input
AUTHOR = ROOT/'_build/goku-xv2'/os.environ.get('GOKU_AUTHOR','author-source')   # GOKU_AUTHOR=splice-preview: the reduced splice-preview build (xv2_to_artist.py --splice-only)
# a reduced splice-preview build keeps its reports inside its own directory; the shipped build's stay in _build/goku-xv2 (FIDELITY.md reads those)
REPORTS = ROOT/'_build/goku-xv2' if os.environ.get('GOKU_AUTHOR','author-source')=='author-source' else AUTHOR/'reports'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import strip_gameplay as SG  # gameplay.full.json (local) wins over the stripped gameplay.json
sys.path.insert(0, str(ROOT/'ports/ir/tools'))
from tools.geno import script, report, throw_standin
from acmd_loss import write_losses

ROLE = {'HAND_R':'hand.R','HAND_L':'hand.L','FOOT_R':'foot.R','FOOT_L':'foot.L','CHEST':'chest',
        'ARM_R':'lower_arm.R','ARM_L':'lower_arm.L','LEG_R':'lower_leg.R','LEG_L':'lower_leg.L','HIPS':'hips','FLOOR':'translation',
        # cross-port hitboxes (tools/cross_port.py) sit on the bone of the source's own role
        'UPLEG_R':'upper_leg.R','UPLEG_L':'upper_leg.L','UPARM_R':'upper_arm.R','UPARM_L':'upper_arm.L','HEAD':'head','NECK':'neck',
        'SPINE':'spine','TOE_R':'toe.R','TOE_L':'toe.L'}

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')

def generated(path):
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT/'_build').resolve()):
        raise ValueError('Generated output must remain under workspace _build: '+str(path))
    return path

def move_source(ir, name):
    key = name if name.startswith('move:') else 'move:'+name
    parity = next((p for p in ir['parity'] if p['here'] == key), None)
    if parity is None:
        raise ValueError('Missing parity decision for '+key)
    move = next(m for m in ir['behavior']['moves'] if m['id'] == key)
    subs = {s['id']:s for s in ir['behavior']['subactions']}
    scripts = {s['id']:s for s in ir['behavior']['scripts']}
    return parity, move, [scripts[subs[s]['scripts']['main']] for s in move['subactions']]

def attributes(ir, host):
    fields = load(ROOT/'tools/geno/artist/data/default_attributes.json')['attributes']
    values = {a['engine_name']:a for a in host['behavior']['attributes']['common']}
    result, evidence = {}, []
    for field in fields:
        row = values[field]
        parity = next((p for p in ir['parity'] if p['here'].startswith('issue:attribute/') and
                       ('(host field '+field+')') in p['differences']), None)
        if parity is None:
            raise ValueError('Missing attribute parity decision for '+field)
        value = 1.0 if field == 'model_scaling' else row['value']
        result[field] = value
        evidence.append({'field':field, 'value':value, 'classification':'destination design',
                         'basis':'Captain Falcon comparison host; model scale fixed to authored dimensions' if field == 'model_scaling' else 'Captain Falcon comparison host copied as initial design',
                         'parity':parity, 'host_attribute':row['key'], 'source_value':None})
    return result, evidence

def apply_attribute_overrides(attrs, evidence, cfg):
    """Apply explicit maintained-source values after host design and artist measurements.

    The Geno schema owns names, numeric types and any bounds. No inherited or
    disc values are serialized into gameplay.json by this helper.
    """
    overrides = cfg.get('attributes', {})
    contract = load(ROOT/'tools/geno/geno.schema.json')['properties']['fighters']['items']['properties']['attributes']
    if not isinstance(overrides, dict):
        raise ValueError('attributes must be an object')
    if len(overrides) > contract['maxProperties']:
        raise ValueError('attributes exceed the Geno schema limit')
    rules = contract['properties']
    result, records = copy.deepcopy(attrs), copy.deepcopy(evidence)
    for name, value in overrides.items():
        if name not in rules:
            raise ValueError('unknown fighter attribute: '+str(name))
        rule = rules[name]
        try:
            finite = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError(name+' must be a finite number')
        if rule['type'] == 'integer' and int(value) != value:
            raise ValueError(name+' must be an integer')
        if (('minimum' in rule and value < rule['minimum']) or
                ('maximum' in rule and value > rule['maximum'])):
            raise ValueError(name+' is outside its schema range')
        result[name] = int(value) if rule['type'] == 'integer' else value
        record = next((row for row in records if row['field'] == name), None)
        if record is None:
            record = {'field': name}
            records.append(record)
        record.update(value=result[name], classification='authored override',
                      basis='Maintained gameplay source attribute override')
    return result, records

def plan_clip_names(package):
    """Bank clip names (plan.json bank.clips) of the built package."""
    try:
        plan = load(package / 'files' / 'plan.json')
        clips = plan['bank']['clips']
        return set(clips) if isinstance(clips, dict) else {c.get('name') for c in clips}
    except Exception:  # noqa: BLE001
        return set()


def row_of(fighter, name):
    """The own row number (303 + index in fighter.rows) of a declared clip name, or None."""
    rows = fighter.get('fighter', {}).get('rows', [])
    return 303 + rows.index(name) if name in rows else None


def bind(text, plan, scale=1.0):
    for marker, role in ROLE.items():
        if '@'+marker+'@' in text:
            if role not in plan['roles']:
                raise ValueError('Missing mapped role '+role)
            text = text.replace('@'+marker+'@', str(plan['roles'][role][0]))
    if '@GRAB_WORD0@' in text:
        joint = plan['roles']['translation'][0]
        text = text.replace('@GRAB_WORD0@', hex(0x2C000000 | (joint << 11)))
    # raw hitbox word 0 with the joint of a role: @HITW0:<ROLE marker>:<word with joint 0>@ (cross-port hitboxes)
    def hit_word0(m):
        role = ROLE[m[1]]
        if role not in plan['roles']:
            raise ValueError('Missing mapped role '+role)
        return '0x%08X' % (int(m[2], 0) | (plan['roles'][role][0] << 11))
    text = re.sub(r'@HITW0:([A-Z_0-9]+):(0x[0-9A-Fa-f]+)@', hit_word0, text)
    if re.search(r'@[A-Z_0-9]+@', text):
        raise ValueError('Unresolved gameplay joint placeholder')
    lines = []
    for line in text.splitlines():
        if line.strip().startswith('hitbox raw='):
            words = [int(w,0) for w in line.split('raw=',1)[1].split(',')]
            def resized(value, signed=False):
                if signed and value >= 32768:
                    value -= 65536
                value = round(value * scale)
                if not (-32768 <= value <= 32767 if signed else 0 <= value <= 65535):
                    raise ValueError('Scaled grab dimension exceeds native packed range')
                return value & 65535
            words[1] = (resized(words[1] >> 16) << 16) | resized(words[1] & 65535,True)
            words[2] = (resized(words[2] >> 16,True) << 16) | resized(words[2] & 65535,True)
            line = 'hitbox raw=' + ','.join(f'0x{w:08X}' for w in words)
        elif line.strip().startswith('hitbox '):
            line = re.sub(r'\b(size|x|y|z)=(-?\d+(?:\.\d+)?)',
                          lambda m: f'{m[1]}={float(m[2])*scale:.9g}',line)
        lines.append(line)
    return '\n'.join(lines)+'\n'

SIZE = 1.2   # the built size of Goku (define "scale"); change here only


def scale_articles(articles, scale):
    result = copy.deepcopy(articles)
    for article in result:
        article['spawn'] = [v*scale for v in article['spawn']]
        for box in article['hitboxes']:
            box['size'] *= scale
            box['offset'] = [v*scale for v in box['offset']]
    return result

def source_losses(ir, config):
    losses, seen = [{'move':'move:special_n','frame':0,
                     'what':'Kamehameha beam presentation and continuous charge response',
                     'why':'Three authored damage tiers launch an original cyan beam proxy with four overlapping spheres. XV2 EEPK presentation, source camera and exact charged behavior were not converted.',
                     'source':'destination design'},
                    {'move':'move:rapid_jab','frame':0,'what':'Source mash/controller continuation',
                     'why':'Authored finite barrage: native rapid-jab entry flag, two-frame start, five BAC candidate pulses, forced end after49frames and automatic recovery. Infinite mash continuation is not reproduced.',
                     'source':'destination design'}], set()
    for spec in config['moves']+config['special_adaptations']:
        parity, move, scripts = move_source(ir, spec['parity'])
        if spec.get('source_candidate_windows'):
            losses.append({'move':spec['name'],'frame':(spec['windows'] or spec.get('strike') or [[0,0]])[0][0],
                           'what':'BAC candidate timing adapted to the exported striking pose',
                           'why':spec.get('pose_review','HB-NONE (remake): no hitbox; timing metadata only'),'source':'native bank pose review',
                           'source_windows':spec['source_candidate_windows'],'destination_windows':spec['windows']})
        if move['id'] in seen:
            continue
        seen.add(move['id'])
        losses.append({'move':move['id'],'frame':0,'what':'Source damage/reaction, shape and locomotion adapted to platform-fighter gameplay',
                       'why':'Melee percentage damage, angle, KBG/BKB and anatomical spheres are destination design; BAC static frames do not execute XV2 time-scale or BCM branches.',
                       'source':'parity adaptation','parity':parity})
        for src in scripts:
            for event in src['events']:
                if event['op'] in ('hitbox.create','engine.animation'):
                    continue
                losses.append({'move':move['id'],'frame':event.get('frame',0),
                               'what':event['op'],
                               'why':'Not executed as XV2 semantics. Homing/tracking and camera locks are omitted; Melee movement, authored windows and common camera apply. Source FX/audio and controller callbacks are not converted by this gameplay pass.',
                               'source':src['id'], 'evidence':src.get('provenance',{}).get('evidence',[])})
    return losses

FX_ARTICLES = {'KameOrb': 'P_TrailGokuOrb', 'KameTap': 'P_TrailGokuBeam', 'KameMid': 'P_TrailGokuBeam',
               'KameFull': 'P_TrailGokuBeamBig', 'KameSuper': 'P_TrailGokuBeamSuper'}
# state name -> [(frame, package, role, scale, end_event)]: ki aura while charging, vanish bursts, the rush trail
FX_STATES = {
    # Kamehameha presentation: converted from XV2's own effects (tools/xv2_fx.py; KAMEHAMEHA.md section 3). The charge is ~10 s (lua/goku.lua CHARGE_FRAMES): the
    # state's own frame clock ('game', FX_CLOCK) drives it, the ball grows between the chant beats (state frames 60 / 180 / 360 / 540 = the tiers) and the aura is re-attached
    # larger at each; each tier has its own beam package; the stored flash shows the tier. Cosmetic shake / flash calls are FX_EVENTS.
    'KameCharge': [(1, 'P_TrailGokuAura', 'hips', 1.0, ('off', 60)), (60, 'P_TrailGokuAura', 'hips', 1.15, ('off', 180)), (180, 'P_TrailGokuAura', 'hips', 1.3, ('off', 360)),
                   (360, 'P_TrailGokuAura', 'hips', 1.5, ('off', 540)), (540, 'P_TrailGokuAura', 'hips', 1.7, 'state_exit'),
                   (1, 'P_TrailGokuXKameCharge', 'hand.R', 1.0, 'state_exit', 'hand.L'), (1, 'P_TrailGokuXKamePressure', 'translation', 1.0, 'state_exit')],
    'KameStore1': [(1, 'P_TrailGokuXKameStore1', 'hand.R', 1.0, 'state_exit', 'hand.L')],
    'KameStore2': [(1, 'P_TrailGokuXKameStore2', 'hand.R', 1.0, 'state_exit', 'hand.L')],
    'KameStore3': [(1, 'P_TrailGokuXKameStore3', 'hand.R', 1.0, 'state_exit', 'hand.L')],
    'KameStore4': [(1, 'P_TrailGokuAura', 'hips', 1.6, 'state_exit'), (1, 'P_TrailGokuXKameStore4', 'hand.R', 1.0, 'state_exit', 'hand.L')],
    'KameTap': [(5, 'P_TrailGokuXKameTap', 'hand.R', 1.0, 'state_exit')],
    'KameThin': [(6, 'P_TrailGokuXKameThin', 'hand.R', 1.0, 'state_exit')],
    'KameMid': [(6, 'P_TrailGokuXKameMuzzle', 'hand.R', 1.0, 'emitter_life'), (6, 'P_TrailGokuXKameMid', 'hand.R', 1.0, 'state_exit')],
    'KameFull': [(8, 'P_TrailGokuXKameMuzzle', 'hand.R', 1.0, 'emitter_life'), (8, 'P_TrailGokuXKameFull', 'hand.R', 1.0, 'state_exit')],
    'KameMax': [(10, 'P_TrailGokuXKameMuzzleMax', 'hand.R', 1.0, 'emitter_life'), (10, 'P_TrailGokuXKameMax', 'hand.R', 1.0, 'state_exit')],
    'KiCharge': [(1, 'P_TrailGokuAura', 'hips', 1.3, 'state_exit')],
    'KiChargeAir': [(1, 'P_TrailGokuAura', 'hips', 1.3, 'state_exit')],
    'KameSuper': [(1, 'P_TrailGokuAura', 'hips', 1.1, 'state_exit'), (1, 'P_TrailGokuXKameSuperCharge', 'hand.R', 1.0, 'state_exit', 'hand.L'),
                  (54, 'P_TrailGokuXKameSuperMuzzle', 'hand.R', 1.0, 'emitter_life'), (54, 'P_TrailGokuXKameSuper', 'hand.R', 1.0, 'state_exit')],
    'Recovery': [(5, 'P_TrailGokuVanish', 'chest', 1.0, 'emitter_life')],
    'ITEnd': [(1, 'P_TrailGokuVanish', 'chest', 1.0, 'emitter_life')],
    'Counter': [(4, 'P_TrailGokuVanish', 'chest', 0.8, 'emitter_life')],
    'Riposte': [(1, 'P_TrailGokuVanish', 'chest', 0.8, 'emitter_life')],
    'Rush': [(2, 'P_TrailGokuDash', 'hips', 1.0, 'state_exit')],
    'RushCombo': [(1, 'P_TrailGokuDash', 'hips', 1.0, 'state_exit')],
}


if os.environ.get('KAME_PROBE'):   # measurement build (tools/kame_ball.py): two probe points on the charge, never ship
    for _st in ('KameCharge', 'KameStore1', 'KameStore2', 'KameStore3', 'KameStore4', 'KameSuper'):
        FX_STATES[_st] += [(1, 'P_TrailGokuXKameBallProbe0', 'hand.R', 1.0, 'state_exit'), (1, 'P_TrailGokuXKameBallProbeM', 'hand.R', 1.0, 'state_exit', 'hand.L')]
FX_CLOCK = {'KameCharge': 'game'}   # states whose call frames are state (game) frames, not animation frames: the charge's clip is stretched, its script clock is not game time
# cosmetic camera events (render-only, no package): state -> [(frame, shake (amp NDC, frames, seed) or None, flash (rgb, alpha, frames) or None)]. The release flash is short
# and faint on every tier but Max and Super (the owner saw a pale haze); the charge shakes only as it nears Max. Super's numbers follow the camera clip GOK_CAM_CKM_C
# (Position range 1.6 / 0.4 / 5.0 m over 225 frames: a long heavy shake once the beam is out, approximated as two decaying shakes).
BLUE = [0.55, 0.8, 1.0]
FX_EVENTS = {
    'KameCharge': [(420, (0.0025, 120, 3), None), (540, (0.006, 70, 4), (BLUE, 0.07, 3)), (590, (0.010, 40, 5), None)] + [(f, (0.004, 45, 7 + f % 5), None) for f in range(640, 1300, 45)],   # the Max hold: a low sustained tremor
    'KameStore4': [(1, None, (BLUE, 0.05, 3))],
    'KameMid': [(6, (0.007, 8, 5), None)],
    'KameFull': [(8, (0.013, 12, 5), (BLUE, 0.05, 2))],
    'KameMax': [(10, (0.028, 24, 5), (BLUE, 0.15, 5))],
    'KameSuper': [(54, (0.032, 36, 5), (BLUE, 0.2, 6)), (80, (0.05, 70, 6), None)],
}


# The Instant Transmission rolls (phase 4). XV2 (skill 001_GOK_KUR, BAC entry 0) plays the common effect 42 at frame 10: three wind-streak ribbons (Act_WindShort.etr) on the
# left shoulder, left knee and right hand with the offsets below (metres x 11.4). Spot dodge: the same at frame 8 (its hidden gap is shorter).
def _it_calls(frame):
    S = 11.4
    return [dict(frame=frame, package='P_TrailGokuITWind' + sfx, bone=role, offset=[o * S for o in off])
            for sfx, role, off, w, blend in (('Shoulder', 'shoulder.L', (0.4, 0.0, 0.4), 0.15, 'alpha'), ('Knee', 'lower_leg.L', (0.0, 0.0, -0.3), 0.10, 'add'),
                                             ('Hand', 'hand.R', (-0.25, 0.0, 0.0), 0.05, 'add'))]


ROW_FX = {'EscapeF': (233, 'moves/escape_f.genoasm', _it_calls(10)), 'EscapeB': (234, 'moves/escape_b.genoasm', _it_calls(10)),
          'EscapeN': (235, 'moves/escape_n.genoasm', _it_calls(8))}


def write_fx(package, fighter, plan, cfg):
    """Copy the original effect packages (tools/fx_build.py) into the package and bind them (geno.md 20.3)."""
    src = ROOT/'_build/goku-xv2/fx'
    if not src.exists():
        print('fx: _build/goku-xv2/fx missing (run tools/fx_build.py); the package has no effects')
        return
    dst = package/'fx'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    for a in fighter.get('articles', []):
        pkg = FX_ARTICLES.get(a['name'])
        if pkg:
            a['fx'] = pkg
            a['show_model'] = True  # the proxy mesh stays under the effect
    states = {s['name']: s for s in fighter['states']}
    scripts = {sa['name']: sa['script'] for sa in cfg['special_adaptations']}
    entries = []
    for name, calls in FX_STATES.items():
        st = states.get(name)
        if not st or not isinstance(st.get('subaction'), int):
            continue
        events = [dict({'frame': f}, **({'shake': {'amp': sk[0], 'frames': sk[1], 'seed': sk[2]}} if sk else {}),
                       **({'flash': {'color': fl[0], 'alpha': fl[1], 'frames': fl[2]}} if fl else {})) for f, sk, fl in FX_EVENTS.get(name, [])]
        entries.append({'state': name, 'subaction': st['subaction'], 'clock': FX_CLOCK.get(name, 'animation'), 'script': scripts.get(name, 'moves/rush.genoasm'),
                        'calls': events + [dict({'frame': c[0], 'macro': 'goku_'+c[1][11:].lower(), 'effect': c[1], 'package': c[1], 'bone': c[2],
                                   'joint': plan['roles'][c[2]][0], 'offset': [0, 0, 0], 'rotation': [0, 0, 0], 'scale': c[3],
                                   'follow': True, 'when': [], 'end_event': c[4][0] if isinstance(c[4], tuple) else c[4]},
                                   # an end given as ('off', frame) detaches the call on that clock frame (the aura steps replace each other)
                                   **({'end_frame': c[4][1]} if isinstance(c[4], tuple) else {}),
                                   # a 6th element names a second joint: the effect origin is the MIDPOINT of the two (geno.md 20.3 "joint2"), the axes the first joint's
                                   **({'joint2': plan['roles'][c[5]][0]} if len(c) > 5 else {})) for c in calls]})
    # rows that are not Geno states (the Instant Transmission rolls): a binding is matched by subaction, so the row's index is enough (geno.md 20.3)
    from tools.geno import report as _rep
    msub = _rep.motion_subactions()
    for name, (motion, script_, calls) in ROW_FX.items():
        row = msub[motion][1]
        entries.append({'state': name, 'subaction': row, 'clock': 'animation', 'script': script_,
                        'calls': [dict({'frame': c['frame'], 'macro': 'goku_' + c['package'][11:].lower(), 'effect': c['package'], 'package': c['package'], 'bone': c['bone'],
                                        'joint': plan['roles'][c['bone']][0], 'offset': c['offset'], 'rotation': [0, 0, 0], 'scale': 1.0, 'follow': True, 'when': [],
                                        'end_event': 'emitter_life'}) for c in calls]})
    (dst/'fx_bindings.json').write_text(json.dumps({'geno_fx_bindings': 1, 'fighter': 'goku-xv2', 'host': 'mario', 'unit_scale': 1.0,
                                                    'states': entries}, indent=1), encoding='utf-8')
    fighter['fx_bindings'] = 'fx/fx_bindings.json'



def write_kame_audio(package, fighter):
    """The Kamehameha's own sounds (tools/kame_audio.py): .gnsnd clips in files/ bound as audio.voice rows on the retail ids the scripts play."""
    # XV2's own voice and SFX when converted (tools/xv2_audio.py, Japanese by default; run it with --lang en for the English lines), else the synthesised fallback
    from xv2_audio import BINDINGS, OUT as AUDIO, STOPPABLE, HUM_STATES
    if not (AUDIO/'GnKameSeShot.gnsnd').exists():
        from kame_audio import BINDINGS, OUT as AUDIO
        STOPPABLE = set()
        if not (AUDIO/'GnKameFire.gnsnd').exists():
            print('audio: _build/goku-xv2/audio missing (run tools/xv2_audio.py); the Kamehameha plays no own sounds')
            return
    rows = []
    for sid, clip in BINDINGS.items():
        shutil.copy2(AUDIO/(clip+'.gnsnd'), package/'files'/(clip+'.gnsnd'))
        rows.append(dict({'sfx': sid, 'file': clip+'.gnsnd', 'volume': 127},
                         **({'stoppable': True, 'while_states': list(HUM_STATES)} if sid in STOPPABLE else {})))
    fighter['audio'] = {'voice': rows}


def write_presentation(package, fighter):
    """Select icon, portrait and HUD/results stock icon from his own converted model (tools/presentation_art.py renders the PNGs)."""
    # A gameplay-only reapply retains a completed CSProject presentation.
    own = fighter.get('presentation', {})
    values = [n for k in ('icon', 'portrait', 'stock', 'results')
              for v in [own.get(k)] for n in (v if isinstance(v, list) else [v])]
    if all(isinstance(n, str) and n.startswith('GnUi_') and
                      (package/'files'/n).is_file() for n in values):
        return
    art = ROOT/'_build/goku-xv2/presentation'
    if not all((art/n).exists() for n in ('icon.png', 'portrait.png', 'stock.png')):
        print('presentation: _build/goku-xv2/presentation/*.png missing (run tools/presentation_art.py in Blender); no own select art')
        return
    tool = Path(os.environ.get('GW_MELEE') or ROOT/'melee')/'pc/tools/png2gx.py'
    names = {}
    for key, png, fmt in (('icon', 'icon.png', 'rgb5a3'), ('portrait', 'portrait.png', 'rgb5a3'), ('stock', 'stock.png', 'rgba8')):
        name = f'GnGokuXv2_{key}.gxtex'
        subprocess.run([sys.executable, str(tool), str(art/png), str(package/'files'/name), '--format', fmt, '--allow-odd-size'], check=True, capture_output=True)
        names[key] = name
    fighter['presentation'] = {'icon': names['icon'], 'portrait': [names['portrait']], 'stock': [names['stock']]}



def apply(package, art_build, ir_path=None):
    package, art_build = generated(package), generated(art_build)
    cfg = load(SG.path())
    art_report = AUTHOR/'art-report.json'
    height = load(art_report)['geometry']['height']
    reference_height = cfg['geometry_reference_height']
    scale = height / reference_height
    if not 8 <= height <= 20 or reference_height <= 0:
        raise ValueError('Invalid gameplay/art dimension contract')
    ir = load(ir_path or PORT/cfg['source_ir'])
    host = load(PORT/cfg['host_ir'])
    plan_path = package/'files/plan.json'
    plan = load(plan_path)
    if plan['joint_count'] > 128:
        raise ValueError('Native define joint-to-part storage limit requires <=128 joints')
    # Native definitions allocate the stock 303 animation rows. The artist table has
    # only stock names, so virtual custom clips need explicit runtime row bindings.
    plan['row_clips'].extend([None]*max(0,303-len(plan['row_clips'])))
    # 2026-10-09 (owner #7, landing sinks to the torso). The engine's ECB is the bounding box of the six x44 joints (mpColl_LoadECB_JObj: bottom =
    # lowest joint - 2, clamped at 0, grounded or not) and the donor layout puts two knees and the hip there. His flight-stance aerials fold the
    # legs, so those joints sit 5-8 units above the root, the ECB bottom floats with them and he lands that far INTO the floor (measured:
    # root y -8.3 at touchdown of a late fair). TopN in the hip slot keeps the ECB bottom at the root in every pose; shoulders/head/knees still
    # shape the width and the crouch height. Plan-level, Goku only: no other fighter's plan or the engine changes.
    ecb = plan['ftdata']['x44_ecb']
    hip = next(e for e in ecb if e['role'] in ('HipN', 'TopN'))
    hip.update(role='TopN', joint=0, name='TopN')
    # 2026-10-11 (owner: the shield bubble was centred at his forearms). x8_part_bytes slot 1 is the SHIELD part (plan_parts: item, shield, head, feet) and it was ThrowN = the grab
    # anchor, which hangs off the root 8 units in front of the chest for the held victim. A first fix pointed it at YRotN, and the guard code scales that joint by the shield size
    # (ftCo_Guard.c:216,338,806,880), which grew the whole body. Retail's ThrowN is a LEAF under YRotN with an identity local; the shield slot now has the same: shield_anchor, a weightless
    # leaf off the root at the pelvis height (xv2_to_artist.py), so the bubble is body-centred and its scaling moves nothing else. The grab anchor stays the throw / hold attach point.
    shield = next(j['index'] for j in plan['joints'] if j['name'] == 'shield_anchor')
    plan['ftdata']['x8_part_bytes'][1] = {'role': 'ThrowN', 'joint': shield, 'name': 'shield_anchor'}
    for state in cfg['states']:
        if isinstance(state['subaction'], str):
            continue  # 'clip:<name>' states bind to a declared clip row later (row_of)
        clip_name = state.get('clip', state['name'])  # air partners share the ground state's clip
        if clip_name not in plan['bank']['clips']:
            raise ValueError('Custom state has no bank clip: '+state['name'])
        plan['row_clips'][state['subaction']] = clip_name
        # BuildOwn gives stock motion mappings precedence over row_clips. Mario's
        # eight special motions343..350 claim animation rows295..302 even though
        # the authored special-input table makes these donor motions unreachable.
        for motion in plan['motion_rows']:
            if motion['motion'] == 343 + state['subaction'] - 295:
                motion['clip'] = clip_name
    doc = load(package/'geno.json')
    fighter = doc['fighters'][0]
    throw_standin.apply(fighter, cfg)
    lib = AUTHOR/'clip-library.json'
    if lib.exists():  # LAB CLIPS library: unbound declared rows 303.. (geno.md fighter.rows)
        fighter.setdefault('fighter', {})['rows'] = [c['name'] for c in load(lib)['clips']] + \
            [n for n in ('ITEnd', 'KiCharge', 'KiChargeAir', 'KameStore1', 'KameStore2', 'KameStore3', 'KameStore4', 'KameThin', 'KameMax', 'KameSuper', 'RushCombo', 'Homing', 'FlightUp', 'FlightF', 'FlightB', 'FlightNair', 'FlightFair', 'FlightBair', 'FlightUair', 'FlightDair') if n in plan_clip_names(package)]
    if cfg.get('cape'):
        fighter['cape'] = cfg['cape']  # Instant Transmission (geno.cape) parameters
    for st in fighter.get('states', []):  # states that name a declared clip get its own row number
        if isinstance(st.get('subaction'), str) and st['subaction'].startswith('clip:'):
            st['subaction'] = row_of(fighter, st['subaction'][5:])
    if cfg.get('toon'):
        fighter['toon'] = cfg['toon']  # engine cel shading (2026-10-08, geno.md toon); visual only
    attrs, attr_evidence = attributes(ir, host)
    # Reference speeds are geometry/animation measurements; preserve measured artist values.
    for key in ('slow_walk_max','mid_walk_point','fast_walk_min','run_animation_scaling'):
        measured = fighter.get('attributes',{}).get(key)
        if measured is not None:
            attrs[key] = measured
            next(e for e in attr_evidence if e['field']==key).update(value=measured,
                basis='Artist output reference speed; inspect artist build-report for measurement/fallback status')
    attrs, attr_evidence = apply_attribute_overrides(attrs, attr_evidence, cfg)
    overlays, audit = {}, []
    motion_rows = report.motion_subactions()
    # Stock ftCo_SM names differ from action names (AttackS3 versus AttackS3S).
    # Resolve common authored rows through the native motion map, as BuildOwn does.
    motion_clips = {m['motion']:m['clip'] for m in plan['motion_rows']}
    for move in cfg['moves']:
        for motion in move['motions']:
            row = motion_rows[motion][1]
            if motion_clips.get(motion):
                plan['row_clips'][row] = motion_clips[motion]
    # goku-stage 2026-10-11 (owner: dash grab and dash attack stop dead): a row whose flags carry 0x80000000 (fp->x594_b0) is animation-driven, so ft_80085030 pulls the
    # ground speed to the clip's TransN speed on the first frame, and these clips have none (measured: gr_vel 1.8 -> 0.0 on frame 1; retail Falcon's CatchDash slides on friction).
    # Plain flags (0) for the two dash attacks: the dash speed is kept and ground friction slows it, like retail.
    rflags = plan.get('row_flags') or [None] * len(plan['row_clips'])
    for move in cfg['moves']:
        if move['name'] in ('dash_attack', 'dash_grab'):
            for motion in move['motions']:
                rflags[motion_rows[motion][1]] = 0
    plan['row_flags'] = rflags
    for spec in cfg['moves']+cfg['special_adaptations']:
        declared = None
        parity, move, sources = move_source(ir, spec['parity'])
        text = bind((PORT/spec['script']).read_text(encoding='utf-8'), plan, scale)
        words = script.assemble(text, cfg['states'])
        name = Path(spec['script']).stem
        (package/'moves').mkdir(exist_ok=True)
        (package/spec['script']).write_text(text, encoding='utf-8')
        destination = package/'moves'/f'{name}.words'
        destination.write_text(' '.join(f'0x{x:08X}' for x in words)+'\n', encoding='utf-8')
        info = report.frames(words)
        # The engine does not wait for a frame already past, so a script out of start-frame order, or one that
        # reuses a live slot, fires differently from the windows declared below: refuse it with the reasons.
        timing = report.timing_problems(words)
        if timing:
            raise ValueError('Hitbox timing in %s would not run as written: %s' % (name, ' '.join(timing)))
        if 'windows' in spec:
            actual = [(b['start'], b['end']-b['start']) for b in info['hitboxes']]
            if actual != [tuple(w) for w in spec['windows']]:
                raise ValueError('Authored window declaration disagrees with assembly: %s: gameplay.json windows %s but the script gives %s'
                                 % (name, [list(w) for w in spec['windows']], [list(w) for w in actual]))
        if 'motions' in spec:
            rows = sorted({motion_rows[m][1] for m in spec['motions']})
            for row in rows:
                overlays[row] = {'index':row,'file':f'moves/{name}.words','move_tag':spec['tag']}
        else:
            state = next(s for s in cfg['states'] if s['name']==spec['name'])
            sub = state['subaction']
            declared = None
            if isinstance(sub, str):  # 'clip:<name>': a declared own row (fighter.rows), 303 on
                declared = sub[5:]
                sub = row_of(fighter, declared)
                if sub is None:
                    raise ValueError(name+': declared clip row missing: '+declared)
            rows = [sub]
            overlays[rows[0]] = {'index':rows[0],'file':f'moves/{name}.words','move_tag':'special'}
        for row in rows:
            clips = plan['row_clips']
            clip = declared if (declared and row == rows[0]) else (clips[row] if row < len(clips) else None)
            if not clip or clip not in plan['bank']['clips']:
                raise ValueError(f'{name}: animation row {row} has no authored bank clip')
            frames = plan['bank']['clips'][clip]['frames']
            if spec.get('minimum_clip_frames') and frames < spec['minimum_clip_frames']:  # absent in the stripped gameplay.json
                raise ValueError(f'{name}: clip {clip} has {frames} frames; needs {spec["minimum_clip_frames"]}')
        audit.append({'move':name,'parity':parity,'source_scripts':[s['id'] for s in sources],
                      'rows':rows,'script_frames':info,'classification':'destination design / static source candidates',
                      'pose_review':spec.get('pose_review'),
                      'words_sha256':hashlib.sha256(destination.read_bytes()).hexdigest()})
    # Row scripts (row_scripts.json, written by cross_port.py): the ledge set's retail scripts (intangibility, hitboxes) overlaid on their rows; not gameplay.json moves
    rs_file = PORT/'row_scripts.json'
    if rs_file.exists():
        row_by_name = {v[0]: v[1] for v in motion_rows.values()}
        for rname, rs in json.loads(rs_file.read_text(encoding='utf-8')).items():
            text = bind((PORT/rs['script']).read_text(encoding='utf-8'), plan, scale)
            words = script.assemble(text, cfg['states'])
            timing = report.timing_problems(words)
            if timing:
                raise ValueError('Hitbox timing in %s would not run as written: %s' % (rs['script'], ' '.join(timing)))
            sname = Path(rs['script']).stem
            (package/'moves').mkdir(exist_ok=True)
            (package/rs['script']).write_text(text, encoding='utf-8')
            (package/'moves'/f'{sname}.words').write_text(' '.join(f'0x{x:08X}' for x in words)+chr(10), encoding='utf-8')
            overlays[row_by_name[rname]] = {'index':row_by_name[rname],'file':f'moves/{sname}.words'}
            audit.append({'move':sname,'parity':None,'source_scripts':[rs['source']],'rows':[row_by_name[rname]],'script_frames':report.frames(words),
                          'classification':'cross-port row script (retail source row)','words_sha256':hashlib.sha256(' '.join(f'0x{x:08X}' for x in words).encode()).hexdigest()})
    fighter.update({key:cfg[key] for key in ('lua','states','specials','articles','jumps')})
    if cfg.get('controls'):
        fighter['controls'] = cfg['controls']   # per-fighter CSS layouts/extras (docs/geno.md section 26): Goku's layout B (Y -> D-pad Down = the blast input)
    import copy
    fighter['states'] = copy.deepcopy(cfg['states'])
    for st in fighter['states']:
        st.pop('clip', None)
        st.pop('pick', None)  # provenance note lives in gameplay.json/PICKS.md, not the runtime schema
        if isinstance(st.get('subaction'), str) and st['subaction'].startswith('clip:'):
            row = row_of(fighter, st['subaction'][5:])
            if row is None:
                raise ValueError('State clip row not declared: '+st['name'])
            st['subaction'] = row
    # Built size (owner 2026-10-11: "Goku should be at 1.2 scale for his default size"). The engine's per-fighter scale (define "scale", x34_scale.x, the
    # mechanism Giant / Tiny Melee use) scales the model, fighter hurt/hitboxes (applied where they are tested), ECB, ledge snap, camera box and the
    # attributes, exactly as the LAB's gd.set_scale does. Articles (the Kamehameha beam, the ki blast) are authored in world units and are not owned by
    # that scale, so they get the same factor here: spawn offsets, hit boxes and the ki model.
    fighter['scale'] = SIZE
    fighter['articles'] = scale_articles(cfg['articles'],scale*SIZE)
    fighter['attributes'] = attrs
    fighter['subactions'] = [overlays[k] for k in sorted(overlays)]
    fighter['special_attributes'] = []
    fighter.pop('fx_bindings', None)
    write_fx(package, fighter, plan, cfg)
    write_kame_audio(package, fighter)
    write_presentation(package, fighter)
    # Native common callbacks are explicit; moves remain source-owned scripts with common engine flow.
    fighter['common_states'] = [{'motion':m,'subaction':motion_rows[m][1]} for spec in cfg['moves'] for m in spec['motions']]
    ki = package/'files/GnGokuKi.dat'
    from ki_model import build as build_ki
    build_ki(package,art_build,scale*SIZE)
    if ki.exists():
        for article in fighter['articles']:
            article['model'] = {'file':ki.name,'symbol':'goku_ki_joint'}
    else:
        raise ValueError('Kamehameha article model missing: '+str(ki))
    (package/'lua').mkdir(exist_ok=True)
    lua_text = (PORT/'lua/goku.lua').read_text(encoding='utf-8')
    (package/'lua/goku_ki.lua').write_text(lua_text, encoding='utf-8')  # the combo package (geno 11) installs this one
    nl = chr(10)
    (package/'lua/goku.lua').write_text(nl.join(l for l in lua_text.split(nl) if '-- @KI' not in l), encoding='utf-8')
    doc['geno'] = 10
    write(package/'geno.json',doc)
    try:  # the LAB CLIPS MOVES table lives in the package's geno-lab copy, which the artist build re-copies
        sys.path.insert(0, str(PORT/'tools')); import movemap; movemap.main()
    except Exception as e:  # noqa: BLE001 - the move map is a LAB aid, never a build blocker
        print('movemap: skipped:', e)
    manifest = load(package/'mod.json')
    manifest['version'] = '0.2.0'
    write(package/'mod.json',manifest)
    write(plan_path,plan)
    write(art_build/'plan.json',plan)
    write(art_build/'attribute-design.json',attr_evidence)
    write(art_build/'geometry-scale.json',{
        'reference_height':reference_height,'art_bind_height':height,'factor':scale,
        'basis':'art-report.json geometry.height / gameplay.json geometry_reference_height',
        'art_report_sha256':hashlib.sha256(art_report.read_bytes()).hexdigest(),
        'scaled':['fighter hitbox radii/local offsets','grab packed radius/local offsets',
                  'article spawn/radii/local offsets','Ki proxy mesh vertex positions'],
        'hurtboxes':'refit from current mesh by audit_gameplay',
        'physics':'Host attributes and authored movement/projectile velocities retained; model_scaling=1',
        'idempotence':'Always applies to maintained source templates/config, never generated dimensions'})
    write(art_build/'gameplay-parity.json',{'source_sha256':hashlib.sha256((ir_path or PORT/cfg['source_ir']).read_bytes()).hexdigest(),'moves':audit})
    write_losses(art_build/'gameplay-losses.json',{'losses':source_losses(ir,cfg)})
    reports = [load(art_build/'gameplay-losses.json')]
    for path in (AUTHOR/'conversion_losses.json',
                 AUTHOR/'art-losses.json'):
        if path.exists():
            reports.append(load(path))
    art_report = AUTHOR/'art-report.json'
    if art_report.exists():
        art = load(art_report)
        art_losses = [{'move':'art','frame':0,'what':limitation,
                       'why':'Explicit art adaptation limitation; see generated art-report.json for parity and source BlobRefs.',
                       'source':'art-report.json'} for limitation in art['limitations']]
        geo = art['geometry']
        art_losses.append({'move':'art','frame':0,'what':'Source influences reduced to at most two per vertex',
                           'why':'Artist/native conversion contract; discarded weight is normalized onto retained influences.',
                           'source':'art-report.json','vertices':geo['source_influences_reduced_vertices'],
                           'max_discarded_weight':geo['max_discarded_weight'],'mean_discarded_weight':geo['mean_discarded_weight']})
        reports.append({'losses':art_losses})
    REPORTS.mkdir(parents=True,exist_ok=True)
    write_losses(REPORTS/'conversion_losses.json',*reports)
    return package

STAMP_NAME = '.stage_a.json'   # written next to <out>/mods and <out>/build after a successful FULL build

def stage_a_inputs(fighter_path):
    """Files whose change invalidates Stage A (the artist pipeline: plan, mesh, animation bank): the fighter config and the art next to it,
    the ground-mode / splice tables and the converter code. Gameplay inputs (moves/*.genoasm, gameplay.json, attributes) are NOT here."""
    fighter_path = Path(fighter_path).resolve()
    art = fighter_path.parent
    files = [fighter_path]
    for pattern in ('*.glb', '*.blend', '*.png', 'clip-library.json', 'art-report.json'):
        files.extend(sorted(art.glob(pattern)))
    files += [PORT/'ground_modes.json', PORT/'splices.json', PORT/'tools/xv2_to_artist.py', PORT/'tools/splice.py', HAND_FILE]   # HAND_FILE: hand-authored deltas (anim/hand.json)
    files += sorted((ROOT/'tools/geno/artist').rglob('*.py'))
    return sorted({f.resolve() for f in files if f.is_file()})

def stage_a_signature(fighter_path):
    sig = {}
    for f in stage_a_inputs(fighter_path):
        st = f.stat()
        sig[str(f)] = [st.st_size, st.st_mtime_ns]
    return sig

def stage_a_stale(fighter_path, out):
    """None when the Stage A outputs are present and current, else the reason (a short string)."""
    out = Path(out)
    stamp = out/STAMP_NAME
    if not stamp.is_file():
        return 'no full-build stamp at %s (run one full build first)' % stamp
    try:
        key = load(fighter_path)['key']
    except Exception as e:  # noqa: BLE001
        return 'cannot read fighter config: %s' % e
    for need in (out/'mods'/key/'geno.json', out/'mods'/key/'files/plan.json', out/'build'):
        if not need.exists():
            return 'Stage A output missing: %s' % need
    old = load(stamp).get('inputs', {})
    new = stage_a_signature(fighter_path)
    changed = sorted(k for k in set(old)|set(new) if old.get(k) != new.get(k))
    if changed:
        names = ', '.join(Path(k).name for k in changed[:4])
        return 'Stage A input changed since the last full build: %s%s' % (names, ' (+%d more)' % (len(changed)-4) if len(changed) > 4 else '')
    return None

def write_stamp(fighter_path, out):
    write(Path(out)/STAMP_NAME, {'schema': 'goku-stage-a/1', 'inputs': stage_a_signature(fighter_path)})

def finish_checks(package, art_build, ground):
    """audit_gameplay is run by the caller; this is the ground audit (optional) and the static Geno checks. Returns an exit code."""
    if ground:
        ga = subprocess.run([sys.executable,'-B',str(PORT/'tools/ground_audit.py')],cwd=ROOT,capture_output=True,text=True)
        print('Ground audit:',ga.stdout.strip() or ga.stderr.strip()[-300:])
        if ga.returncode:
            print('Ground audit failed: a ground row sinks below the floor (see %s)'%(REPORTS/'ground-audit.json'))
            return 1
    for command in ([sys.executable,'-B','-m','tools.geno.check',str(package),'--json'],
                    [sys.executable,'-B','-m','tools.geno.report',str(package),'--frames','--json']):
        result = subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        name = 'geno-check.json' if 'tools.geno.check' in command else 'geno-report.json'
        (art_build/name).write_text(result.stdout,encoding='utf-8')
        if result.returncode:
            print(result.stdout+result.stderr)
            return result.returncode
    return 0

def render_presentation(package, fighter_path=None):
    """Optional full-build step, through the shared standalone UI renderer."""
    from tools.csp.render_ui import main as render_ui
    args = ['--project', str(PORT), '--package', str(package), '--costume', 'all']
    source = Path(fighter_path) if fighter_path else AUTHOR/'fighter.json'
    if source.is_file():
        args += ['--fighter', str(source)]
        glb = load(source).get('art', {}).get('glb')
        if glb:
            args += ['--art', str((source.parent/glb).resolve())]
    return render_ui(args)


def main(argv=None):
    import time
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ui',action='store_true',
                    help='render CSProject UI after a full build (off by default; --auto forces full; incompatible with --gameplay-only)')
    ap.add_argument('--package',type=Path)
    ap.add_argument('--art-build',type=Path)
    ap.add_argument('--fighter',type=Path)
    ap.add_argument('--out',type=Path,default=AUTHOR/'package')
    ap.add_argument('--gameplay-only',action='store_true',
                    help='run only Stage B (gameplay reapply) + audit_gameplay on the existing package; needs --fighter; refuses when Stage A outputs are missing/stale')
    ap.add_argument('--auto',action='store_true',
                    help='the Workbench mode: --gameplay-only when the Stage A outputs are current, else a full build')
    ap.add_argument('--no-audit',action='store_true',help='with --gameplay-only/--auto: skip audit_gameplay too')
    args = ap.parse_args(argv)
    t0 = time.time()
    if args.ui and args.gameplay_only:
        ap.error('--ui requires a full build; omit --gameplay-only')
    if (args.gameplay_only or args.auto) and not args.fighter:
        ap.error('--gameplay-only/--auto need --fighter (the stale check reads its inputs)')
    mode = 'full'
    if (args.gameplay_only or args.auto) and not args.ui:
        generated(args.out)
        reason = stage_a_stale(args.fighter, args.out)
        if reason is None:
            mode = 'gameplay-only'
        elif args.gameplay_only:
            print('build: --gameplay-only refused: %s. Run a full build (without --gameplay-only).' % reason)
            return 2
        else:
            print('build: full build needed: %s' % reason,flush=True)
    if mode == 'gameplay-only':
        key = load(args.fighter)['key']
        package, art_build = args.out/'mods'/key, args.out/'build'
        print('[1/3] reapply gameplay',flush=True)
        package = apply(package,art_build)
        if not args.no_audit:
            print('[2/3] audit gameplay',flush=True)
            from audit_gameplay import audit
            problems = audit(package,art_build,fit=True)
            if problems:
                print('Gameplay audit failed:',problems)
                return 1
        print('[3/3] static Geno checks',flush=True)
        code = finish_checks(package,art_build,ground=False)
        if code:
            return code
        print('BUILD_MODE: gameplay-only %.1fs' % (time.time()-t0))
        print('Gameplay reapplied%s (Stage A skipped, no ground audit):' % ('' if args.no_audit else ' and audited'),package)
        return 0
    if args.fighter:
        from tools.geno.artist import pipeline
        generated(args.out)
        result, fighter = pipeline.build(str(args.fighter),str(args.out))
        if result:
            return result
        args.package = args.out/'mods'/fighter.key
        args.art_build = args.out/'build'
    if not args.package or not args.art_build:
        ap.error('Supply --package and --art-build, or --fighter')
    print('BUILD_PHASE: reapply gameplay',flush=True)
    package = apply(args.package,args.art_build)
    print('BUILD_PHASE: audit gameplay',flush=True)
    from audit_gameplay import audit
    problems = audit(package,args.art_build,fit=True)
    if problems:
        print('Gameplay audit failed:',problems)
        return 1
    if args.ui:
        code = render_presentation(package,args.fighter)
        if code:
            return code
    print('BUILD_PHASE: static checks and ground audit',flush=True)
    code = finish_checks(package,args.art_build,ground=True)
    if code:
        return code
    if args.fighter:
        write_stamp(args.fighter,args.out)
    print('BUILD_MODE: full %.1fs' % (time.time()-t0))
    print('Gameplay reapplied and static Geno checks passed:',package)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
