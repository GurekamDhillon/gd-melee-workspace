#!/usr/bin/env python3
"""Export crash_sweep's stage roster plus deterministic enemy/item spawn driver.
No execution API is provided. Boot-log counts and a runtime item roster must be
supplied for complete custom coverage; an absent roster is explicitly incomplete.
"""
import importlib.util
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
ENEMIES=['goomba','koopa','redead','like_like','octorok','polar_bear','topi']


def make_plan(disc,probe_log,items,seconds):
    if disc not in ('vanilla','ace','akaneia'):raise ValueError('unknown disc')
    if seconds<1:raise ValueError('seconds must be positive')
    match=re.findall(r'stage tables ready: (\d+) internal, (\d+) external',probe_log)
    external=int(match[-1][1]) if match else 0
    if external>5000:raise ValueError('implausible external stage count')
    unique=[]
    for item in items:
        if isinstance(item,dict):item=item.get('kind',item.get('name'))
        if isinstance(item,bool) or not isinstance(item,(str,int)) or (isinstance(item,int) and not 0<=item<5000) or (isinstance(item,str) and not item):
            raise ValueError('invalid runtime item identity')
        if item not in unique:unique.append(item)
    spec=importlib.util.spec_from_file_location('pipeline_crash_sweep',ROOT/'tools/sweep/crash_sweep.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    runs=module.plan(disc,0,external,'stages',seconds,'off')
    return dict(version=1,disc=disc,enemies=ENEMIES.copy(),items=unique,
                stage_roster_complete=disc=='vanilla' or bool(match),item_roster_complete=False,
                item_discovery="gd.item_kinds() after enemy warm preloads; native evidence required",
                runs=[dict(tag=run.tag,scene=run.scene.replace('mode=vs','mode=training'),seconds=seconds) for run in runs],
                evidence='Plan only. Spawn refusals, missing descriptors, and timeouts are coverage failures; inspect per-run logs.')


def driver(plan):
    # JSON strings/arrays are valid Lua strings when escaped; list syntax differs.
    def array(values):return '{'+','.join(json.dumps(v,ensure_ascii=True) for v in values)+'}'
    return """-- Generated pipeline coverage driver; enumeration occurs after enemy preloads.
local enemies=ENEMIES
local phase,index,timer,enemy,item,warm,rows,batch_end=0,1,0,nil,nil,nil,{},0
local function cleanup()
  if enemy then gd.enemy_remove(enemy);enemy=nil end
  if item then gd.item_despawn(item);item=nil end
end
local function poll()
  local done,why=gd.warm_done(warm)
  if why then
    gd.log('pipeline sweep FAIL discovery',phase,index,tostring(why))
    gd.warm_release(warm);warm=nil;return true
  end
  if not done then return false end
  gd.warm_release(warm);warm=nil;return true
end
function on_frame()
  if not gd.match().active or phase==5 then return end
  for port=1,6 do local p=gd.player(port);if p and p.cpu then gd.cpu_mode(port,'stand') end end
  if phase==0 then
    if not warm then warm=gd.warm{enemies=enemies};gd.log('pipeline sweep enemy discovery');return end
    if not poll() then return end
    phase,index,timer=1,1,30;return
  end
  if phase==1 then
    timer=timer+1;if timer<30 then return end
    cleanup()
    local value=enemies[index]
    if not value then
      rows=gd.item_kinds();gd.log('pipeline sweep runtime item kinds',#rows)
      phase,index=2,1;return
    end
    local why;enemy,why=gd.spawn_enemy(value,20,12)
    gd.log(enemy and 'pipeline sweep enemy spawned' or 'pipeline sweep FAIL enemy spawn',value,tostring(why))
    index=index+1;timer=0;return
  end
  if phase==2 then
    if warm then if not poll() then return end;index=batch_end+1 end
    if index>#rows then phase,index,timer=3,1,30;return end
    local names={};batch_end=math.min(index+127,#rows)
    for i=index,batch_end do names[#names+1]=rows[i].name end
    warm=gd.warm{items=names};return
  end
  if phase==3 then
    timer=timer+1;if timer<30 then return end
    cleanup()
    local row=rows[index]
    if not row then phase=5;gd.log('pipeline sweep complete');return end
    if row.spawnable then
      local why;item,why=gd.item_spawn(row.name,20,18)
      gd.log(item and 'pipeline sweep item spawned' or 'pipeline sweep FAIL item spawn',row.name,tostring(why))
      timer=0
    else gd.log('pipeline sweep item warmed only: owning context required',row.name) end
    index=index+1
  end
end
function on_unload() cleanup();if warm then gd.warm_release(warm) end end
""".replace('ENEMIES',array(plan['enemies']))



def export_plan(plan,output):
    output=Path(output);scripts=output/'mods/pipeline-sweep/scripts';scripts.mkdir(parents=True,exist_ok=True)
    (scripts/'main.lua').write_text(driver(plan),encoding='utf-8')
    manifest=dict(id='pipeline-sweep',name='Pipeline coverage sweep',version='0.1.0',kind='script',api_version=1,gameplay=True,rollback_safe=False,entry='scripts/main.lua')
    (scripts.parent/'mod.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (output/'README.md').write_text('''# Generated pipeline coverage plan

No game was started. Run every plan.json scene with the generated mods parent
as MELEE_MODS_DIR. Keep each sandbox pipeline_cache.db, merge the resulting
runs with build_pipeline_seed.py, and retain the logs as coverage evidence.
Each driver warms all seven enemies before discovering gd.item_kinds(). It
warms registered item descriptors in batches of 128 and spawns only kinds
marked spawnable. Unsafe fighter/stage articles are explicitly warmed-only;
this is descriptor coverage, not full owning-context draw coverage.
Allow every driver to log `pipeline sweep complete`; the plan seconds is a
starting duration, not evidence of completion. Poll compilation rather than
using a fixed timeout as success. FAIL spawn/discovery lines invalidate that
kind; fighter/stage-only articles may require their owning context instead.
Runtime-provided custom stage counts are passed to crash_sweep.plan, avoiding
its CLI --plan default of zero custom stages. Missing roster flags mean this
plan cannot certify exhaustive coverage. Use one fresh scene per stage.
''')
