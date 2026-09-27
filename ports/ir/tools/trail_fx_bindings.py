#!/usr/bin/env python3
"""Census Ultimate ACMD effects and bind trail's own packages to Melee subactions.

The output is derived game data: keep it under _build/, beside the imported .gfx.json files.
ACMD is parsed from the local Ghidra C with acmd_parse, using the same joint table and
unit scale as acmd_to_ftcmd. Common effects and sword trails remain census-only.
"""
import argparse
from collections import Counter
import json
import os
import re

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

# The special-state names and subaction numbers are the same ones installed by
# trail_specials_geno.py. Repeated scripts intentionally bind to each dash state.
SPECIAL = {
    'SStart': 'effect_specialsstart', 'SStart2': 'effect_specialssearch',
    'SDash1': 'effect_specials1', 'SDash2': 'effect_specials2',
    'SDash3': 'effect_specials2', 'SEnd': 'effect_specials3',
    'SEndAir': 'effect_specialairs3', 'Hi': 'effect_specialhi',
    'HiAir': 'effect_specialairhi', 'LwStart': 'effect_speciallwstart',
    'LwStartAir': 'effect_specialairlwstart', 'LwAttack': 'effect_speciallw',
    'LwAttackAir': 'effect_specialairlw', 'LwAttackBack': 'effect_speciallw',
    'LwAttackBackAir': 'effect_specialairlw', 'LwRebound': 'effect_speciallw',
    'LwReboundAir': 'effect_specialairlw',
}


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


def magic_states(scripts, acmd):
    """The magic Geno states play a stand-in clip, so their effects use game time.

    Follow trail_magic_geno's start/cast/end composition and its motion-rate map.
    Read the game scripts from the same Ghidra dump; effects still come from the
    effect scripts parsed above.
    """
    by_script = {r['script']: r for r in scripts if r['agent'] == 'trail' and
                 r['owner'] == 'fighter' and not r['share']}
    nro = A.Nro(os.path.join(TOOL, 'workspace', 'extracted', 'prebuilt', 'nro',
                            'release', 'lua2cpp_trail.nro'))
    helpers = A.helper_names(acmd)
    game = {}
    for air in (False, True):
        pre = 'game_specialairn' if air else 'game_specialn'
        for suffix in ('1start', '1', '1end', '2', '3'):
            name = pre + suffix
            path = os.path.join(acmd, 'game', f'{hex(A.hash40("trail"))}__{hex(A.hash40(name))}.c')
            if not os.path.exists(path):
                raise FileNotFoundError(path)
            game[name] = {'commands': A.parse_body(open(path, encoding='utf-8').read(), nro, {}, helpers)}
    states = []
    for air in (False, True):
        pre = 'specialairn' if air else 'specialn'
        game_pre = 'game_' + pre
        suffix = 'Air' if air else ''
        firaga_parts = [('1start', 0),
                        ('1', M.game_time(game[game_pre + '1start'])(18)),
                        ('1end', M.game_time(game[game_pre + '1start'])(18) +
                         M.game_time(game[game_pre + '1'])(15))]
        for state, parts in ((
                'Firaga' + suffix, firaga_parts),
                ('Blizzaga' + suffix, [('2', 0)]),
                ('Thundaga' + suffix, [('3', 0)])):
            calls = []
            names = []
            for part, shift in parts:
                effect_script = 'effect_' + pre + part
                if effect_script not in by_script:
                    continue
                names.append(effect_script)
                clock = M.game_time(game[game_pre + part])
                for src in by_script[effect_script]['calls']:
                    if not src['package']:
                        continue
                    call = dict(src)
                    call['frame'] = round(shift + clock(src['frame']), 6)
                    if 'end_frame' in call:
                        call['end_frame'] = round(shift + clock(call['end_frame']), 6)
                    calls.append(call)
            if calls:
                states.append({'state': state, 'subaction': M.SUB[state], 'clock': 'game',
                               'script': '/'.join(names), 'calls': sorted(calls, key=lambda x: x['frame'])})
    return states


def bind(scripts, host_ir, host, packages, acmd):
    by_script = {r['script']: r for r in scripts if r['agent'] == 'trail' and r['owner'] == 'fighter'
                 and not r['share']}
    states = []
    overlaid_subactions = set(HOSTS[host].values()) | set(M.SUB.values())
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
        if state == 'SStart' and 'effect_specialairsstart' in by_script:
            # One Geno state serves ground and air. Ultimate's air start raises
            # SonicStart by one unit; the later dash/search effects are identical.
            ground = [dict(c, situation='ground') for c in calls]
            air = [dict(c, situation='air') for c in
                   by_script['effect_specialairsstart']['calls'] if c['package']]
            calls = ground + air
            script += '/effect_specialairsstart'
        if calls:
            states.append({'state': state, 'subaction': HOSTS[host][state], 'clock': 'animation',
                           'script': script, 'calls': calls})
    states += magic_states(scripts, acmd)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dump', default=os.path.join(ROOT, '_build', 'ultimate-vfx', 'ef_trail'))
    ap.add_argument('--acmd', default=r'C:\Users\Gurek\ghidra-projects\sora_acmd')
    ap.add_argument('--host', choices=sorted(HOSTS), default='marth')
    ap.add_argument('--packages', default=os.path.join(ROOT, '_build', 'tmp', 'codex-fx', 'trail'))
    ap.add_argument('-o', '--out', default=os.path.join(ROOT, '_build', 'tmp', 'codex-fx'))
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


if __name__ == '__main__':
    main()
