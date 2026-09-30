#!/usr/bin/env python3
"""Drive bundled main's real TBD3 save/load seam against v2 route fixtures.

Fixtures are built by the pure modules with an in-memory test-only recipe
admission; the bundled runtime is built from a temporary copy whose
`is_certified` is opened only in that copy. Production certified flags and the
tracked sources are never modified. This exercises main's real dispatcher,
route re-validation, progress persistence and safe refusal, not only Codec.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import prepare

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

# Minimal deterministic engine stub, identical in shape to test_runtime.py's.
PRELUDE = r'''
local last_scene;local files={};local mx,my,mb=-1000,-1000,0; local controls=0; local tick=100;local pause=false;local request=true
local ps={[1]={x=-42,y=0,vx=0,vy=0,stocks=99,percent=0,facing=1,action=14,airborne=false,hitlag=0,costume=0},[2]={x=28,y=0,vx=0,vy=0,stocks=99,percent=0,facing=-1,action=14,airborne=false,hitlag=0,costume=0}}
local models={};local enemies={};local serial=0;local writes=0;local hits=0;local claims={};local masks={};local commands={};local cpu={};local fail_write=false;local fail_hit=false;local refuse_platform=false;local refuse_teleport={};local isolated=false;local refuse_isolation=false
local kit=setmetatable({roles={},row={pitch=36}}, {__index=function() return function() return 1 end end})
gd={buttons={A=256,B=512,UP=8,DOWN=4,LEFT=1,RIGHT=2},kit=kit,
 log=function() end,data_read=function(n)return files[n]end,
 data_write=function(n,s) if fail_write then error('disk full') end files[n]=s;writes=writes+1;return true end,
 command=function(n,f)commands[n]=f end,input=function(p)claims[p]=true end,
 input_mask=function(p,b)masks[p]=b end,release_pad=function(p)claims[p]=nil end,
 tbd_request=function()local v=request;request=false;return v end,
 scene_launch=function(opts)last_scene=opts.p1;assert(opts.mode=='vs','unsupported scene grammar');assert(opts.p2=='fox/c0/cpu9');assert(opts.stocks==99 and opts.items=='off' and opts.time==0,'unbounded/native-scene rules mismatch');tick=0 end,match=function()return {active=true,frame=tick,netplay=false,stage=37}end,
 player=function(p)return ps[p]end,pad=function()return {buttons=controls}end,
 pause=function()pause=true end,resume=function()pause=false end,paused=function()return pause end,
 mouse=function()return mx,my,mb end,
 set_stocks=function(p,n)ps[p].stocks=n end,set_percent=function(p,n)ps[p].percent=n end,
 teleport=function(p,x,y)if refuse_teleport[p] then error('fighter respawning') end ps[p].x=x;ps[p].y=y end,
 model_load=function()serial=serial+1;return serial end,model_spawn=function()serial=serial+1;return serial end,model_despawn=function()return true end,model_release=function()end,
 stage_add_platform=function()if refuse_platform then return nil,'pool exhausted' end serial=serial+1;models[serial]=true;return serial end,
 stage_remove=function(h)models[h]=nil end,
 stage_isolate=function(value)if value~=nil then if value and refuse_isolation then return false end isolated=value end return isolated end,
 spawn_enemy=function(kind,x,y,opts)serial=serial+1;enemies[serial]={kind=kind,x=x,y=y,facing=opts.facing,hits=0,received=0,attack_id=1,damage=0};return serial end,
 enemy_state=function(h)return enemies[h]end,enemy_strike=function()return true end,enemy_hurt=function(h,spec)enemies[h].damage=enemies[h].damage+spec.damage;return true end,
 enemy_remove=function(h)enemies[h]=nil end,enemy_alive=function(h)return enemies[h]~=nil end,cpu_mode=function(p,m)cpu[p]=m;return true end,
 hit=function(p,opts)if fail_hit then return false end hits=hits+1;ps[p].percent=ps[p].percent+opts.damage;return true end,
 impulse=function()return true end,fx_play=function()return 0 end,fx_end=function()end,
 parts_clear=function()end,parts=function()return {geometry_signature='unknown'}end,
 fill=function()end,project=function(x,y)return x+320,240-y end}
'''

FIXTURE_GEN = r'''
local RT=arg[1]
local OUT=arg[2]
local function load(name) return assert(loadfile(RT .. '/' .. name .. '.lua'))() end
local RNG=load('rng'); local Core=load('core'); local RoomCatalogue=load('room_catalogue')
local RoomRecipes=load('room_recipes'); local EncounterCatalogue=load('encounter_catalogue')
local Progression=load('progression'); local Topology=load('topology'); local Progress=load('progress')
local Codec=load('codec'); local Adapter=load('adapter'); local Route=load('route'); local Checkpoint=load('checkpoint')
-- Test-only admission; the production table on disk is untouched.
for _,recipe in pairs(RoomRecipes.recipes) do recipe.certified=true end
local topology=Topology.new(RoomCatalogue,EncounterCatalogue,Progression,RNG)
local adapter=Adapter.new(RoomCatalogue,RoomRecipes)
local routes=Route.new({topology=topology,adapter=adapter,progress=Progress,progression=Progression,encounters=EncounterCatalogue})
local profile=Core.new_profile(90210)
local run=Core.new_run(profile,{stocks=3,seed=4242})
local created=assert(routes:create(run))
local manifest,view,progress=created.manifest,created.view,created.progress
-- Advance so the persisted progress is not a fresh record.
local node=view.nodes[progress.current_room]
progress=assert(routes:travel({manifest=manifest,view=view,progress=progress},assert(node.exits[1])))
run.progress.room=progress.current_room
run.progress.supplies=progress.supplies
run.stocks=progress.lives
local cleared,claimed={},{}
for id,state in pairs(progress.objectives) do if state=='done' then cleared[id]=true end end
for id in pairs(progress.claimed) do local room=id:match('^reward:(.+)$');if room then claimed[room]=true end end
run.progress.cleared,run.progress.claimed=cleared,claimed
assert(routes:validate_save(run,manifest,progress),'fixture route must validate')
local pt=assert(Core.snapshot(profile))
local rt=assert(Core.snapshot(run))
local mt=assert(Codec.encode(manifest))
local prt=assert(Codec.encode(progress))
local roster='ROSTER1 link/c1\nROSTER1 falco/c0\n'
local function enc(gen,m,p,ros) return assert(Checkpoint.encode({generation=gen,profile=pt,run=rt,manifest=m,roster=ros,progress=p})) end
local valid=enc(5,mt,prt,roster)
local noprogress=enc(5,mt,nil,roster)
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
local p1=clone(progress); p1.version=1; p1.opened=nil; p1.pickups=nil; p1.encounter_kos=nil
local p3=clone(progress); p3.version=3
local futureprogress=enc(6,mt,assert(Codec.encode(p3)),roster)
local fg=clone(manifest); fg.generator_version=99
local futuregen=enc(6,assert(Codec.encode(fg)),prt,roster)
local fm=clone(manifest); fm.schema_version=3
local futureman=enc(6,assert(Codec.encode(fm)),prt,roster)
-- Safe migration strips every finite pickup and consumable gate so the schema-1
-- record's missing histories cannot matter; the original route keeps its
-- consumable gate (timed_vault on seed 4242), which makes migration unsafe.
local safeman=clone(manifest)
for _,e in pairs(safeman.edges_by_id) do e.gate_rule=nil end
safeman.locks={}
for _,room in pairs(safeman.rooms_by_id) do room.pickups=nil; room.grants_consumable=nil end
local safe1=enc(5,assert(Codec.encode(safeman)),assert(Codec.encode(p1)),roster)
local unsafe1=enc(5,mt,assert(Codec.encode(p1)),roster)
-- Malformed nested manifest/progress: locks becomes a number and an opened
-- entry makes validate_save index it. topology.validate never inspects locks
-- without a gate, so this reaches the downstream route validator.
local badm=clone(manifest)
for _,e in pairs(badm.edges_by_id) do e.gate_rule=nil end
badm.locks=5
local badp=clone(progress); badp.opened={bogus=true}
local malformed=enc(5,assert(Codec.encode(badm)),assert(Codec.encode(badp)),roster)
local oldvalid=enc(2,mt,prt,roster)
local f=assert(io.open(OUT,'w'))
f:write('return {\n')
f:write('valid='..string.format('%q',valid)..',\n')
f:write('noprogress='..string.format('%q',noprogress)..',\n')
f:write('futureprogress='..string.format('%q',futureprogress)..',\n')
f:write('futuregen='..string.format('%q',futuregen)..',\n')
f:write('futureman='..string.format('%q',futureman)..',\n')
f:write('safe1='..string.format('%q',safe1)..',\n')
f:write('unsafe1='..string.format('%q',unsafe1)..',\n')
f:write('malformed='..string.format('%q',malformed)..',\n')
f:write('oldvalid='..string.format('%q',oldvalid)..',\n')
f:write('roster='..string.format('%q',roster)..',\n')
f:write('}\n')
f:close()
'''

def _copy_and_patch(directory):
    """Copy the runtime sources into an owned temp dir and open test-only hooks.

    Certification is admitted and Route.validate_save can be forced to refuse
    via a global, but only in this throwaway copy; the tracked sources and their
    production flags are never modified.
    """
    directory = Path(directory)
    for path in RT.glob('*.lua'):
        shutil.copyfile(path, directory / path.name)
    recipes = directory / 'room_recipes.lua'
    text = recipes.read_text()
    original = ('function RoomRecipes.is_certified(id)\n'
                '  local r = RoomRecipes.recipes[id]\n'
                '  return r ~= nil and r.certified == true\nend')
    assert original in text, 'room_recipes.lua admission hook moved'
    recipes.write_text(text.replace(original,
        'function RoomRecipes.is_certified(id)\n  return RoomRecipes.recipes[id] ~= nil\nend'))
    route = directory / 'route.lua'
    rtext = route.read_text()
    anchor = 'function Route:validate_save(run, manifest, progress)\n'
    assert anchor in rtext, 'route.lua validate_save anchor moved'
    route.write_text(rtext.replace(anchor,
        anchor + ' if _G.__ROGUE_FORCE_ROUTE_REFUSAL then return false, "forced route refusal" end\n'))
    return directory

WRAPPED = ''

_LOAD = ("local FIX=dofile(arg[1]); local Core=dofile(arg[2]); local Codec=dofile(arg[3]); "
         "local Checkpoint=dofile(arg[4])\n")
_HELPERS = r'''
local function step(b) controls=b or 0;on_tick() end
local function state() return roguelite_state() end
local function click(id)
 local view=state().menu_view;assert(view,'No menu for '..id)
 local found
 for _,c in ipairs(view.controls) do if c.id==id then found=c;break end end
 assert(found,'Missing control '..id)
 mx=found.x+found.w/2;my=found.y+found.h/2;mb=0;step(0);mb=1;step(0);mb=0;step(0);mx=-1000;my=-1000
 for i=1,10 do if not state().loading then break end;step(0) end
 assert(not state().loading)
end
'''

FIXTURES = None
ARGS = []


def run_program(code, args):
    full = PRELUDE + code
    try:
        subprocess.run([LUA, '-', *[str(a) for a in args]], input=full, text=True, check=True)
    except subprocess.CalledProcessError:
        Path('/tmp/roguelite-persistence-failure.lua').write_text(full)
        raise


def scenario(setup, assertions, label):
    run_program(_LOAD + setup + WRAPPED + _HELPERS + assertions, ARGS)


def main():
    global FIXTURES, ARGS, WRAPPED
    with tempfile.TemporaryDirectory(prefix='roguelite-persistence-src-') as src, \
            tempfile.TemporaryDirectory(prefix='roguelite-fixtures-') as temp:
        _copy_and_patch(src)
        WRAPPED = '(function()\n' + prepare.bundle(source=Path(src)) + '\nend)()\n'
        FIXTURES = Path(temp) / 'fixtures.lua'
        subprocess.run([LUA, '-', str(RT), str(FIXTURES)], input=FIXTURE_GEN, text=True, check=True)
        ARGS = [FIXTURES, RT / 'core.lua', RT / 'codec.lua', RT / 'checkpoint.lua']

        # Valid v2: real save/load seam keeps the exact resolved manifest and
        # schema-2 progress, separates selected from running fighter and refuses
        # to start the unwired traversal while retaining the validated route.
        scenario(
            "files={}\nfiles['checkpoint-a.txt']=FIX.valid\nrequest=true;tick=0\n",
            r'''
step();step();tick=91;step()
assert(state().ready and state().menu=='collection','valid v2 route did not load')
assert(state().v2 and state().v2.schema==2 and state().v2.generator==2 and state().v2.progress==2)
assert(state().v2.current=='r002','saved current room was not retained')
assert(state().fighter.id=='link' and state().fighter.costume==1)
assert(state().run_fighter.id=='falco' and state().run_fighter.costume==0)
assert(state().run and state().run.status=='active')
local orig=assert(Checkpoint.decode(FIX.valid,Core,Codec))
local before=files['checkpoint-a.txt']
click('lock')
local changed=files['checkpoint-a.txt']
assert(changed and changed~=before,'a collection save did not write the v2 route')
local back=assert(Checkpoint.decode(changed,Core,Codec,{progress_versions={[2]=true}}))
assert(back.progress and back.progress.version==2)
assert(Codec.encode(back.progress)==Codec.encode(orig.progress),'saved progress was not exact')
assert(Codec.encode(back.manifest)==Codec.encode(orig.manifest),'saved manifest was not exact')
assert(back.roster==FIX.roster and back.run.type=='run')
click('resume')
assert(not state().active,'v2 resume must not start gameplay')
assert(state().menu=='collection','v2 refusal must leave collection review available')
assert(state().toast and state().toast:find('v2 route',1,true),'v2 refusal message missing')
assert(state().v2 and state().v2.current=='r002','validated route state must survive refusal')
on_unload()
print('persistence: valid v2 route loads, separates selected/running fighters, re-saves exact manifest+progress and refuses traversal safely')
''',
            'valid v2')

        # Missing progress on a v2 manifest is an incompatible section, not a
        # legacy or new run; the file is preserved.
        scenario(
            "files={}\nfiles['checkpoint-a.txt']=FIX.noprogress\nrequest=true;tick=0\n",
            r'''
step();step();tick=91;step()
assert(state().menu=='error' and state().save_error,'missing v2 progress must refuse')
assert(files['checkpoint-a.txt']==FIX.noprogress,'refused file must be preserved')
print('persistence: a v2 manifest without progress is refused and preserved')
''',
            'missing progress')

        # Valid older A plus a future inner-schema B: load A, never overwrite B.
        scenario(
            "files={}\nfiles['checkpoint-a.txt']=FIX.oldvalid\nfiles['checkpoint-b.txt']=FIX.futureprogress\nrequest=true;tick=0\n",
            r'''
step();step();tick=91;step()
assert(state().ready and state().v2 and state().v2.current=='r002','older valid v2 route did not load')
assert(files['checkpoint-b.txt']==FIX.futureprogress,'future inner-schema file lost during load')
click('lock')
assert(files['checkpoint-b.txt']==FIX.futureprogress,'future inner-schema file overwritten by save')
assert(files['checkpoint-a.txt']~=FIX.oldvalid,'replacement checkpoint was not redirected')
local back=assert(Checkpoint.decode(files['checkpoint-a.txt'],Core,Codec,{progress_versions={[2]=true}}))
assert(back.progress and back.progress.version==2)
print('persistence: valid older A loads while a future inner-schema B stays byte-identical')
''',
            'future inner schema')

        # A future generator version inside a schema-2 envelope is preserved and
        # never mistaken for the current generator.
        scenario(
            "files={}\nfiles['checkpoint-a.txt']=FIX.oldvalid\nfiles['checkpoint-b.txt']=FIX.futuregen\nrequest=true;tick=0\n",
            r'''
step();step();tick=91;step()
assert(state().ready and state().v2,'older valid route did not load past a future generator')
assert(files['checkpoint-b.txt']==FIX.futuregen,'future-generator file lost during load')
click('lock')
assert(files['checkpoint-b.txt']==FIX.futuregen,'future-generator file overwritten by save')
assert(files['checkpoint-a.txt']~=FIX.oldvalid,'replacement checkpoint was not redirected')
print('persistence: a future generator version is preserved, not adopted or overwritten')
''',
            'future generator')

        # A future manifest schema is refused by the decoder's explicit gate.
        scenario(
            "files={}\nfiles['checkpoint-a.txt']=FIX.oldvalid\nfiles['checkpoint-b.txt']=FIX.futureman\nrequest=true;tick=0\n",
            r'''
step();step();tick=91;step()
assert(state().ready and state().v2,'older valid route did not load past a future manifest schema')
assert(files['checkpoint-b.txt']==FIX.futureman,'future-manifest file lost during load')
click('lock')
assert(files['checkpoint-b.txt']==FIX.futureman,'future-manifest file overwritten by save')
assert(files['checkpoint-a.txt']~=FIX.oldvalid,'replacement checkpoint was not redirected')
print('persistence: a future manifest schema is preserved, not adopted or overwritten')
''',
            'future manifest schema')

        # Schema-1 migration is unsafe when the route has finite pickups or
        # consumable gates: preserve/refuse instead of inventing empty claims.
        scenario(
            "files={}\nfiles['checkpoint-a.txt']=FIX.unsafe1\nrequest=true;tick=0\n",
            r'''
step();step();tick=91;step()
assert(state().menu=='error' and state().save_error,'unsafe schema-1 migration must refuse')
assert(files['checkpoint-a.txt']==FIX.unsafe1,'unsafe migration file must be preserved')
print('persistence: schema-1 migration is refused when pickup/lock history would be invented')
''',
            'unsafe migration')

        # Genuinely safe schema-1 migration: no finite pickups or consumable
        # gates exist, so an empty-map upgrade loses nothing.
        scenario(
            "files={}\nfiles['checkpoint-a.txt']=FIX.safe1\nrequest=true;tick=0\n",
            r'''
step();step();tick=91;step()
assert(state().ready and state().v2 and state().v2.progress==2,'safe schema-1 migration did not load')
assert(files['checkpoint-a.txt']==FIX.safe1,'load must not rewrite the file')
click('lock')
local back=assert(Checkpoint.decode(files['checkpoint-a.txt'],Core,Codec,{progress_versions={[2]=true}}))
assert(back.progress.version==2 and back.progress.opened and back.progress.pickups and back.progress.encounter_kos)
print('persistence: safe schema-1 progress migrates explicitly and persists as schema 2')
''',
            'safe migration')

        # Staged validation: a forced semantic refusal and a forced device failure
        # must both leave the last usable slot, the protected sibling and live
        # in-memory mirrors exactly intact.
        scenario(
            "files={}\nfiles['checkpoint-a.txt']=FIX.valid\nfiles['checkpoint-b.txt']=FIX.futureprogress\nrequest=true;tick=0\n",
            r'''
step();step();tick=91;step()
assert(state().ready and state().v2,'valid route did not load for the save-failure cases')
local before_a,before_b=files['checkpoint-a.txt'],files['checkpoint-b.txt']
local room0,supp0,lives0=state().run.progress.room,state().run.progress.supplies,state().run.stocks
__ROGUE_FORCE_ROUTE_REFUSAL=true
click('lock')
assert(state().toast and state().toast:find('previous checkpoint retained',1,true),'forced refusal message missing')
assert(files['checkpoint-a.txt']==before_a,'refused save overwrote the last usable slot')
assert(files['checkpoint-b.txt']==before_b,'refused save touched the protected sibling')
assert(state().run.progress.room==room0 and state().run.progress.supplies==supp0 and state().run.stocks==lives0,'refused save altered live mirrors')
__ROGUE_FORCE_ROUTE_REFUSAL=false
fail_write=true
click('lock')
fail_write=false
assert(state().toast and state().toast:find('write/readback failed',1,true),'forced write-failure message missing')
assert(files['checkpoint-a.txt']==before_a,'failed write overwrote the last usable slot')
assert(files['checkpoint-b.txt']==before_b,'failed write touched the protected sibling')
assert(state().run.progress.room==room0 and state().run.progress.supplies==supp0 and state().run.stocks==lives0,'failed write altered live mirrors')
print('persistence: forced refusal and write failure keep the last usable slot, protected sibling and live mirrors intact')
''',
            'staged save failures')

        # Malformed nested route data is contained at the load boundary.
        scenario(
            "files={}\nfiles['checkpoint-a.txt']=FIX.malformed\nrequest=true;tick=0\n",
            r'''
step();step();tick=91;step()
assert(state().menu=='error' and state().save_error,'malformed nested route must refuse')
assert(files['checkpoint-a.txt']==FIX.malformed,'malformed file must be preserved')
print('persistence: malformed nested route data is contained as controlled refusal')
''',
            'malformed nested')

        # A torn newest v2 slot falls back to the older complete generation.
        scenario(
            "files={}\nfiles['checkpoint-a.txt']=FIX.valid\nfiles['checkpoint-b.txt']=FIX.valid:sub(1,#FIX.valid-6)\nrequest=true;tick=0\n",
            r'''
step();step();tick=91;step()
assert(state().ready and state().v2,'torn newest v2 save did not fall back to the older slot')
print('persistence: a torn newest v2 checkpoint falls back to the older valid generation')
''',
            'torn newest')

    print('persistence: bundled main real save/load seam scenarios passed')


main()
