#!/usr/bin/env python3
"""Independent Gate 3 room-layout test: distinctness, BF kit grounding, budgets.

This is an independent wrapper, not a restatement of the builder's numbers. It
runs the real pure Lua modules (`room_catalogue.lua`, `room_recipes.lua`,
`rooms.lua`), then checks them against the actual installed BF kit meshes and
sidecars (dimensions, collider endpoints, atlas), the native capacity constants
compiled into the engine, and a directed per-mobility reachability screen.

It proves an authoring/asset contract only. It never runs the game, so nothing
here certifies a layout; every recipe must still read `certified == false`.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import unittest
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
import game_source

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = game_source.ROGUELITE
NATIVE = game_source.GAME
KIT = ROOT / 'menu/out_roguelite/room-kit'
EXPORTER = RUNTIME.parent / 'bf_interior_room/models'
HEADER = struct.Struct('>4sIIIfffII')

# Role groups for the finite content target (plan section 3).
ROLE_TARGETS = {
    'traversal': (('traversal',), 5),
    'combat': (('combat',), 4),
    'branch_connector': (('branch', 'connector'), 3),
    'rest_reward': (('rest', 'reward'), 2),
    'boss': (('boss',), 2),
}
ANCHORS = {'left': (-52, 0), 'right': (52, 0), 'top': (39, 26)}
STRUCTURAL = {'mainfloor', 'trim', 'wall', 'portal', 'beam', 'post'}
UNIT_SCALE = {'mainfloor', 'trim', 'wall', 'portal', 'beam', 'post'}


def _lua() -> str:
    found = shutil.which('lua5.4') or shutil.which('lua')
    assert found, 'Lua interpreter required'
    return found


LUA_DUMP = r'''
local C=dofile(arg[1]); local Recipes=dofile(arg[2]); local Rooms=dofile(arg[3])
local function copy(t) if type(t)~='table' then return t end local o={} for k,v in pairs(t) do o[k]=copy(v) end return o end
local function row(...) local f={} for i=1,select('#',...) do f[i]=tostring(select(i,...)) end print(table.concat(f,'\t')) end
assert(C.validate(  ))
for name in pairs(Recipes.mobility_profiles) do
  row('DIRECTED',name,Recipes.can_traverse({lo=0,hi=0,y=0},{lo=0,hi=0,y=26},name) and 1 or 0,
      Recipes.can_traverse({lo=0,hi=0,y=26},{lo=0,hi=0,y=0},name) and 1 or 0)
end
local audit=C:audit(Recipes)
row('AUDIT',audit.templates,audit.distinct)
for role,g in pairs(audit.by_role) do row('ROLE',role,g.templates,g.distinct_count) end
for sig,ids in pairs(audit.aliases) do row('ALIAS',table.concat(ids,',')) end
for recipe,ids in pairs(audit.recipe_aliases) do row('RECIPE_ALIAS',recipe,table.concat(ids,',')) end
-- Negative screen regressions: entry-based seeding, required surfaces, finite
-- coordinates. These must be refused, not silently passed.
local function rclone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=rclone(x) end return o end
local function neg(label,recipe,profile,opts)
  local ok,why=Recipes.screen(recipe,profile,opts)
  row('SCREEN_NEG',label,ok and 1 or 0,why or '')
end
local zero={jump_height=0,horizontal_gap=0,fall_gap=0}
neg('shortcut_zero',Recipes.recipes.shortcut_door,zero)
neg('crossing_zero',Recipes.recipes.crossing_door,zero)
local raised=rclone(Recipes.recipes.combat_dais)
raised.geometry.platforms[#raised.geometry.platforms+1]={x=0,y=60,width=10,passthrough=true,ledges=true}
neg('raised_unreachable',raised,'standard')
local nanplat=rclone(Recipes.recipes.combat_dais)
nanplat.geometry.platforms[1].y=0/0
neg('nan_platform_y',nanplat,'standard')
local infline=rclone(Recipes.recipes.combat_flank)
infline.geometry.lines[1].y0=1/0
neg('inf_line',infline,'standard')
neg('entry_off_surface',Recipes.recipes.lane_open,'standard',{entry={x=0,y=40}})
local function make_node(id,t,g,r)
  local node={id='layout_'..id,template_id=id,recipe=t.recipe,recipe_modules=copy(r.modules or {}),
    recipe_version=r.version,theme=t.theme or 'cobalt',kind=t.role,room=copy(g),exits={}}
  for _,socket in ipairs(t.sockets) do
    node.room.arrivals[socket.id]=copy(g.arrivals[socket.side])
    node.exits[#node.exits+1]={socket=socket.id,side=socket.side,anchor=copy(g.exit_anchors[socket.side]),to='other'}
  end
  return node
end
local ids={} for id in pairs(C.rooms) do ids[#ids+1]=id end table.sort(ids)
for _,id in ipairs(ids) do
  local t=C.rooms[id]
  local g,r=assert(Recipes.resolve(t))
  row('TEMPLATE',id,t.role,t.recipe,t.shape,t.theme or '',r.version,r.certified and 1 or 0,#t.sockets)
  row('SIGNATURE',id,Recipes.signature(r,t))
  for _,socket in ipairs(t.sockets) do
    local an=g.exit_anchors[socket.side]; local ar=g.arrivals[socket.side]
    row('SOCKET',id,socket.id,socket.side,an.x,an.y,an.drop and 1 or 0,ar.x,ar.y,ar.facing)
  end
  for _,p in ipairs(g.platforms or {}) do row('PLAT',id,p.x,p.y,p.width,p.passthrough and 1 or 0,p.ledges and 1 or 0) end
  for _,l in ipairs(g.lines or {}) do row('LINE',id,l.x0,l.y0,l.x1,l.y1,l.part or '') end
  for _,o in ipairs(g.floor.openings or {}) do row('OPEN',id,o.x,o.width) end
  for _,m in ipairs(r.modules or {}) do row('MODULE',id,m.part,m.x,m.y,m.scale_x or 1,m.scale_y or 1) end
  local node=make_node(id,t,g,r)
  local plan=assert(Rooms.plan(node))
  local models={}
  for _,part in ipairs(plan.parts) do
    row('PART',id,part.kind,part.model,part.x,part.y,part.z,part.scale_x,part.scale_y,part.scale_z)
    models[part.model]=true
  end
  local mcount=0 for _ in pairs(models) do mcount=mcount+1 end
  row('MODELCOUNT',id,mcount)
  row('PARTCOUNT',id,#plan.parts)
  local col=assert(Rooms.collision(node))
  row('COLLISION',id,#col.floor_segments,#col.platforms,#col.lines)
  for _,s in ipairs(col.floor_segments) do row('SEG',id,s.left,s.right,s.y) end
  for name in pairs(Recipes.mobility_profiles) do
    local ok,why=Recipes.screen(r,name)
    row('SCREEN',id,name,ok and 1 or 0,why or '')
  end
  if id=='traverse_bridge' then
    -- Saved-geometry readback: mutate the live recipe, then plan the captured
    -- snapshot. The plan must not regenerate from the changed recipe table.
    local live=Recipes.recipes[t.recipe]
    local original=live.geometry
    live.geometry={floor={left=-65,right=65,y=0,openings={}},kit=original.kit,platforms={},
      exit_anchors=original.exit_anchors,arrivals=original.arrivals}
    local node2=make_node(id,t,g,r)
    local plan2=Rooms.plan(node2)
    live.geometry=original
    if plan2 then
      row('READBACK',id,#plan2.parts,(#plan2.parts==#plan.parts) and 1 or 0,plan2.recipe_version or 0)
    else
      row('READBACK',id,-1,0,0)
    end
  end
end
'''


def load_dump() -> dict:
    proc = subprocess.run(
        [_lua(), '-', str(RUNTIME / 'room_catalogue.lua'), str(RUNTIME / 'room_recipes.lua'), str(RUNTIME / 'rooms.lua')],
        input=LUA_DUMP, text=True, capture_output=True, timeout=60,
    )
    if proc.returncode != 0:
        raise AssertionError('Lua dump failed:\n' + proc.stdout + proc.stderr)
    groups: dict[str, list[list[str]]] = {}
    for line in proc.stdout.splitlines():
        if not line:
            continue
        fields = line.split('\t')
        groups.setdefault(fields[0], []).append(fields[1:])
    return groups


def parse_mesh(path: Path) -> dict:
    data = path.read_bytes()
    magic, version, nv, ni, width, depth, height, voff, ioff = HEADER.unpack_from(data)
    assert (magic, version) == (b'GXMS', 2), f'{path.name}: bad mesh magic'
    assert ioff + ni * 2 == len(data), f'{path.name}: truncated mesh'
    points = [struct.unpack_from('>8f', data, voff + i * 32)[:3] for i in range(nv)]
    lo = [min(p[a] for p in points) for a in range(3)]
    hi = [max(p[a] for p in points) for a in range(3)]
    return {'nverts': nv, 'nindices': ni, 'dims': (width, depth, height), 'lo': lo, 'hi': hi,
            'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def parse_sidecar(path: Path) -> dict:
    return json.loads(path.read_text())


def native_caps() -> dict:
    header = (NATIVE / 'pc/gameworld/script_model.h').read_text()
    stage = (NATIVE / 'pc/gameworld/script_game.c').read_text()
    def macro(text, name):
        match = re.search(rf'#define\s+{name}\s+(\d+)', text)
        assert match, f'missing native {name}'
        return int(match.group(1))
    return {
        'mesh_assets': macro(header, 'SCRIPT_MESH_ASSETS'),
        'mesh_instances': macro(header, 'SCRIPT_MESH_INSTANCES'),
        'mesh_lines': macro(header, 'SCRIPT_MESH_LINES'),
        'stage_lines': macro(stage, 'SCRIPT_STAGE_LINES'),
        'stage_models': macro(stage, 'SCRIPT_STAGE_MODELS'),
    }


def rooms_budget() -> dict:
    source = (RUNTIME / 'rooms.lua').read_text()
    match = re.search(r'R=\{version=\d+,max_instances=(\d+),max_assets=(\d+)', source)
    assert match, 'rooms.lua budget header not found'
    collision = re.search(r'floor_segments\+#collision\.platforms\+#collision\.lines>(\d+)\s+then error\(\'collision budget\'\)', source)
    assert collision, 'rooms.lua collision budget not found'
    return {'max_instances': int(match.group(1)), 'max_assets': int(match.group(2)),
            'collision_budget': int(collision.group(1))}


class RoomLayoutTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.dump = load_dump()
        cls.templates = {row[0]: row for row in cls.dump['TEMPLATE']}
        cls.audit = {row[0]: row for row in cls.dump.get('AUDIT', [])}
        cls.signatures = {row[0]: row[1] for row in cls.dump.get('SIGNATURE', [])}
        cls.manifest = json.loads((KIT / 'manifest.json').read_text())
        cls.kit_models = {row['name'][:-len('.gxmesh')]
                          for row in cls.manifest['files'] if row['name'].endswith('.gxmesh')}
        cls.sidecars = {name: parse_sidecar(KIT / f'{name}.coll.json') for name in cls.kit_models}

    def test_distinct_layout_targets_and_alias_audit(self):
        audit = list(self.audit.values())
        self.assertEqual(len(audit), 1, 'expected one audit row')
        total, distinct = int(audit[0][0]), int(audit[0][1])
        self.assertEqual(total, len(self.templates), 'audit must cover every template')
        self.assertGreaterEqual(distinct, 16, 'fewer than 16 distinct authored layouts')
        self.assertGreaterEqual(total, 24, 'catalogue expansion is too small')

        roles = {row[0]: (int(row[1]), int(row[2])) for row in self.dump['ROLE']}
        for group, (members, minimum) in ROLE_TARGETS.items():
            signatures = {self.signatures[t] for t, meta in self.templates.items() if meta[1] in members}
            self.assertGreaterEqual(len(signatures), minimum, f'{group} distinct layouts below target')
            for member in members:
                self.assertIn(member, roles, f'missing role {member}')

        # True aliases are explicitly reported: every group shares one signature
        # and, conversely, no signature is hidden behind an alias-free row.
        alias_groups = [set(row[0].split(',')) for row in self.dump.get('ALIAS', [])]
        aliased = set().union(*alias_groups) if alias_groups else set()
        by_sig: dict[str, set[str]] = {}
        for template, signature in self.signatures.items():
            by_sig.setdefault(signature, set()).add(template)
        for group in alias_groups:
            signatures = {self.signatures[t] for t in group}
            self.assertEqual(len(signatures), 1, f'alias group spans signatures: {group}')
        for signature, members in by_sig.items():
            if len(members) > 1:
                self.assertIn(members, alias_groups, f'undisclosed alias for {sorted(members)}')
        self.assertEqual(len(aliased) + len(by_sig) - len([g for g in alias_groups]),
                         len(self.templates),
                         'alias accounting must partition the catalogue')
        self.assertTrue({'lane_pit', 'arena_drop'} <= aliased, 'lane_pit/arena_drop alias must be declared')
        self.assertTrue({'lane_balcony', 'lane_fork', 'arena_tiered', 'rest_balcony'} <= aliased,
                        'reviewed ascent alias group must be declared')
        # Geometry diversity is honest: a split and a merge sharing the ascent
        # surface are the same geometry, so they must be aliased, not counted
        # twice on the strength of a shape label.
        self.assertTrue({'branch_y', 'rejoin_merge'} <= aliased,
                        'shape-only designs must alias by geometry')

    def test_certification_and_version_discipline(self):
        for template, meta in self.templates.items():
            _id, role, recipe, shape, theme, version, certified, sockets = meta
            self.assertEqual(int(version), 2, f'{template} recipe version changed')
            self.assertEqual(int(certified), 0, f'{template} may not be certified without a native replay')
            self.assertGreaterEqual(int(sockets), 1, f'{template} has no sockets')
            if theme:
                self.assertIn(theme, ('cobalt', 'fire', 'frost'), f'{template} unknown theme')

    def test_mesh_sidecars_ground_every_line_and_module(self):
        # Installed kit is the reviewed exporter output, not a rewritten copy.
        for name in self.kit_models:
            self.assertEqual(self.sidecars[name], parse_sidecar(EXPORTER / f'{name}.coll.json'),
                             f'{name}: installed sidecar drifted from the exporter')
            mesh = parse_mesh(KIT / f'{name}.gxmesh')
            manifest_row = next(r for r in self.manifest['files'] if r['name'] == f'{name}.gxmesh')
            self.assertEqual(manifest_row['sha256'], mesh['sha256'], f'{name}: manifest hash mismatch')
            self.assertEqual(manifest_row['bytes'], mesh['bytes'], f'{name}: manifest size mismatch')
            source_mesh = EXPORTER / f'{name}.gxmesh'
            if source_mesh.exists():  # the exporter .gxmesh binaries are generated, often not checked out
                source = parse_mesh(source_mesh)
                self.assertEqual(mesh['dims'], source['dims'], f'{name}: installed dims drifted')
                self.assertEqual(mesh['sha256'], source['sha256'], f'{name}: installed mesh drifted')
            for line in self.sidecars[name]['lines']:
                for x, y in ((line[1], line[2]), (line[3], line[4])):
                    self.assertLessEqual(mesh['lo'][0] - 1e-6, x)
                    self.assertLessEqual(x, mesh['hi'][0] + 1e-6)
                    self.assertLessEqual(mesh['lo'][1] - 1e-6, y)
                    self.assertLessEqual(y, mesh['hi'][1] + 1e-6)

        for template in self.templates:
            for part, x, y, sx, sy in [(r[1], float(r[2]), float(r[3]), float(r[4]), float(r[5]))
                                       for r in self.dump.get('MODULE', []) if r[0] == template]:
                self.assertIn(part, self.kit_models, f'{template}: unknown module {part}')
                self.assertEqual(x % 13, 0, f'{template}: module {part} off the 13-unit grid')
                self.assertIn(y, (0, 13, 26), f'{template}: module {part} off the storey grid')
                self.assertLessEqual(abs(sx), 100)
            for x0, y0, x1, y1, part in [(float(r[1]), float(r[2]), float(r[3]), float(r[4]), r[5])
                                         for r in self.dump.get('LINE', []) if r[0] == template]:
                self.assertLess(x0, x1)
                self.assertTrue(-65 <= x0 and x1 <= 65 and 0 <= y0 <= 60 and 0 <= y1 <= 60)
                self.assertTrue(part, f'{template}: slope line without a part')
                placed = [(float(r[2]), float(r[3]), float(r[4]), float(r[5]))
                          for r in self.dump.get('MODULE', []) if r[0] == template and r[1] == part]
                self.assertTrue(placed, f'{template}: slope part {part} not placed')
                side = self.sidecars[part]['lines'][0]
                line = {(x0, y0), (x1, y1)}
                matched = False
                for mx, my, sx, sy in placed:
                    expected = {(mx + sx * side[1], my + sy * side[2]),
                                (mx + sx * side[3], my + sy * side[4])}
                    if expected == line:
                        matched = True
                self.assertTrue(matched,
                                f'{template}: {part} slope endpoints disagree with the exporter sidecar')

    def test_plans_obey_bf_rules_arrivals_budgets(self):
        budget = rooms_budget()
        caps = native_caps()
        self.assertLessEqual(budget['max_instances'], caps['mesh_instances'])
        self.assertLessEqual(budget['max_assets'], caps['mesh_assets'])
        self.assertLessEqual(budget['collision_budget'], caps['stage_lines'])

        for template, meta in self.templates.items():
            sockets = [r for r in self.dump.get('SOCKET', []) if r[0] == template]
            plats = [(float(r[1]), float(r[2]), float(r[3]), r[4] == '1', r[5] == '1')
                     for r in self.dump.get('PLAT', []) if r[0] == template]
            opens = [(float(r[1]), float(r[2])) for r in self.dump.get('OPEN', []) if r[0] == template]
            parts = [r for r in self.dump.get('PART', []) if r[0] == template]
            segs = [(float(r[1]), float(r[2]), float(r[3])) for r in self.dump.get('SEG', []) if r[0] == template]
            collision = [r for r in self.dump.get('COLLISION', []) if r[0] == template]
            self.assertTrue(collision, f'{template}: no collision plan')

            # Socket anchors and safe arrivals.
            for _tid, sid, side, ax, ay, drop, arx, ary, facing in sockets:
                ax, ay, arx, ary = float(ax), float(ay), float(arx), float(ary)
                if side in ANCHORS:
                    self.assertEqual((ax, ay), ANCHORS[side], f'{template}/{sid}: anchor off the reviewed grid')
                    self.assertEqual(drop, '0', f'{template}/{sid}: unexpected drop flag')
                else:
                    self.assertEqual(side, 'bottom')
                    self.assertEqual((drop, ay), ('1', -6.0), f'{template}/{sid}: drop anchor malformed')
                self.assertIn(facing, ('1', '-1'))
                supported = any(lo + 2 <= arx <= hi - 2 and abs(ary - y) < 0.01 for lo, hi, y in segs)
                supported = supported or any(px - w / 2 + 2 <= arx <= px + w / 2 - 2 and abs(ary - py) < 0.01
                                             for px, py, w, _p, _l in plats)
                self.assertTrue(supported, f'{template}/{sid}: arrival is not on a solid surface')

            # Recovery space: the ground floor reaches both room ends and is
            # wide enough to fight and recover after a knockback.
            ground = [(lo, hi) for lo, hi, y in segs if abs(y) < 0.01]
            self.assertTrue(ground, f'{template}: no ground floor')
            self.assertLessEqual(min(lo for lo, _hi in ground), -60, f'{template}: no left recovery space')
            self.assertGreaterEqual(max(hi for _lo, hi in ground), 60, f'{template}: no right recovery space')
            self.assertGreaterEqual(sum(hi - lo for lo, hi in ground), 100, f'{template}: too little ground')

            # Real openings, split exactly on the exporter gap; never filled.
            hole = [(x - w / 2, x + w / 2) for x, w in opens]
            for lo, hi in hole:
                self.assertIn((-6.5, 6.5), [(round(lo, 4), round(hi, 4))],
                              f'{template}: opening is not the authored 13-unit gap')
            for px, py, _w, _p, _l in plats:
                self.assertFalse(py == 0 and any(lo <= px <= hi for lo, hi in hole),
                                 f'{template}: platform fills a floor opening')

            # Visual/collision agreement: every raised collision platform maps to
            # a placed module whose exporter floor line spans it, and every flat
            # module placement maps to a platform. No staircase-like visual
            # without standable collision, and no invisible collision.
            flat_placed = []
            for _pid, _kind, model, mx, my, _z, sx, _sy, _sz in parts:
                mx, my, sx = float(mx), float(my), float(sx)
                for line in self.sidecars[model]['lines']:
                    if line[0] == 'floor' and abs(line[2] - line[4]) < 1e-6:
                        center = mx + sx * (line[1] + line[3]) / 2
                        flat_placed.append((mx, my, center, abs(sx) * (line[3] - line[1])))
            for px, py, w, _p, _l in plats:
                if py == 0:
                    continue
                matched = [f for f in flat_placed if abs(f[0] - px) < 0.01 and abs(f[1] - py) < 0.01
                           and abs(f[2] - px) < 0.01 and abs(f[3] - w) < 0.01]
                self.assertTrue(matched, f'{template}: platform ({px},{py}) has no matching visual module')
            for mx, my, _c, _w in flat_placed:
                if my == 0:
                    continue
                self.assertTrue(any(abs(mx - px) < 0.01 and abs(my - py) < 0.01
                                    for px, py, _pw, _pp, _pl in plats),
                                f'{template}: flat module ({mx},{my}) has no collision platform')

            for _pid, kind, model, x, y, z, sx, sy, sz in parts:
                x, y, z, sx, sy, sz = map(float, (x, y, z, sx, sy, sz))
                self.assertTrue(model.startswith('bf_'), f'{template}: non-kit model {model}')
                self.assertEqual(z, 0, f'{template}: render depth policy must preserve authored projection')
                self.assertTrue(-65 <= x <= 65 and 0 <= y <= 60)
                if kind in STRUCTURAL:
                    self.assertEqual(x % 13, 0, f'{template}: {kind} off the 13-unit grid')
                    self.assertIn(y, (0, 13, 26), f'{template}: {kind} off the storey grid')
                    self.assertEqual(abs(sz), 1)
                if kind in UNIT_SCALE:
                    self.assertIn(sx, (1, -1), f'{template}: {kind} is not unit scale')
                    self.assertEqual(sy, 1, f'{template}: {kind} is not unit scale')
                if kind == 'beam':
                    self.assertEqual(y, 26, f'{template}: beam not at a storey top')
                if kind == 'post':
                    self.assertEqual(y, 0, f'{template}: post not standing on the floor')
                if kind == 'trim':
                    self.assertIn(x, (-65, 65), f'{template}: trim not at a floor end')

            for px, py, w, passthrough, ledges in plats:
                self.assertGreater(w, 0)
                self.assertLessEqual(px - w / 2, 65)
                self.assertGreaterEqual(px - w / 2, -65)
                self.assertLessEqual(px + w / 2, 65)
                if not passthrough:
                    self.assertFalse(ledges, f'{template}: interior seam ledge on a solid landing')

            # BF placement rule: a surface that shares an edge with another
            # surface, a floor segment or a ramp endpoint is an interior seam and
            # must not carry ledges (the per-surface flag cannot vary per edge).
            lines = [(float(r[1]), float(r[2]), float(r[3]), float(r[4]))
                     for r in self.dump.get('LINE', []) if r[0] == template]
            seam_edges = set()
            for lo, hi, y in segs:
                seam_edges.add((round(lo, 3), round(y, 3)))
                seam_edges.add((round(hi, 3), round(y, 3)))
            for x0, y0, x1, y1 in lines:
                seam_edges.add((round(x0, 3), round(y0, 3)))
                seam_edges.add((round(x1, 3), round(y1, 3)))
            plat_edges = {}
            for index, (px, py, w, _p, _l) in enumerate(plats):
                plat_edges[index] = {(round(px - w / 2, 3), round(py, 3)),
                                     (round(px + w / 2, 3), round(py, 3))}
            for index, (px, py, w, passthrough, ledges) in enumerate(plats):
                others = set(seam_edges)
                for other_index, edges in plat_edges.items():
                    if other_index != index:
                        others |= edges
                if plat_edges[index] & others:
                    self.assertFalse(ledges,
                                     f'{template}: platform ({px},{py}) shares an interior seam but carries ledges')
            if template == 'combat_flank':
                for row in [r for r in self.dump['PLAT'] if r[0] == 'combat_flank']:
                    self.assertEqual(row[5], '0', 'combat_flank seam surfaces must not carry ledges')

            # Doorway replaces a wall bay; no wall behind an opening.
            for x in {p[3] for p in parts if p[1] == 'portal'}:
                self.assertNotIn(x, {p[3] for p in parts if p[1] == 'wall'},
                                 f'{template}: wall left behind a doorway')

            # Budgets are derived from the engine constants, not invented.
            self.assertLessEqual(int([r for r in self.dump['PARTCOUNT'] if r[0] == template][0][1]),
                                 budget['max_instances'])
            self.assertLessEqual(int([r for r in self.dump['MODELCOUNT'] if r[0] == template][0][1]),
                                 budget['max_assets'])
            self.assertLessEqual(int(collision[0][1]) + int(collision[0][2]) + int(collision[0][3]),
                                 budget['collision_budget'])

    def test_directed_mobility_screen_and_readback(self):
        directed = {row[0]: (row[1], row[2]) for row in self.dump['DIRECTED']}
        for profile in ('short_heavy', 'fast_faller', 'standard'):
            self.assertEqual(directed[profile][0], '0', f'{profile} should not jump 26 units upward')
            self.assertEqual(directed[profile][1], '1', f'{profile} should fall 26 units')
            self.assertNotEqual(directed[profile][0], directed[profile][1], 'screen must be directed')
        for profile in ('floaty', 'multi_jump'):
            self.assertEqual(directed[profile][0], '1')

        for template in self.templates:
            for row in [r for r in self.dump['SCREEN'] if r[0] == template]:
                self.assertEqual(row[2], '1', f'{template} unreachable for {row[1]}: {row[3]}')

        # Negative screens: disconnected floors (zero jump/gap), a raised
        # unreachable required surface, NaN/inf geometry and an off-surface
        # entry must all be refused.
        negative = {row[0]: row[1] for row in self.dump.get('SCREEN_NEG', [])}
        for label in ('shortcut_zero', 'crossing_zero', 'raised_unreachable',
                      'nan_platform_y', 'inf_line', 'entry_off_surface'):
            self.assertIn(label, negative, f'missing negative screen {label}')
            self.assertEqual(negative[label], '0', f'{label} was not refused')

        readback = [r for r in self.dump.get('READBACK', []) if r[0] == 'traverse_bridge']
        self.assertTrue(readback, 'saved-geometry readback case missing')
        partcount = int([r for r in self.dump['PARTCOUNT'] if r[0] == 'traverse_bridge'][0][1])
        self.assertEqual(int(readback[0][1]), partcount, 'planner regenerated geometry from the live recipe')
        self.assertEqual(readback[0][2], '1')
        self.assertEqual(int(readback[0][3]), 2, 'prior recipe version was not read back')


if __name__ == '__main__':
    unittest.main(verbosity=2)
