#!/usr/bin/env python3
"""Census Ultimate ACMD effects and bind trail's own packages to Melee subactions.

The output is derived game data: keep it under _build/, beside the imported .gfx.json files.
ACMD is parsed from the local Ghidra C with acmd_parse, using the same joint table and
unit scale as acmd_to_ftcmd. Common effects and sword trails remain census-only.
"""
from pathlib import Path
import argparse
from collections import Counter
import json
import os
import re
import shutil

import acmd_parse as A
import acmd_to_ftcmd as F
import plan_parts
import trail_magic_geno as M
from acmd_loss import LossGuard, write_losses
from convert_ultimate_anim import INSTANCES, TOOL
from trail_specials_geno import HOSTS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
EFFECT_CMDS = {'EFFECT', 'EFFECT_ALPHA', 'EFFECT_FOLLOW', 'EFFECT_FOLLOW_ALPHA',
               'EFFECT_FOLLOW_NO_STOP', 'EFFECT_FLW_POS', 'EFFECT_GLOBAL',
               'FOOT_EFFECT', 'LANDING_EFFECT', 'DOWN_EFFECT'}
END_CMDS = {'EFFECT_OFF_KIND', 'EFFECT_DETACH_KIND'}
COMMON_EFFECT_NAMES = (
    'null', 'sys_smash_flash_s', 'sys_sliding_smoke', 'sys_landing_smoke',
    'sys_landing_smoke_s', 'sys_attack_speedline', 'sys_piyo', 'sys_crown',
    'sys_piyopiyo', 'sys_atk_smoke', 'sys_run_smoke', 'sys_v_smoke_a',
    'sys_jump_smoke', 'sys_down_smoke', 'sys_dash_smoke', 'sys_turn_smoke',
    'sys_jump_aerial', 'sys_smash_flash', 'sys_whirlwind_l',
)

# Sora's special states and the ACMD effect script each plays. State names and rows are the ones
# trail_specials_geno.py (HOSTS) and trail_magic_geno.py (CAST) install. Every clip is bound on the
# "animation" clock, which is the CLIP frame (fp->cur_anim_frame, geno.md 20.3): ACMD effect frames
# count motion (clip) frames whatever the motion rate, and the Geno states play the real clips at
# their rate (dashes 13/12, END clips 35/40/45 game frames), so a clip-frame clock needs no rescaling.
# Fixed rows that share an effect script with another row repeat it (LwAttackBack plays the Counter).
SPECIAL = {
    'SStart': 'effect_specialsstart', 'SSearch': 'effect_specialssearch',
    'SDash1': 'effect_specials1', 'SDash2': 'effect_specials2', 'SDash3': 'effect_specials3',
    'Hi': 'effect_specialhi', 'HiAir': 'effect_specialairhi',
    'LwStart': 'effect_speciallwstart', 'LwStartAir': 'effect_specialairlwstart',
    'LwAttack': 'effect_speciallw', 'LwAttackAir': 'effect_specialairlw',
    'LwAttackBack': 'effect_speciallw', 'LwAttackBackAir': 'effect_specialairlw',
    'LwRebound': 'effect_speciallw', 'LwReboundAir': 'effect_specialairlw',
    'S3Combo2': 'effect_attacks32', 'S3Combo3': 'effect_attacks33',
}
# One Geno state serves ground and air for these: the ACMD has a ground script and an `air` twin
# (effect_specialairs1 for effect_specials1), and the call carries the situation it came from.
SHARED_AIR = ('SStart', 'SSearch', 'SDash1', 'SDash2', 'SDash3')
# States with no effect script of their own in the ACMD (the END clips, the turn clips): see SPECIAL_NOTES.
SPECIAL_NOTES = {
    'SStart2': 'level TURN clip: no effect script of its own',
    'STurnUp': 'turn clip: no effect script of its own',
    'STurnDown': 'turn clip: no effect script of its own',
    'SEnd': 'END clip: no effect script (the ACMD has none; the old binding replayed the third dash)',
    'SEndAir': 'END clip: no effect script',
}


def cast_script(state):
    """The effect script of a magic cast part: Firaga/1start -> effect_specialn1start, air -> specialairn..."""
    for name, _row, clip, suffix, air in M.CAST:
        if name == state:
            return 'effect_special' + ('air' if air else '') + 'n' + suffix
    raise KeyError(state)


def air_twin(script):
    """effect_specials1 -> effect_specialairs1."""
    return script.replace('effect_special', 'effect_specialair', 1)


def effect_name(set_name):
    """EffectLibrary P_TrailKeybladeFlare -> ACMD trail_keyblade_flare."""
    stem = set_name[2:] if set_name.startswith('P_') else set_name
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', stem).lower()


def own_names(dump):
    sets = sorted(x for x in os.listdir(dump) if os.path.isdir(os.path.join(dump, x)))
    return sets, {A.hash40(effect_name(x)): (effect_name(x), x) for x in sets}


def parsed_rows(acmd, own):
    agents, scripts = A.name_tables('trail')
    hashes = dict(scripts)
    hashes.update({h: v[0] for h, v in own.items()})
    hashes.update({A.hash40(n): n for n in COMMON_EFFECT_NAMES})
    body = json.load(open(os.path.join(INSTANCES, 'trail.ultimate-body.ir.json'), encoding='utf-8'))
    for j in body['assets']['skeletons'][0]['joints']:
        hashes[A.hash40(j['name'].lower())] = j['name'].lower()
    for bone in ('top', 'rot', 'hip', 'throw'):
        hashes[A.hash40(bone)] = bone
    nro = A.Nro(os.path.join(TOOL, 'workspace', 'extracted', 'prebuilt', 'nro',
                            'release', 'lua2cpp_trail.nro'))
    helpers = A.helper_names(acmd)
    rows = []
    for r in A.load_index(acmd):
        if r['kind'] != 'effect':
            continue
        r['agent'] = agents.get(int(r['agent_hash'], 16), r['agent_hash'])
        r['script'] = scripts.get(int(r['script_hash'], 16), r['script_hash'])
        r['source_file'] = os.path.join('effect', r['agent_hash'] + '__' + r['script_hash'] + '.c')
        path = os.path.join(acmd, r['source_file'])
        r['commands'] = A.parse_body(open(path, encoding='utf-8').read(), nro, hashes, helpers)
        rows.append(r)
    return rows, body


def package_of(name, own):
    if not isinstance(name, str):
        return None
    try:
        return own.get(int(name, 16), (None, None))[1]
    except ValueError:
        return next((package for resolved, package in own.values() if resolved == name), None)


def call_from_command(c, own, joint_of, scale):
    args = c['args']
    needed = 8 if c['cmd'] == 'EFFECT_GLOBAL' else 9
    if len(args) < needed:
        raise ValueError(f"{c['cmd']} arguments are incomplete: {args!r}")
    pkg = package_of(args[0], own)
    global_effect = c['cmd'] == 'EFFECT_GLOBAL'
    bone = 'top' if global_effect else str(args[1]).lower()
    xyz = args[1:4] if global_effect else args[2:5]
    rot = args[4:7] if global_effect else args[5:8]
    size = args[7] if global_effect else args[8]
    if not all(isinstance(v, (int, float)) for v in xyz + rot + [size]):
        raise ValueError(f"{c['cmd']} arguments are unresolved: {args!r}")
    return {'frame': c['frame'], 'macro': c['cmd'], 'effect': args[0], 'package': pkg,
            'bone': bone, 'joint': joint_of.get(bone),
            'offset': [round(v * scale, 6) for v in xyz], 'rotation': rot,
            'scale': size, 'follow': c['cmd'] in {'EFFECT_FOLLOW', 'EFFECT_FOLLOW_ALPHA',
                                                   'EFFECT_FOLLOW_NO_STOP', 'EFFECT_FLW_POS'},
            'when': c.get('when', []),
            'end_event': ('owner_destroy' if c['cmd'] == 'EFFECT_FOLLOW_NO_STOP' else
                          'state_exit' if 'FOLLOW' in c['cmd'] or c['cmd'] == 'EFFECT_FLW_POS'
                          else 'emitter_life')}


def decorate_ends(commands, calls):
    consumed = set()
    for call in calls:
        start = call.pop('_command_index')
        for c in commands[start + 1:]:
            if c['cmd'] in END_CMDS and c['frame'] >= call['frame'] and c['args'] and c['args'][0] == call['effect']:
                call['end_frame'] = c['frame']
                call['end_event'] = 'off' if c['cmd'] == 'EFFECT_OFF_KIND' else 'detach'
                consumed.add(id(c))
                break
    return consumed


def census(rows, own, joint_of, scale, *, allowlist=None):
    scripts, common, after, losses = [], Counter(), [], []
    for r in rows:
        guard = LossGuard(f"{r['agent']}/{r['script']}", allowlist)
        calls, end_calls, modifiers = [], [], []
        for command_index, c in enumerate(r['commands']):
            if c['cmd'] in EFFECT_CMDS:
                try:
                    call = call_from_command(c, own, joint_of, scale)
                except ValueError as exc:
                    raise ValueError(f"{r['script']} frame {c['frame']:g}: {exc}") from exc
                needed = 8 if c['cmd'] == 'EFFECT_GLOBAL' else 9
                if len(c['args']) > needed:
                    guard.omit(c['frame'], 'case', c['cmd'] + '.extra_args',
                               f"{c['cmd']} trailing arguments {c['args'][needed:]!r}")
                if c.get('when'):
                    guard.omit(c['frame'], 'case', c['cmd'] + '.branch',
                               f"conditional effect {c['cmd']} branch {c['when']!r}")
                if call['joint'] is None:
                    guard.omit(c['frame'], 'case', 'effect.bone.unmapped:' + call['bone'],
                               f"effect bone {call['bone']!r} has no converted skeleton joint; use top")
                    call['joint'] = joint_of['top']
                    call['bone'] = 'top'
                if not call['package']:
                    guard.omit(c['frame'], 'case', 'effect.common:' + str(call['effect']),
                               f"effect {call['effect']!r} has no converted package")
                    common[str(call['effect'])] += 1
                call['_command_index'] = command_index
                call['source'] = [r['source_file'], command_index]
                calls.append(call)
            elif c['cmd'] in END_CMDS:
                if len(c['args']) != 1:
                    guard.omit(c['frame'], 'case', c['cmd'] + '.extra_args',
                               f"{c['cmd']} arguments {c['args']!r}")
                end_calls.append({'frame': c['frame'], 'macro': c['cmd'],
                                  'effect': c['args'][0] if c['args'] else None,
                                  'args': c['args'], 'when': c.get('when', [])})
            elif c['cmd'].startswith('LAST_EFFECT_'):
                guard.omit(c['frame'], 'command', c['cmd'],
                           f"effect modifier {c['cmd']} arguments {c.get('args')!r}")
                modifiers.append({'frame': c['frame'], 'macro': c['cmd'],
                                  'args': c['args'], 'when': c.get('when', [])})
            elif c['cmd'].startswith('AFTER_IMAGE'):
                guard.omit(c['frame'], 'command', c['cmd'],
                           f"sword trail {c['cmd']} arguments {c.get('args')!r}")
                a = c['args']
                after.append({'agent': r['agent'], 'script': r['script'], 'frame': c['frame'],
                              'macro': c['cmd'], 'source_file': r['source_file'], 'parameters': a,
                              'texture': a[:2] if 'ON' in c['cmd'] else [],
                              'length': a[2] if 'ON' in c['cmd'] and len(a) > 2 else None,
                              'bones': [a[i] for i in (3, 7) if 'ON' in c['cmd'] and len(a) > i],
                              'blade_points': [a[4:7], a[8:11]] if 'ON' in c['cmd'] else [],
                              'color': 'texture-derived' if 'ON' in c['cmd'] else None,
                              'tail_parameters': a[-2:] if 'ON' in c['cmd'] else []})
            elif c['cmd'] in ('frame', 'wait'):
                if (c.get('unresolved_frame') or len(c.get('args', [])) != 1 or
                        not isinstance(c['args'][0], (int, float))):
                    raise ValueError(f"{r['script']} frame {c['frame']:g}: {c['cmd']} timing unresolved")
            else:
                guard.omit(c['frame'], 'command', c['cmd'],
                           f"effect command {c['cmd']} arguments {c.get('args')!r}")
        consumed_ends = decorate_ends(r['commands'], calls)
        for c in r['commands']:
            if c['cmd'] in END_CMDS and id(c) not in consumed_ends:
                guard.omit(c['frame'], 'case', c['cmd'] + '.unmatched',
                           f"{c['cmd']} has no matching converted effect call")
        scripts.append({'agent': r['agent'], 'script': r['script'], 'source_file': r['source_file'],
                        'share': r['share'], 'owner': r['owner'], 'calls': calls,
                        'end_calls': end_calls, 'modifiers': modifiers})
        losses.extend(guard.losses)
    return scripts, dict(sorted(common.items())), after, losses


def magic_states(scripts):
    """One bound state per cast part (trail_magic_geno.CAST): each plays its real clip on a common row
    and its script counts clip frames, so the effect script's own frames apply on the animation clock."""
    by_script = {r['script']: r for r in scripts if r['agent'] == 'trail' and
                 r['owner'] == 'fighter' and not r['share']}
    states = []
    for state, row, _clip, _suffix, _air in M.CAST:
        script = cast_script(state)
        if script not in by_script:
            continue
        calls = [c for c in by_script[script]['calls'] if c['package']]
        if calls:
            states.append({'state': state, 'subaction': row, 'clock': 'animation',
                           'script': script, 'calls': calls})
    return states


# A Geno state ends on the tick its script reaches its length, and the effects are driven after that
# tick under the NEW state, so an ACMD call at the last frame (the cast's FireShot at 18 of
# specialn1start, the search's SonicTurn at 9) is never seen by its own state. In Ultimate that frame
# is the moment the next motion starts; the call moves to frame 0 of each state that can follow.
HANDOFF = {'Firaga': ('FiragaFire',), 'FiragaAir': ('FiragaFireAir',),
           'SSearch': ('SStart2', 'STurnUp', 'STurnDown')}


def state_lengths():
    """Script length in clip frames of the states whose effects can reach it (generators' own numbers)."""
    import trail_specials_geno as T
    lengths = {state: M.CLIP_FRAMES[clip] for state, _row, clip, _suffix, _air in M.CAST}
    for state in ('SStart', 'SDash1', 'SDash2', 'SDash3'):
        lengths[state] = T.clip_info(T.CLIPS[state])[0]
    lengths['SSearch'] = int(T.params()['param_special_s']['search_frame'])
    return lengths


def carry_past_end(states, by_script, lengths, rows):
    """Move calls at or after their state's last frame onto the successors (HANDOFF) at frame - length.

    A carried call also takes the end its successor's script gives the same effect (the cast's FireShot is
    detached at 13 of specialn1). A state with such calls and no successor is an error."""
    by_name = {s['state']: s for s in states}
    for state in list(states):
        length = lengths.get(state['state'])
        if length is None:
            continue
        past = [c for c in state['calls'] if c['frame'] >= length]
        if not past:
            continue
        targets = HANDOFF.get(state['state'], ())
        if not targets:
            raise ValueError(f"{state['state']}: effect calls at frame >= {length} never play: "
                             + ', '.join(f"{c['package']}@{c['frame']:g}" for c in past))
        state['calls'] = [c for c in state['calls'] if c['frame'] < length]
        for name in targets:
            target = by_name.get(name)
            if target is None:
                target = {'state': name, 'subaction': rows[name], 'clock': 'animation', 'script': '', 'calls': []}
                states.append(target)
                by_name[name] = target
            ends = by_script.get(re.split('[/+]', target['script'])[0], {}).get('end_calls', [])
            for c in past:
                moved = dict(c, frame=round(c['frame'] - length, 6))
                moved.pop('end_frame', None)
                if 'end_frame' in c:
                    moved['end_frame'] = round(c['end_frame'] - length, 6)
                for e in ends:
                    if e['effect'] == c['effect'] and e['frame'] >= moved['frame'] and 'end_frame' not in moved:
                        moved['end_frame'] = e['frame']
                        moved['end_event'] = 'off' if e['macro'] == 'EFFECT_OFF_KIND' else 'detach'
                target['calls'].append(moved)
            source = re.split('[/+]', state['script'])[0]
            target['script'] = target['script'] + '+' + source if target['script'] else source
            target['calls'].sort(key=lambda x: x['frame'])
    states[:] = [st for st in states if st['calls']]
    return states


def bind(scripts, host_ir, host, packages, acmd=None, lengths=None):
    by_script = {r['script']: r for r in scripts if r['agent'] == 'trail' and r['owner'] == 'fighter'
                 and not r['share']}
    states = []
    overlaid_subactions = set(HOSTS[host].values()) | set(M.CAST_ROW.values())
    for s in host_ir['behavior']['subactions']:
        if s['index']['value'] in overlaid_subactions:
            continue  # Geno's Sora state replaces this host row.
        game_script = F.ROWS.get(s['name'])
        direct = 'effect_' + s['name'].lower()
        variants = (direct, direct[:-1]) if s['name'].endswith('HiS') or s['name'].endswith('LwS') else (direct,)
        script = next((x for x in variants if x in by_script),
                      'effect_' + game_script[5:] if game_script else None)
        if script not in by_script:
            continue
        calls = [c for c in by_script[script]['calls'] if c['package']]
        if calls:
            states.append({'state': s['name'], 'subaction': s['index']['value'], 'clock': 'animation',
                           'script': script, 'calls': calls})
    for state, script in SPECIAL.items():
        if script not in by_script:
            continue
        calls = [c for c in by_script[script]['calls'] if c['package']]
        twin = air_twin(script)
        if state in SHARED_AIR and twin in by_script:
            # One Geno state serves ground and air. The air script may differ (Ultimate's air start
            # raises SonicStart by one unit); each call fires only in its own situation.
            calls = ([dict(c, situation='ground') for c in calls] +
                     [dict(c, situation='air') for c in by_script[twin]['calls'] if c['package']])
            script += '/' + twin
        if calls:
            states.append({'state': state, 'subaction': HOSTS[host][state], 'clock': 'animation',
                           'script': script, 'calls': calls})
    states += magic_states(scripts)
    rows = dict(HOSTS[host], **M.CAST_ROW)
    carry_past_end(states, by_script, state_lengths() if lengths is None else lengths, rows)
    missing = sorted({c['package'] for s in states for c in s['calls']} - packages)
    if missing:
        raise ValueError('binding refers to missing packages: ' + ', '.join(missing))
    unknown_bones = sorted({c['bone'] for s in states for c in s['calls'] if c['joint'] is None})
    if unknown_bones:
        raise ValueError('unmapped bones: ' + ', '.join(unknown_bones))
    return {'geno_fx_bindings': 1, 'fighter': 'trail', 'host': host, 'unit_scale': 1.0,
            'states': states}


def audit_unbound(scripts, bindings, *, allowlist=None):
    """An own effect in the census must reach at least one installed state."""
    bound = {tuple(c['source']) for state in bindings['states'] for c in state['calls']}
    losses = []
    for script in scripts:
        guard = LossGuard(f"{script['agent']}/{script['script']}", allowlist)
        for call in script['calls']:
            if call['package'] and tuple(call['source']) not in bound:
                guard.omit(call['frame'], 'case', 'effect.unbound:' + script['script'],
                           f"effect {call['effect']!r} is not bound to an installed state")
        losses.extend(guard.losses)
    return losses


def check_against_geno(bindings, fighter):
    """Every bound state must point at a row the generated profile really has.

    `fighter` is a geno.json fighter entry (its `states` carry name + subaction). A bound state named
    like a Geno state must use that state's row; any other bound state is a host row and must not be one
    the profile's states replace (the host's row would then play Sora's clip under another fighter's
    effects). Raises ValueError listing every mismatch."""
    geno = {s['name']: s['subaction'] for s in fighter.get('states', [])}
    rows = {v: k for k, v in geno.items()}
    problems = []
    for st in bindings['states']:
        if st['state'] in geno:
            if geno[st['state']] != st['subaction']:
                problems.append(f"{st['state']}: bound to row {st['subaction']}, the profile has row {geno[st['state']]}")
        elif st['subaction'] in rows:
            problems.append(f"{st['state']}: host row {st['subaction']} is the profile's state {rows[st['subaction']]}")
    if problems:
        raise ValueError('bindings do not match the generated profile: ' + '; '.join(problems))


def unbound_geno_states(bindings, fighter):
    """Profile states with no effect binding (informational: some have no ACMD effect script)."""
    bound = {s['subaction'] for s in bindings['states']}
    return [s['name'] for s in fighter.get('states', []) if s['subaction'] not in bound]


# trail_magic_geno.py --fx gives each article variant its package by this name; a mod installed without
# that flag has no article effects, so attach_to fills them in (never overriding one that is set).
ARTICLE_FX = {'Fire': 'P_TrailFireBullet', 'Ice': 'P_TrailIceBullet', 'Bolt': 'P_TrailThunderBullet',
              'Cloud': 'P_TrailThunderCloud'}


def article_package(name):
    return ARTICLE_FX.get(name.replace('Air', '').replace('Last', ''))


def attach_to(mod_dir, packages_dir, bindings, *, attach=None, articles=True):
    """Put the effects into an installed Geno mod: fx/<pkg>/<pkg>.gfx.json with the textures and meshes
    that package names, fx/fx_bindings.json, and the fighter entry's "fx_bindings" key (geno.md 20.3).

    install_ultimate.py does not touch fx/, so this is the step that makes fighter-bound effects play.
    `attach` selects the fighter entry by its `attach` file (the only entry when omitted). Articles
    without an `fx` get their package. Returns a summary dict."""
    geno_path = os.path.join(mod_dir, 'geno.json')
    doc = json.load(open(geno_path, encoding='utf-8'))
    fighters = [f for f in doc.get('fighters', []) if attach is None or f.get('attach') == attach]
    if len(fighters) != 1:
        raise ValueError(f'{geno_path}: {len(fighters)} fighter entries match attach={attach!r}; pass attach')
    fighter = fighters[0]
    check_against_geno(bindings, fighter)
    names = sorted(f[:-9] for f in os.listdir(packages_dir) if f.endswith('.gfx.json'))
    fx = os.path.join(mod_dir, 'fx')
    for name in names:
        package = json.load(open(os.path.join(packages_dir, name + '.gfx.json'), encoding='utf-8'))
        dest = os.path.join(fx, name)
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        os.makedirs(dest)
        shutil.copyfile(os.path.join(packages_dir, name + '.gfx.json'), os.path.join(dest, name + '.gfx.json'))
        for asset in package.get('textures', []) + package.get('meshes', []):
            target = os.path.join(dest, asset['file'])
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(os.path.join(packages_dir, asset['file']), target)
    missing = sorted({c['package'] for s in bindings['states'] for c in s['calls']} - set(names))
    if missing:
        raise ValueError('bindings name packages that are not in ' + packages_dir + ': ' + ', '.join(missing))
    json.dump(bindings, open(os.path.join(fx, 'fx_bindings.json'), 'w', encoding='utf-8'), indent=1)
    fighter['fx_bindings'] = 'fx/fx_bindings.json'
    filled = []
    if articles:
        for art in fighter.get('articles', []):
            pkg = article_package(art.get('name', ''))
            if pkg and not art.get('fx'):
                if pkg not in names:
                    raise ValueError(f"article {art['name']} needs package {pkg}")
                art['fx'] = pkg
                filled.append(art['name'])
    json.dump(doc, open(geno_path, 'w', encoding='utf-8'), indent=1)
    return {'packages': len(names), 'bound_states': len(bindings['states']), 'articles_filled': filled}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dump', default=os.path.join(ROOT, '_build', 'ultimate-vfx', 'ef_trail'))
    ap.add_argument('--acmd', default=os.path.join(os.environ.get("GW_GHIDRA_PROJECTS", str(Path.home() / "ghidra-projects")), 'sora_acmd'))
    ap.add_argument('--host', choices=sorted(HOSTS), default='marth')
    ap.add_argument('--packages', default=os.path.join(ROOT, '_build', 'tmp', 'codex-fx', 'trail'))
    ap.add_argument('-o', '--out', default=os.path.join(ROOT, '_build', 'tmp', 'codex-fx'))
    ap.add_argument('--geno', help="the generated profile's geno.json (staged-specials or an installed mod's): "
                    "fail unless every bound state points at a row it really has")
    ap.add_argument('--attach-to', metavar='MOD_DIR', help="an installed mod (install_ultimate.py --out): copy the "
                    "packages into its fx/, write fx/fx_bindings.json and set the fighter's fx_bindings key "
                    "(and the articles' fx); checks the bindings against that mod's geno.json")
    ap.add_argument('--attach-name', help="with --attach-to: the fighter entry's `attach` file (PlUs.dat)")
    a = ap.parse_args()
    sets, own = own_names(a.dump)
    rows, body = parsed_rows(a.acmd, own)
    plan = plan_parts.plan(body)
    joint_of = {j['name'].lower(): i for i, j in enumerate(plan['joints'])}
    joint_of['top'] = 0
    scripts, common, after, census_losses = census(rows, own, joint_of, 1.0)
    host_ir = json.load(open(os.path.join(INSTANCES, a.host + '.melee.ir.json'), encoding='utf-8'))
    packages = {f[:-9] for f in os.listdir(a.packages) if f.endswith('.gfx.json')}
    bindings = bind(scripts, host_ir, a.host, packages, a.acmd)
    if a.geno:
        fighters = json.load(open(a.geno, encoding='utf-8'))['fighters']
        fighter = next(f for f in fighters if a.attach_name in (None, f.get('attach')))
        check_against_geno(bindings, fighter)
        print('profile states with no effect script:', ', '.join(unbound_geno_states(bindings, fighter)))
    unbound_losses = audit_unbound(scripts, bindings)
    os.makedirs(a.out, exist_ok=True)
    write_losses(os.path.join(a.out, 'conversion_losses.json'),
                 {'losses': census_losses}, {'losses': unbound_losses})
    json.dump({'sets': sets, 'scripts': scripts, 'common_effects': common, 'after_images': after},
              open(os.path.join(a.out, 'effect_census.json'), 'w'), indent=1)
    json.dump(bindings, open(os.path.join(a.packages, 'fx_bindings.json'), 'w'), indent=1)
    print(f'{len(sets)} sets; {len(scripts)} effect scripts; {len(bindings["states"])} bound states; '
          f'{sum(len(s["calls"]) for s in bindings["states"])} own calls; '
          f'{sum(common.values())} common calls; {len(after)} after-image commands')
    if a.attach_to:
        print('attached:', attach_to(a.attach_to, a.packages, bindings, attach=a.attach_name))


if __name__ == '__main__':
    main()
