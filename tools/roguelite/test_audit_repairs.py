"""Actual bundled Lua regressions for the October state-integrity audit."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
from tools.roguelite import prepare
from test_maze_runtime import PRELUDE, ENGINE, HELPERS

LUA = shutil.which('lua') or shutil.which('lua5.4')


class AuditRepairs(unittest.TestCase):
    def execute(self, code):
        result = subprocess.run([LUA, '-'], input=code, text=True, encoding='utf-8',
                                errors='replace', capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def runtime(self, body, after_reload=None, maze=False):
        wrapped=';(function()\n'+prepare.bundle()+'\nend)()\ncommands.rogue_start()\n'
        engine=ENGINE if maze else ENGINE.replace('generator=maze','generator=physical')
        code='local SOURCE='+json.dumps(prepare.SOURCE.as_posix())+'\n'+PRELUDE+engine+wrapped+HELPERS+body
        if after_reload is not None: code+=wrapped+after_reload
        self.execute(code)

    def test_starter_selection_roundtrips_and_discard_reselects(self):
        self.runtime(r'''
step();settle();click('gene:g3');click('starter')
assert(state().menu_view.starter=='g3');on_unload();request=true;tick=0
''',r'''
step();settle();assert(state().menu_view.starter=='g3','saved starting ability was lost')
click('gene:g3');click('discard');click('discard')
assert(state().menu_view.starter=='g1','discard left a missing starter selected')
''')

    def test_room_storage_error_can_return_home_after_recovery(self):
        self.runtime(r'''
local old_launch=gd.scene_launch;local home=false
gd.scene_launch=function(opts)if opts.mode=='menu'then home=true;return true end;return old_launch(opts)end
step();settle();fail_write=true;click('start');assert(state().menu=='error')
fail_write=false;press(512);settle()
assert(home and not pause,'repaired storage left the error screen inert')
''')

    def test_dead_actor_cleanup_does_not_block_recovery(self):
        self.runtime(r'''
local old_remove=gd.enemy_remove
gd.enemy_remove=function(h)local alive=enemies[h]~=nil;old_remove(h);return alive end
start();local n=decoded().manifest.nodes[state().node];travel(n.exits[1]);assert(next(enemies))
for h in pairs(enemies)do enemies[h]=nil end
isolated=false;tick=tick+1;on_frame();assert(state().menu=='error');isolated=true
local home=false;gd.scene_launch=function(opts)assert(opts.mode=='menu');home=true;return true end
press(512);settle();assert(home,'already-dead native actor blocked Home cleanup')
''', maze=True)

    def test_snapshot_load_returns_to_durable_collection(self):
        self.runtime(r'''
start();local runid=state().run.id;local n=decoded().manifest.nodes[state().node]
-- Both nodes are solo; their transition stays in the same native scene epoch.
local original={};for k,v in pairs(models)do original[k]=v end
travel(n.exits[1]);assert(state().node~='entry');models=original;enemies={}
assert(type(on_loadstate)=='function','Envoy has no native snapshot recovery hook')
on_loadstate(1);settle()
assert(not state().active and state().menu=='collection','stale Lua director kept running')
assert(state().run.id==runid and state().run.progress.room==decoded().run.progress.room)
''', maze=True)

    def test_snapshot_recovery_preserves_durable_finished_exports(self):
        self.runtime(r'''
step();settle();click('start');local rid=state().run.id
ps[1].x=390;ps[1].y=0;press(4);settle();assert(state().profile.finished[rid])
local before=C.snapshot(state().profile)
assert(type(on_loadstate)=='function');on_loadstate(1);settle()
assert(C.snapshot(state().profile)==before and state().run==nil,'load rewound a durable export')
''')

    def test_snapshot_load_keeps_the_loader_error_when_no_slot_is_usable(self):
        self.runtime(r'''
start();assert(state().active)
files['checkpoint-a.txt']='not a checkpoint';files['checkpoint-b.txt']='also not a checkpoint'
on_loadstate(1);settle()
assert(not state().active,'stale Lua director kept running')
assert(state().menu=='error','snapshot recovery replaced the loader error with '..tostring(state().menu))
assert(state().menu_view.section~='collection','error state drew the collection')
assert(files['checkpoint-a.txt']=='not a checkpoint' and files['checkpoint-b.txt']=='also not a checkpoint',
 'unusable checkpoints were overwritten')
''', maze=True)

    def test_pending_exports_paginate_and_decline_requires_confirmation(self):
        self.execute('Core=assert(loadfile('+json.dumps((prepare.SOURCE/'core.lua').as_posix())+'))()\n'
            +'local M=assert(loadfile('+json.dumps((prepare.SOURCE/'menus.lua').as_posix())+'))()\n'+r'''
local p=Core.new_profile(321);local pending={}
for i=1,20 do pending[i]={run='run'..i,gene='r1',kind='cinder'}end
local ctx={menu='collection',profile=p,starter='g1',capacity={count=128,max=128,full=true},pending_exports=pending}
local s=M.new();M.view(s,ctx);s.focus='exports';M.update(s,ctx,{confirm=true})
local v=M.view(s,ctx);assert(v.section=='exports','pending exports need a dedicated screen')
local shown={}
for _,b in ipairs(v.controls)do
 assert(b.y>=0 and b.y+b.h<=460,'export control outside the readable canvas')
 if b.action.kind=='decline_export'then shown[b.action.run]=true;s.focus=b.id end
end
assert(next(shown) and not shown.run20,'exports were not paginated')
local first=M.update(s,ctx,{confirm=true});assert(first.kind=='blocked','decline must require confirmation')
local second=M.update(s,ctx,{confirm=true});assert(second.kind=='decline_export')
local visited={};s.page=1
while true do
 local page=M.view(s,ctx);local next_id
 for _,b in ipairs(page.controls)do
  if b.action.kind=='decline_export'then visited[b.action.run]=true end
  if b.id=='next' and b.enabled then next_id=b.id end
 end
 if not next_id then break end;s.focus=next_id;assert(M.update(s,ctx,{confirm=true})==nil)
end
for i=1,20 do assert(visited['run'..i],'pending export unreachable')end
''')

    def editor(self, body):
        root=Path(__file__).resolve().parents[2]
        fixture=require_game('pc/tests/map_editor_test.lua').read_text().split('local chunk = loadfile')[0]
        stage=r'''
local live_spawns={}
gd.stage_set_spawn=function(slot,x,y)live_spawns[slot]={x=x,y=y};return true end
gd.stage_spawn=function(slot)local s=live_spawns[slot] or{x=12,y=34};return s.x,s.y,0 end
gd.stage_restore_bounds=function()stub_camera=nil;stub_blast=nil;live_spawns={};return true end
local function deep(t)if type(t)~='table'then return t end;local r={};for k,v in pairs(t)do r[k]=deep(v)end;return r end
'''
        self.execute(fixture+stage+'assert(loadfile('+json.dumps(require_game('pc/scripts/examples/map_editor/scripts/main.lua').as_posix())+'))()\n'+r'''
local function command(s)commands.map(s)end
local function count()local n=0;for _ in pairs(models)do n=n+1 end;return n end
command('on');command('ghost off')
'''+body)

    def test_editor_undo_reconciles_removed_spawns_and_bounds(self):
        self.editor(r'''
command('bounds capture');command('spawn 4 -100 0');command('undo')
assert(gd.stage_spawn(4)==12,'undo left the native spawn changed')
command('bounds restore');command('bounds blast -250 250 160 -50')
command('bounds camera -50 50 100 0');command('undo')
assert(stub_camera==nil and stub_blast[1]==-250,'undo left an omitted camera override')
''')

    def test_editor_load_replaces_arena_fields_and_rejects_partial_commit(self):
        self.editor(r'''
command('bounds camera -50 50 100 0');command('spawn 4 -100 0')
files['plain.lua']='return {version=1,units=6.5,parts={}}';command('load plain.lua')
assert(stub_camera==nil and gd.stage_spawn(4)==12,'new layout inherited old arena overrides')
command('place');command('save before.lua')
files['reject.lua']='return {version=2,units=6.5,camera={left=-99,right=99,top=150,bottom=0},parts={}}'
gd.stage_set_camera_bounds=function()error('owned by another script')end
command('load reject.lua');command('save after.lua')
assert(files['before.lua']==files['after.lua'],'refused bounds load partially committed document')
''')

    def test_editor_new_match_reapplies_document_arena(self):
        self.editor(r'''
command('place');command('bounds camera -50 50 100 0');command('spawn 4 -100 0')
on_match_end();models={};stub_camera=nil;live_spawns={};on_match_start()
assert(stub_camera and stub_camera[1]==-50 and gd.stage_spawn(4)==-100,'new match omitted document arena')
''')

    def test_editor_snapshot_does_not_orphan_ghost(self):
        self.editor(r'''
command('ghost on');on_frame_pre();assert(count()==1)
local native_saved=deep(models);on_savestate(1)
command('tool select');on_frame_pre();command('tool place');on_frame_pre()
models=deep(native_saved);on_loadstate(1);command('on');on_frame_pre()
assert(count()==1,'restored placement ghost was orphaned');command('ghost off');assert(count()==0)
''')


if __name__=='__main__': unittest.main()
