#!/usr/bin/env python3
"""Reproducible native room certification harness for the roguelite recipes.

This tool inspects the UNCERTIFIED resolved recipes and prepares a bounded,
auditable native probe. It never sets ``recipe.certified`` and never admits a
recipe into the production runtime; the isolated certification mod resolves a
recipe directly (``RoomRecipes.resolve``) and the production adapter's
certification gate is left untouched.

Subcommands
-----------
``inspect``  resolve every template through the pure recipe modules and print
             machine-readable rows (no native process).
``plan``     build the per-template traversal plan and validate it against the
             inspected sockets and the roster.
``install``  bundle the isolated certification mod into an app directory. Only
             runs when ``--app-dir`` is given explicitly. It preserves the
             enabled-mod list (backed up once), user saves and the shared exe.
``restore``  put the original enabled-mod list back.
``run``      drive an already running native 60 Hz match over the console socket
             and write JSONL evidence plus a machine-readable summary. Native
             traversal is never auto-certified: the verdict is always
             ``pending-native-run`` or ``manual-review-required``.

Honest limits
-------------
* ``run`` needs a native build with a disc image and is driven by the
  coordinator. The pure tests only
  validate plans, parsing, refusal and state handling.
* ``run`` refuses turbo/uncapped timing, debug flight, a CPU-controlled port and
  any recipe already certified. Teleports are labelled fixtures for placement
  and inspection only; they are never traversal evidence.
* Screenshots and per-frame sequences are evidence artifacts, not a claim that
  a mandatory traversal succeeded.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
GAME = Path(os.environ.get('GW_MELEE') or (ROOT / 'melee/worktrees/linux')).resolve()
RT = GAME / 'pc/scripts/examples/roguelite'
CERT_SRC = GAME / 'pc/scripts/examples/roguelite_certification'
ROOM_KIT = ROOT / 'menu/out_roguelite/room-kit'
SHARED_APP = (ROOT / '_build/agents/linux').resolve()
MOD_ID = 'roguelite_certification'
BUNDLE_MODULES = (('room_catalogue', 'RoomCatalogue'), ('room_recipes', 'RoomRecipes'), ('rooms', 'Rooms'))
REQUIRED_KIT = (
    'bf_floor_2m', 'bf_floor_4m', 'bf_floor_end_trim', 'bf_floor_opening_4m',
    'bf_wall_solid_4m', 'bf_wall_doorway_4m', 'bf_wall_window_4m', 'bf_wall_side_return',
    'bf_beam_4m', 'bf_rear_post_4m', 'bf_rear_glass_rail_4m', 'bf_rear_glass_rail_4m_glass',
    'bf_corner_inside_4m', 'bf_corner_outside_4m', 'bf_door_leaf',
    'bf_stairs_4m_rise2m', 'bf_ramp_4m_rise2m', 'bf_ramp_4m_rise2m_glass',
    'bf_balcony_4m', 'bf_balcony_4m_glass', 'bf_window_glass_insert_glass',
)
REQUIRED_TEMPLATES = ('branch_y', 'rejoin_merge', 'junction_cross', 'shortcut_door')
SCHEMA = 'certify-rooms/1'

MOBILITY_PROFILES = (
    {'id': 'bowser', 'fighter': 'bowser', 'costume': 0, 'label': 'short/heavy large frame',
     'checks': ['large-feet drop clearance', 'landing/body clearance']},
    {'id': 'jigglypuff', 'fighter': 'jigglypuff', 'costume': 0, 'label': 'floaty',
     'checks': ['ascent without extra jump', 'return control']},
    {'id': 'falco', 'fighter': 'falco', 'costume': 0, 'label': 'fast-faller',
     'checks': ['ascent seam pop', 'underside clearance']},
    {'id': 'kirby', 'fighter': 'kirby', 'costume': 0, 'label': 'multiple-jump',
     'checks': ['alternate-return reach', 'recovery margin']},
)

# --- controller probe mini-language ------------------------------------------------
def walk(direction, frames): return ('walk', direction, frames)
def neutral(frames): return ('neutral', frames)
def button(name, frames): return ('button', name, frames)
def down(frames): return ('down', frames)


def _plan_specs():
    """Per-template required coverage. ``probes`` are proposed attempt programs."""
    return {
        'branch_y': {
            'segments': [
                {'id': 'ascent', 'kind': 'ascent', 'source': 'in', 'target': 'branch_b',
                 'natural': True, 'probes': [[walk(1, 240)], [walk(1, 120), button('A', 4), walk(1, 240)]],
                 'note': 'in -> stairs/balcony/ramp -> top door; holding right must climb without tech'},
                {'id': 'return', 'kind': 'return', 'source': 'branch_b', 'target': 'in',
                 'natural': True, 'probes': [[walk(-1, 240)], [walk(-1, 120), button('A', 4), walk(-1, 240)]],
                 'note': 'top door -> ground return; no seam pop or stuck state'},
                {'id': 'fork_branch_a', 'kind': 'fork', 'source': 'in', 'target': 'branch_a',
                 'natural': True, 'probes': [[walk(1, 150), button('A', 4), walk(1, 200)]],
                 'note': 'ground/right fork reachable from the entry without tech'},
                {'id': 'fork_branch_b', 'kind': 'fork', 'source': 'in', 'target': 'branch_b',
                 'natural': True, 'probes': [[walk(1, 260)], [walk(1, 140), button('A', 4), walk(1, 260)]],
                 'note': 'upper/top fork reachable from the entry without tech'},
            ],
        },
        'rejoin_merge': {
            'segments': [
                {'id': 'entry_left', 'kind': 'entry', 'source': 'in_a', 'target': 'out',
                 'natural': True, 'probes': [[walk(1, 260)]],
                 'note': 'left incoming arrival -> merge -> out; safe progression'},
                {'id': 'entry_top', 'kind': 'entry', 'source': 'in_b', 'target': 'out',
                 'natural': True, 'probes': [[walk(-1, 120)], [walk(1, 160), walk(1, 200)]],
                 'note': 'top incoming arrival -> merge -> out; descend and rejoin'},
            ],
        },
        'junction_cross': {
            'segments': [
                {'id': 'drop_through', 'kind': 'drop', 'source': None, 'target': None,
                 'fixture': {'x': 20, 'y': 0}, 'natural': True, 'requires_fall': True,
                 'probes': [[walk(-1, 90)], [down(30), neutral(30)]],
                 'note': 'walk over the real 13-unit floor opening and fall through to y=-6 trigger'},
                {'id': 'drop_one_way', 'kind': 'drop-one-way', 'source': None, 'target': None,
                 'fixture': {'x': 20, 'y': 0}, 'natural': True, 'requires_fall': True,
                 'forbid_climb_back': True,
                 'probes': [[walk(-1, 90), neutral(120)]],
                 'note': 'after falling, the fighter may not climb back onto the lane floor'},
                {'id': 'safe_incoming_bottom', 'kind': 'safe-arrival', 'source': 'branch_b', 'target': 'out',
                 'natural': True, 'probes': [[walk(1, 200)]],
                 'note': 'incoming bottom arrival (20,0) is solid and outside the hole; walk to out'},
                {'id': 'alternate_return', 'kind': 'alternate-return', 'source': 'branch_b', 'target': 'branch_a',
                 'natural': True, 'probes': [[walk(-1, 240)], [walk(-1, 120), button('A', 4), walk(-1, 240)]],
                 'note': 'after a bottom arrival, use the ascent to reach the top branch (graph return)'},
            ],
        },
        'shortcut_door': {
            'segments': [
                {'id': 'drop_through', 'kind': 'drop', 'source': None, 'target': None,
                 'fixture': {'x': 20, 'y': 0}, 'natural': True, 'requires_fall': True,
                 'probes': [[walk(-1, 90)], [down(30), neutral(30)]],
                 'note': 'same drop/landing coverage as junction_cross without ascent'},
                {'id': 'safe_incoming_bottom', 'kind': 'safe-arrival', 'source': 'shortcut', 'target': 'out',
                 'natural': True, 'probes': [[walk(1, 200)]],
                 'note': 'incoming bottom arrival is solid and safe'},
            ],
        },
    }


def _segment(template, spec, sockets):
    """Resolve socket sides/anchors into a concrete segment record."""
    def sock(name):
        if name is None:
            return None
        entry = sockets.get(name)
        if not entry:
            raise ValueError('%s: no such socket %r' % (template, name))
        return entry
    source = sock(spec.get('source'))
    target = sock(spec.get('target'))
    return {
        'id': spec['id'], 'kind': spec['kind'], 'natural': spec.get('natural', True),
        'source': spec.get('source'), 'source_side': source and source['side'],
        'target': spec.get('target'), 'target_side': target and target['side'],
        'fixture': spec.get('fixture'), 'requires_fall': spec.get('requires_fall', False),
        'forbid_climb_back': spec.get('forbid_climb_back', False),
        'probes': spec.get('probes', []), 'note': spec.get('note', ''),
        'status': 'proposed-needs-native-validation',
    }


def build_plan(template, recipe_info):
    """Return the plan for one template, validated against inspected sockets."""
    specs = _plan_specs().get(template)
    if not specs:
        return None, 'no certification plan for template ' + template
    sockets = {row['socket']: row for row in recipe_info.get('sockets', [])}
    if not sockets:
        return None, template + ': no resolved sockets'
    segments = [_segment(template, spec, sockets) for spec in specs['segments']]
    return {
        'template': template,
        'recipe': recipe_info.get('recipe'),
        'recipe_version': recipe_info.get('version'),
        'certified': recipe_info.get('certified', False),
        'mobility_contract': recipe_info.get('mobility'),
        'sockets': recipe_info.get('sockets', []),
        'openings': recipe_info.get('openings', []),
        'segments': segments,
        'mobility_profiles': [dict(p) for p in MOBILITY_PROFILES],
        'status': 'proposed-needs-native-validation',
    }, None


def build_plans(recipes, templates=None):
    """Build and validate plans for the requested templates."""
    templates = templates or list(REQUIRED_TEMPLATES)
    by_template = {row['template']: row for row in recipes.get('recipes', [])}
    if not recipes.get('available', False):
        return [], [recipes.get('reason', 'recipe inspection unavailable')]
    plans, errors = [], []
    for template in templates:
        info = by_template.get(template)
        if not info:
            errors.append(template + ': not in the room catalogue')
            continue
        plan, why = build_plan(template, info)
        if not plan:
            errors.append(why)
        else:
            plans.append(plan)
    return plans, errors


# --- parsing -----------------------------------------------------------------------
ANSI = re.compile(r'\x1b\[[0-9;]*m')
NUMBER = re.compile(r'^-?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$', re.I)


def _value(raw):
    if raw in ('true', 'false', 'nil'):
        return {'true': True, 'false': False, 'nil': None}[raw]
    if NUMBER.match(raw):
        value = float(raw)
        if math.isfinite(value):
            return value
    return raw


def parse_rows(output, prefix):
    """Parse ``prefix key=value ...`` rows from console output."""
    text = ANSI.sub('', output)
    rows = []
    for match in re.finditer(r'\b' + re.escape(prefix) + r'\s+([^\n]+)', text):
        row = {}
        for key, raw in re.findall(r'(\w+)=([^\s]+)', match.group(1)):
            row[key] = _value(raw)
        if row:
            rows.append(row)
    return rows


def parse_scalar(output):
    """Return the last scalar line (number/bool/nil) from console output."""
    for line in reversed(ANSI.sub('', output).splitlines()):
        value = line.strip()
        if value in ('true', 'false', 'nil'):
            return _value(value)
        if NUMBER.match(value):
            number = float(value)
            if math.isfinite(number):
                return number
    raise ValueError('missing scalar console result: ' + output)


# --- pure recipe inspection through the game's Lua --------------------------------
LUA_INSPECT = r'''
local Catalogue=dofile(arg[1]); local Recipes=dofile(arg[2])
local ids={} for id in pairs(Catalogue.rooms) do ids[#ids+1]=id end table.sort(ids)
for _,id in ipairs(ids) do
  local t=Catalogue.rooms[id]
  local g,r=Recipes.resolve(t)
  if not g then
    print('certify_recipe template='..id..' resolved=false reason='..tostring(r))
  else
    print(string.format('certify_recipe template=%s recipe=%s version=%s certified=%s mobility=%s modules=%d platforms=%d lines=%d openings=%d floor_left=%s floor_right=%s',
      id, t.recipe, tostring(r.version), tostring(r.certified), tostring(r.mobility_contract),
      #(r.modules or {}), #g.platforms, #g.lines, #(g.floor.openings or {}),
      tostring(g.floor.left), tostring(g.floor.right)))
    for _,s in ipairs(t.sockets) do
      local a=g.exit_anchors[s.side] or {}; local ar=(g.arrivals or {})[s.side] or {}
      print(string.format('certify_socket template=%s socket=%s side=%s ax=%s ay=%s drop=%s rx=%s ry=%s facing=%s',
        id, s.id, s.side, tostring(a.x), tostring(a.y), tostring(a.drop),
        tostring(ar.x), tostring(ar.y), tostring(ar.facing)))
    end
    for i,o in ipairs(g.floor.openings or {}) do
      print(string.format('certify_opening template=%s index=%d x=%s width=%s', id, i, tostring(o.x), tostring(o.width)))
    end
  end
end
'''


def lua_interpreter():
    return shutil.which('lua5.4') or shutil.which('lua')


def inspect_recipes(game_root=GAME, lua=None, timeout=30):
    """Resolve every template purely; returns rows plus availability info."""
    rt = Path(game_root) / 'pc/scripts/examples/roguelite'
    modules = [rt / 'room_catalogue.lua', rt / 'room_recipes.lua']
    missing = [str(m) for m in modules if not m.is_file()]
    if missing:
        return {'available': False, 'reason': 'recipe modules missing: ' + ', '.join(missing),
                'recipes': [], 'sockets': {}, 'openings': {}}
    lua = lua or lua_interpreter()
    if not lua:
        return {'available': False, 'reason': 'no lua interpreter (lua5.4/lua) on PATH',
                'recipes': [], 'sockets': {}, 'openings': {}}
    result = subprocess.run([lua, '-', str(modules[0]), str(modules[1])], input=LUA_INSPECT,
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        return {'available': False, 'reason': 'lua inspection failed: ' + result.stderr.strip(),
                'recipes': [], 'sockets': {}, 'openings': {}}
    recipes, sockets, openings = {}, {}, {}
    for row in parse_rows(result.stdout, 'certify_recipe'):
        row['resolved'] = row.get('resolved', 'true') is not False
        row['sockets'] = []
        recipes[row['template']] = row
    for row in parse_rows(result.stdout, 'certify_socket'):
        sockets.setdefault(row['template'], []).append(row)
    for row in parse_rows(result.stdout, 'certify_opening'):
        openings.setdefault(row['template'], []).append(row)
    for template, row in recipes.items():
        row['sockets'] = sorted(sockets.get(template, []), key=lambda r: r['socket'])
        row['openings'] = sorted(openings.get(template, []), key=lambda r: r.get('index', 0))
    order = sorted(recipes)
    return {'available': True, 'reason': None, 'recipes': [recipes[t] for t in order],
            'sockets': sockets, 'openings': openings, 'lua': lua, 'game_root': str(game_root)}


# --- install / restore -------------------------------------------------------------
def bundle_text(cert_src=CERT_SRC):
    """Prepend the pure modules as locals, exactly like prepare.py, then main.lua."""
    chunks = []
    for name, local in BUNDLE_MODULES:
        chunks.append('local %s = (function()\n%s\nend)()\n' % (local, (RT / (name + '.lua')).read_text()))
    chunks.append((Path(cert_src) / 'main.lua').read_text())
    return '\n'.join(chunks)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(65536), b''):
            digest.update(block)
    return digest.hexdigest()


def install(app_dir, *, enable=True, cert_src=CERT_SRC, room_kit=ROOM_KIT, allow_shared=False):
    """Install the isolated certification mod. Never touches saves or the exe."""
    app = Path(app_dir).resolve()
    if not app.exists():
        raise FileNotFoundError('app dir does not exist: ' + str(app))
    if app == SHARED_APP and not allow_shared:
        raise ValueError('refusing to install into the shared review app dir; choose an isolated '
                         '--app-dir or pass --allow-shared')
    mods = app / 'mods'
    mods.mkdir(parents=True, exist_ok=True)
    script = bundle_text(cert_src)
    mod = mods / MOD_ID
    (mod / 'scripts').mkdir(parents=True, exist_ok=True)
    (mod / 'scripts/main.lua').write_text(script)
    (mod / 'mod.json').write_text(json.dumps({
        'id': MOD_ID, 'name': 'Roguelite room certification', 'version': '0.1.0',
        'author': "GD's Melee", 'kind': 'script', 'api_version': 1, 'gameplay': True,
        'rollback_safe': False, 'entry': 'scripts/main.lua',
        'description': 'Isolated probe that resolves uncertified room recipes; never certifies them.',
    }, indent=2) + '\n')
    models = mod / 'models'
    models.mkdir(exist_ok=True)
    if not Path(room_kit).is_dir():
        raise FileNotFoundError('BF room kit not found: ' + str(room_kit))
    names = [name + suffix for name in REQUIRED_KIT for suffix in ('.gxmesh', '.coll.json')]
    names += ['bf_kit.gxtex', 'bf_kit.glow.gxtex', 'bf_kit_glass.gxtex', 'bf_kit_glass.glow.gxtex']
    missing = [name for name in names if not (Path(room_kit) / name).is_file()]
    if missing:
        raise FileNotFoundError('BF room kit incomplete: ' + ', '.join(missing))
    for name in names:
        shutil.copyfile(Path(room_kit) / name, models / name)
    enabled, backup = mods / 'enabled.txt', mods / (MOD_ID + '-enabled.backup')
    if enable:
        if not backup.exists():
            backup.write_text(enabled.read_text() if enabled.exists() else '')
        enabled.write_text(MOD_ID + '\n')
    return {
        'app_dir': str(app), 'mod_dir': str(mod), 'bundle_sha256': hashlib.sha256(script.encode()).hexdigest(),
        'models': len(names), 'enabled_backup': str(backup),
        'enabled_written': MOD_ID if enable else None,
    }


def restore(app_dir):
    app = Path(app_dir).resolve()
    mods = app / 'mods'
    enabled, backup = mods / 'enabled.txt', mods / (MOD_ID + '-enabled.backup')
    if not backup.exists():
        return {'restored': False, 'reason': 'no enabled-list backup at ' + str(backup)}
    shutil.copyfile(backup, enabled)
    return {'restored': True, 'enabled': str(enabled), 'from': str(backup)}


# --- native driver -----------------------------------------------------------------
def classify_trace(result, trace, *, floor_y, target=None, requires_fall=False,
                   forbid_climb_back=False,
                   arrival_tolerance=10.0, height_tolerance=6.0, fall_margin=30.0,
                   stuck_frames=90, air_epsilon=0.05):
    """Pure classification of a bounded trace. Never implies certification."""
    samples = [dict(s) for s in trace]
    checks = {
        'sampled': len(samples),
        'truncated': bool(result.get('truncated')),
        'arrived': False,
        'fell': False,
        'climb_back': False,
        'stuck': False,
        'airborne_frames': sum(1 for s in samples if s.get('airborne')),
        'min_y': min((s['y'] for s in samples), default=None),
        'max_y': max((s['y'] for s in samples), default=None),
        'seam_pop_candidate': False,
        'manual_review': [],
    }
    if not samples:
        return {'status': 'no-samples', 'checks': checks,
                'manual_review': ['no per-frame samples observed']}
    # arrival: a grounded sample inside the socket's arrival window
    if target is not None:
        for s in samples:
            if (not s.get('airborne') and abs(s['x'] - target['x']) < arrival_tolerance
                    and abs(s['y'] - target['y']) < height_tolerance):
                checks['arrived'] = True
                break
    # falling: a sample well below the lane floor
    if requires_fall or checks['min_y'] is not None:
        checks['fell'] = checks['min_y'] is not None and checks['min_y'] < (floor_y - fall_margin)
    # one-way: after the fall, a grounded sample back at lane-floor height means a climb back
    if requires_fall and checks['fell']:
        for index, current in enumerate(samples):
            if current['y'] < floor_y - fall_margin:
                for later in samples[index + 1:]:
                    if not later.get('airborne') and later['y'] >= floor_y - 1:
                        checks['climb_back'] = True
                        break
                break
    # stuck: a long grounded run with no horizontal progress
    run, stuck = 0, False
    for previous, current in zip(samples, samples[1:]):
        if (not current.get('airborne') and abs(current['x'] - previous['x']) < air_epsilon):
            run += 1
            if run >= stuck_frames:
                stuck = True
        else:
            run = 0
    checks['stuck'] = stuck
    # a seam pop would be a grounded -> airborne transition with near-zero rise during
    # pure horizontal walking; record the candidate for human review, never an auto-pass
    for previous, current in zip(samples, samples[1:]):
        if not previous.get('airborne') and current.get('airborne') and current.get('vy', 0) <= 0:
            checks['seam_pop_candidate'] = True
            break
    if checks['seam_pop_candidate']:
        checks['manual_review'].append('grounded->airborne with non-positive vy: inspect for a seam pop')
    if checks['truncated']:
        checks['manual_review'].append('trace window was truncated; rerun with a longer window')
    if forbid_climb_back and checks['climb_back']:
        status = 'one-way-violated'
        checks['manual_review'].append('fighter returned to the lane floor after a drop')
    elif requires_fall and not checks['fell']:
        status = 'failed-no-fall'
    elif checks['fell']:
        status = 'fell'
    elif target is not None and checks['arrived']:
        status = 'arrived'
    elif checks['stuck']:
        status = 'stuck'
    else:
        status = 'inconclusive'
    return {'status': status, 'checks': checks, 'manual_review': checks['manual_review']}


def recipe_verdict(recipe, version, outcomes, *, native_run):
    """The verdict never claims certification. Manual review is always required."""
    passed = [o for o in outcomes if o.get('status') in ('arrived', 'fell')]
    failed = [o['id'] for o in outcomes if o.get('status') in ('failed-no-fall', 'stuck', 'one-way-violated')]
    inconclusive = [o['id'] for o in outcomes if o.get('status') == 'inconclusive']
    return {
        'schema': SCHEMA, 'recipe': recipe, 'recipe_version': version,
        'certified': False, 'auto_certification': 'forbidden',
        'verdict': 'manual-review-required' if native_run else 'pending-native-run',
        'native_run_performed': bool(native_run),
        'segments_total': len(outcomes), 'segments_with_observation': len(passed),
        'failed_segments': failed, 'inconclusive_segments': inconclusive,
        'requires_human_review': True,
        'note': ('A human/coordinator must review captures and observations. '
                 'A successful trace is not certification.'),
    }


class MissingAPI(Exception):
    pass


class UnsupportedRun(Exception):
    pass


class Console:
    """Injectable console boundary; tests need no socket or native process."""

    def __init__(self, command, *, sleep=time.sleep, clock=time.monotonic, note=None):
        self.cmd_raw, self.sleep, self.clock = command, sleep, clock
        self.note = note or (lambda record: None)
        self.commands = []

    def cmd(self, text, category='observation'):
        output = self.cmd_raw(text, category)
        self.commands.append({'command': text, 'category': category})
        return output

    def rows(self, prefix, output=None):
        return parse_rows(output if output is not None else self.cmd(prefix), prefix)

    def scalar(self, expression):
        return parse_scalar(self.cmd('= ' + expression))


class CertificationDriver:
    """Drives one running match. It never certifies and never owns a pad past cleanup."""

    def __init__(self, console, *, port=1, native_run=True, capture_dir=None,
                 capture_stride=30, sleep_frames=None):
        if port != 1:
            raise UnsupportedRun('certification replay owns port 1 only; got port %r' % (port,))
        self.c = console
        self.port = port
        self.native_run = native_run
        self.capture_dir = Path(capture_dir) if capture_dir else None
        self.capture_stride = capture_stride
        self.pad_owned = False
        self._sleep_frames = sleep_frames or (lambda frames: self.c.sleep(frames / 60.0 + 0.05))

    # -- prerequisites --------------------------------------------------------------
    def ensure_apis(self):
        rows = parse_rows(self.c.cmd('certify_apis', 'api_probe'), 'certify_api')
        missing = [r['name'] for r in rows if r.get('name') and r.get('present') is False]
        if missing:
            raise MissingAPI('missing native API: ' + ', '.join(missing))
        return rows

    def ensure_normal_speed(self, sample=True):
        if self.c.scalar('gd.perf().target') != 60:
            raise UnsupportedRun('certification requires a 60 Hz paced process (no uncapped/turbo)')
        if self.c.scalar('gd.paused()'):
            raise UnsupportedRun('certification requires a running simulation; call resume first')
        for port in (1, 2):
            if self.c.scalar('gd.fly(%d)' % port):
                raise UnsupportedRun('disable debug flight before a traversal probe')
        if sample:
            frame, start = self.c.scalar('gd.match().frame'), self.c.clock()
            self.c.sleep(0.5)
            end = self.c.scalar('gd.match().frame')
            rate = (end - frame) / max(1e-6, self.c.clock() - start)
            if not 0 < rate <= 75:
                raise UnsupportedRun('accelerated/stalled simulation: %.1f logic frames/s' % rate)
            self.c.note({'category': 'timing_observation', 'target': 60, 'logic_frames_per_second': rate})

    def launch_scene(self, fighter, costume=0, timeout=18):
        output = self.c.cmd('certify_scene %s %d' % (fighter, costume), 'native_scene')
        if 'ok=true' not in output:
            raise UnsupportedRun('scene launch refused: ' + output.strip())
        deadline = self.c.clock() + timeout
        # scene_launch queues a transition; fighter pointers can still refer to
        # the retiring scene. Require a stable active match after the queue has
        # had a logic tick to run before building collision into the new scene.
        stable = 0
        while self.c.clock() < deadline:
            self.c.sleep(0.25)
            state = self.c.cmd('certify_status', 'poll')
            if parse_rows(state, 'certify_status') and self.c.scalar('gd.match().active'):
                p1 = self.c.scalar('gd.player(1) ~= nil')
                p2 = self.c.scalar('gd.player(2) ~= nil')
                if p1 and p2:
                    if self.c.scalar('gd.player(1).cpu'):
                        raise UnsupportedRun('port 1 is CPU-controlled; certification must drive a human port')
                    stable += 1
                    if stable >= 2:
                        # Geometry probes need an idle opponent, not combat
                        # interference. This does not alter player physics.
                        self.c.cmd("gd.cpu_mode(2, 'stand')", 'fixture_opponent')
                        return True
                    continue
            stable = 0
        raise UnsupportedRun('certification match did not become ready')

    # -- recipe lifecycle -----------------------------------------------------------
    def build(self, template, timeout=30):
        output = self.c.cmd('certify_build ' + template, 'native_build')
        if 'certify_missing_api' in output and 'certify_build_start' not in output:
            names = [r['name'] for r in parse_rows(output, 'certify_missing_api')]
            raise MissingAPI('missing native API: ' + ', '.join(names))
        if 'certify_error' in output and 'certify_build_start' not in output:
            raise UnsupportedRun('build refused: ' + output.strip())
        deadline = self.c.clock() + timeout
        while self.c.clock() < deadline:
            status = self.c.cmd('certify_status')
            rows = parse_rows(status, 'certify_status')
            if rows:
                phase = rows[-1].get('phase')
                if phase == 'ready':
                    self.c.note({'category': 'native_build', 'template': template, 'template_rows': rows[-1]})
                    return rows[-1]
                if phase == 'error':
                    raise UnsupportedRun('build failed in phase error: ' + str(rows[-1].get('error')))
            self.c.sleep(0.25)
        raise UnsupportedRun('build timed out (phase never reached ready)')

    def fixture_place(self, socket):
        return self.c.cmd('certify_place %s' % socket, 'explicit_fixture')

    def fixture_place_at(self, x, y):
        return self.c.cmd('certify_place_at %.3f %.3f' % (x, y), 'explicit_fixture')

    def arm(self, socket, label):
        return self.c.cmd('certify_arm %s %s' % (socket, label), 'observation')

    def arm_window(self, label, target=None):
        """Open a window; ``target`` is an arrival region or None for a pure fall."""
        if target is None:
            return self.c.cmd('certify_arm_coords %s none none' % label, 'observation')
        return self.c.cmd('certify_arm_coords %s %s %s' % (label, target['x'], target['y']), 'observation')

    def result(self):
        output = self.c.cmd('certify_result', 'observation')
        return parse_rows(output, 'certify_result'), parse_rows(output, 'certify_trace')

    def sample(self):
        rows = parse_rows(self.c.cmd('certify_sample'), 'certify_sample')
        return rows[-1] if rows else None

    def bounds(self):
        return parse_rows(self.c.cmd('certify_bounds'), 'certify_bounds')

    def capture(self, name):
        if not self.capture_dir:
            return None
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        path = self.capture_dir / name
        self.c.cmd('shot %s' % path, 'evidence_capture')
        return str(path)

    # -- controller replay ----------------------------------------------------------
    def _render(self, op, port):
        kind = op[0]
        if kind == 'walk':
            return 'input %d none %d %d 0' % (port, op[2], 127 * op[1])
        if kind == 'neutral':
            return 'input %d none %d' % (port, op[1])
        if kind == 'button':
            return 'input %d %s %d' % (port, op[1], op[2])
        if kind == 'down':
            return 'input %d DOWN %d' % (port, op[1])
        raise ValueError('unknown probe op: %r' % (op,))

    def replay(self, program, *, capture_prefix=None):
        if not self.pad_owned:
            self.c.cmd('input %d none 1' % self.port, 'controller_sample')
            self.pad_owned = True
        frames_done = 0
        for index, op in enumerate(program):
            self.c.cmd(self._render(op, self.port), 'controller_sample')
            frames = op[-1] if isinstance(op[-1], int) else 1
            frames_done += frames
            self._sleep_frames(frames)
            if capture_prefix and self.capture_stride > 0:
                self.capture('%s_%03d.png' % (capture_prefix, frames_done))
        self.c.cmd('input %d none 2' % self.port, 'controller_sample')
        self._sleep_frames(2)

    def release(self):
        if self.pad_owned:
            self.c.cmd('gd.release_pad(%d)' % self.port, 'controller_cleanup')
            self.pad_owned = False

    # -- cleanup --------------------------------------------------------------------
    def cleanup(self):
        errors = []
        try:
            self.release()
        except Exception as error:  # pragma: no cover - defensive
            errors.append('release: ' + str(error))
        try:
            output = self.c.cmd('certify_cleanup', 'native_cleanup')
            for row in parse_rows(output, 'certify_cleanup_error'):
                errors.append(str(row.get('message')))
        except Exception as error:  # pragma: no cover - defensive
            errors.append('cleanup: ' + str(error))
        return errors

    # -- orchestration --------------------------------------------------------------
    def certify_segment(self, segment, target, floor_y, *, capture_prefix=None):
        if not segment.get('natural', True):
            return {'id': segment['id'], 'status': 'fixture-only', 'checks': {},
                    'manual_review': ['segment is inspection-only']}
        fixture = segment.get('fixture')
        if fixture:
            self.fixture_place_at(fixture['x'], fixture['y'])
        elif segment.get('source'):
            self.fixture_place(segment['source'])
        if capture_prefix:
            self.capture('%s_start.png' % capture_prefix)
        self.arm_window(segment['id'], target)
        outcome = {'id': segment['id'], 'status': 'inconclusive', 'checks': {}, 'manual_review': []}
        for probe in segment.get('probes', []):
            self.replay(probe, capture_prefix=capture_prefix)
            summary, trace = self.result()
            rows = [dict(row) for row in trace]
            samples = [{'x': r.get('x'), 'y': r.get('y'), 'vy': r.get('vy'),
                        'airborne': bool(r.get('airborne')), 'frame': r.get('frame')} for r in rows]
            outcome = classify_trace(summary[-1] if summary else {}, samples,
                                     floor_y=floor_y, target=target,
                                     requires_fall=segment.get('requires_fall', False),
                                     forbid_climb_back=segment.get('forbid_climb_back', False))
            outcome['id'] = segment['id']
            if outcome['status'] in ('arrived', 'fell'):
                break
        if capture_prefix:
            self.capture('%s_end.png' % capture_prefix)
        return outcome


# --- evidence writing --------------------------------------------------------------
def collect_build_info(app_dir):
    app = Path(app_dir)
    info = {'app_dir': str(app.resolve()), 'game_root': str(GAME), 'backend': os.environ.get('MELEE_BACKEND', 'unknown')}
    exe = None
    for candidate in ('melee', 'melee-pc.exe'):
        if (app / candidate).is_file():
            exe = app / candidate
            break
    if exe:
        info['exe'] = str(exe)
        info['exe_sha256'] = _sha256(exe)
    try:
        revision = subprocess.run(['git', '-C', str(GAME), 'rev-parse', 'HEAD'],
                                  capture_output=True, text=True, timeout=10)
        if revision.returncode == 0:
            info['game_revision'] = revision.stdout.strip()
    except Exception:
        pass
    return info


class EvidenceLog:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open('a')

    def write(self, **record):
        record.setdefault('ts', time.time())
        self.handle.write(json.dumps(record) + '\n')
        self.handle.flush()

    def close(self):
        self.handle.close()


def run_certification(app_dir, *, port=51700, templates=None, profiles=None, log_path=None,
                      capture_dir=None, connect=None):
    """Drive a running match. Returns the summary dict; never certifies."""
    templates = list(templates or REQUIRED_TEMPLATES)
    profile_ids = list(profiles or [p['id'] for p in MOBILITY_PROFILES])
    profiles_by_id = {p['id']: p for p in MOBILITY_PROFILES}
    unknown = [p for p in profile_ids if p not in profiles_by_id]
    if unknown:
        raise UnsupportedRun('unknown mobility profiles: ' + ', '.join(unknown))
    installed = Path(app_dir) / 'mods' / MOD_ID / 'scripts/main.lua'
    if not installed.is_file():
        raise UnsupportedRun('certification mod is not installed in %s (run install first)' % app_dir)
    inspection = inspect_recipes(GAME)
    if not inspection['available']:
        raise UnsupportedRun('cannot inspect recipes: ' + str(inspection['reason']))
    plans, errors = build_plans(inspection, templates)
    if errors:
        raise UnsupportedRun('plan validation failed: ' + '; '.join(errors))
    plan_by_template = {p['template']: p for p in plans}
    log = EvidenceLog(log_path or (Path(app_dir) / 'certification' / 'certify-rooms.jsonl'))
    capture_root = Path(capture_dir) if capture_dir else Path(app_dir) / 'certification' / 'captures'
    summary = {'schema': SCHEMA, 'build': collect_build_info(app_dir),
               'log': str(log.path), 'captures': str(capture_root),
               'recipes': {}, 'any_certified': False, 'errors': []}

    owns_socket = connect is None
    if owns_socket:
        def connect():
            sys.path.insert(0, str(GAME / 'pc/scripts'))
            from console import run  # noqa: E402
            return socket.create_connection(('127.0.0.1', port), timeout=10), run
    try:
        sock, console_run = connect()
        reader = sock.makefile('r')
        reader.readline()

        def command(text, category):
            output, ok = console_run(reader, sock, text)
            text_out = '\n'.join(output)
            log.write(category=category, command=text, ok=ok, output=text_out)
            if not ok:
                raise UnsupportedRun('console command failed: ' + text)
            return text_out

        console = Console(command, note=lambda record: log.write(**record))
        driver = CertificationDriver(console, port=1, native_run=True, capture_dir=capture_root)
        driver.ensure_apis()
        driver.ensure_normal_speed()
        for template in templates:
            plan = plan_by_template[template]
            log.write(category='plan', template=template, recipe=plan['recipe'],
                      certified=plan['certified'], segments=[s['id'] for s in plan['segments']])
            summary['recipes'][template] = {'recipe_version': plan['recipe_version'],
                                            'certified_before': plan['certified'],
                                            'certified_after': plan['certified'],
                                            'profiles': {}, 'verdict': None}
            if plan['certified']:
                summary['errors'].append(template + ': already certified; refusing to re-probe')
                continue
            for profile_id in profile_ids:
                profile = profiles_by_id[profile_id]
                outcomes = []
                try:
                    driver.launch_scene(profile['fighter'], profile.get('costume', 0))
                    status = driver.build(template)
                    floor_y = status.get('floor_y', 0)
                    bounds = driver.bounds()
                    log.write(category='bounds', template=template, profile=profile_id, rows=bounds)
                    targets = {s['id']: None for s in plan['segments']}
                    for row in plan['sockets']:
                        x = row.get('rx') if row.get('rx') is not None else row.get('ax')
                        y = row.get('ry') if row.get('ry') is not None else row.get('ay')
                        targets[row['socket']] = {'x': x, 'y': y}
                    for segment in plan['segments']:
                        target = targets.get(segment['target']) if segment['target'] else None
                        prefix = '%s_%s_%s' % (template, profile_id, segment['id'])
                        outcome = driver.certify_segment(segment, target, floor_y, capture_prefix=prefix)
                        outcome['segment'] = segment['id']
                        log.write(category='segment_outcome', template=template, profile=profile_id,
                                  segment=segment['id'], outcome=outcome)
                        outcomes.append(outcome)
                except (MissingAPI, UnsupportedRun) as error:
                    summary['errors'].append('%s/%s: %s' % (template, profile_id, error))
                    outcomes.append({'id': 'setup', 'status': 'error', 'checks': {}, 'manual_review': [str(error)]})
                finally:
                    cleanup_errors = driver.cleanup()
                    if cleanup_errors:
                        log.write(category='cleanup_failure', template=template, profile=profile_id,
                                  errors=cleanup_errors)
                verdict = recipe_verdict(plan['recipe'], plan['recipe_version'], outcomes, native_run=True)
                summary['recipes'][template]['profiles'][profile_id] = {
                    'verdict': verdict, 'outcomes': outcomes}
                log.write(category='recipe_verdict', template=template, profile=profile_id, verdict=verdict)
            summaries = [p['verdict'] for p in summary['recipes'][template]['profiles'].values()]
            summary['recipes'][template]['verdict'] = _aggregate_verdict(plan, summaries)
    finally:
        if owns_socket and 'sock' in locals():
            try:
                sock.close()
            except Exception:
                pass
        log.close()
    return summary


def _aggregate_verdict(plan, verdicts):
    return {
        'schema': SCHEMA, 'recipe': plan['recipe'], 'recipe_version': plan['recipe_version'],
        'certified': False, 'auto_certification': 'forbidden',
        'verdict': 'manual-review-required', 'requires_human_review': True,
        'profiles': len(verdicts),
        'failed': sorted({s for v in verdicts for s in v.get('failed_segments', [])}),
        'inconclusive': sorted({s for v in verdicts for s in v.get('inconclusive_segments', [])}),
        'note': 'No recipe may be marked certified from this harness output.',
    }


# --- CLI ---------------------------------------------------------------------------
def _print_json(value):
    print(json.dumps(value, indent=2, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)

    inspect = sub.add_parser('inspect', help='resolve uncertified recipes purely')
    inspect.add_argument('--template', action='append', default=[])
    inspect.add_argument('--json', type=Path)

    plan = sub.add_parser('plan', help='build and validate native certification plans')
    plan.add_argument('--template', action='append', default=[])
    plan.add_argument('--json', type=Path)

    install_parser = sub.add_parser('install', help='install the isolated certification mod')
    install_parser.add_argument('--app-dir', type=Path, required=True)
    install_parser.add_argument('--no-enable', action='store_true', help='do not change enabled.txt')
    install_parser.add_argument('--allow-shared', action='store_true',
                                help='permit the workspace shared review app dir')

    restore_parser = sub.add_parser('restore', help='restore the original enabled-mod list')
    restore_parser.add_argument('--app-dir', type=Path, required=True)

    run = sub.add_parser('run', help='drive an already running 60 Hz native match')
    run.add_argument('--app-dir', type=Path, required=True)
    run.add_argument('--port', type=int, default=51700)
    run.add_argument('--recipe', action='append', default=[])
    run.add_argument('--profile', action='append', default=[])
    run.add_argument('--log', type=Path)
    run.add_argument('--capture-dir', type=Path)
    run.add_argument('--summary', type=Path)

    args = parser.parse_args(argv)
    if args.action == 'inspect':
        result = inspect_recipes(GAME)
        if args.template:
            wanted = set(args.template)
            result['recipes'] = [r for r in result['recipes'] if r['template'] in wanted]
            result['sockets'] = {k: v for k, v in result.get('sockets', {}).items() if k in wanted}
            result['openings'] = {k: v for k, v in result.get('openings', {}).items() if k in wanted}
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        _print_json(result)
        return 0 if result['available'] else 1
    if args.action == 'plan':
        inspection = inspect_recipes(GAME)
        if not inspection['available']:
            print('recipe inspection unavailable: ' + str(inspection['reason']), file=sys.stderr)
            return 1
        templates = args.template or list(REQUIRED_TEMPLATES)
        plans, errors = build_plans(inspection, templates)
        result = {'schema': SCHEMA, 'plans': plans, 'errors': errors, 'certified': False,
                  'verdict': 'pending-native-run'}
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        _print_json(result)
        return 0 if not errors else 1
    if args.action == 'install':
        _print_json(install(args.app_dir, enable=not args.no_enable, allow_shared=args.allow_shared))
        return 0
    if args.action == 'restore':
        _print_json(restore(args.app_dir))
        return 0
    if args.action == 'run':
        if os.environ.get('MELEE_TURBO', '').strip() not in ('', '0'):
            print('refusing to run: MELEE_TURBO is set; certification needs normal speed', file=sys.stderr)
            return 2
        if os.environ.get('MELEE_FPS', '').strip().lower() == 'u':
            print('refusing to run: MELEE_FPS=u is uncapped; certification needs normal speed', file=sys.stderr)
            return 2
        summary = run_certification(args.app_dir, port=args.port,
                                    templates=args.recipe or list(REQUIRED_TEMPLATES),
                                    profiles=args.profile or [p['id'] for p in MOBILITY_PROFILES],
                                    log_path=args.log, capture_dir=args.capture_dir)
        if args.summary:
            args.summary.parent.mkdir(parents=True, exist_ok=True)
            args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
        _print_json(summary)
        return 0 if not summary['errors'] else 1
    return 2


if __name__ == '__main__':
    sys.exit(main())
