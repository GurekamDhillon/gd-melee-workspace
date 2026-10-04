"""Seed/sweep fixtures use synthetic SQLite and Lua stubs; never run the game."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import shutil
import tempfile
import unittest
import build_pipeline_seed as seed
import pipeline_seed_sweep as sweep

class SeedTests(unittest.TestCase):
    def cache(self, path, rows, tags=(), origins=(), version=1):
        with closing(sqlite3.connect(path)) as db:
            db.executescript('CREATE TABLE aurora_schema(value INTEGER); CREATE TABLE pipeline_cache(type INTEGER,hash INTEGER,config_version INTEGER,config_size INTEGER,config BLOB,first_frame_used INTEGER,PRIMARY KEY(type,hash)); CREATE TABLE pipeline_tags(type INTEGER,hash INTEGER,tags INTEGER,PRIMARY KEY(type,hash)); CREATE TABLE pipeline_origins(type INTEGER,hash INTEGER,origin TEXT,PRIMARY KEY(type,hash,origin));')
            db.execute('INSERT INTO aurora_schema VALUES (?)',(version,))
            db.executemany('INSERT INTO pipeline_cache VALUES (?,?,?,?,?,?)',rows)
            db.executemany('INSERT INTO pipeline_tags VALUES (?,?,?)',tags)
            db.executemany('INSERT INTO pipeline_origins VALUES (?,?,?)',origins)
            db.commit()
    def test_merge_deduplicates_sources_and_carries_tags_origins(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=root/'a.db';b=root/'b.db';out=root/'seed.db'
            self.cache(a,[(1,10,1,1,b'a',50)],[(1,10,1)],[(1,10,'enemy:goomba')])
            self.cache(b,[(1,10,1,1,b'a',2),(1,20,1,1,b'b',1)],[(1,10,2)],[(1,10,'item:0')])
            stats=seed.merge_caches([a,a,b],out)
            self.assertEqual(stats['runs'],2)
            with closing(sqlite3.connect(out)) as db:
                self.assertEqual(db.execute('SELECT tags FROM pipeline_tags').fetchone()[0],3)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM pipeline_origins').fetchone()[0],2)
                self.assertEqual(db.execute('SELECT hash FROM pipeline_cache ORDER BY first_frame_used').fetchall(),[(10,),(20,)])
    def test_empty_or_incompatible_input_preserves_existing_seed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'seed.db';out.write_bytes(b'previous')
            empty=root/'empty.db';self.cache(empty,[])
            with self.assertRaises(ValueError):seed.merge_caches([empty],out)
            self.assertEqual(out.read_bytes(),b'previous')
    def test_schema_mismatch_and_legacy_metadata_are_handled(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=root/'a.db';b=root/'b.db';out=root/'seed.db'
            self.cache(a,[(1,10,1,1,b'a',5)])
            self.cache(b,[(1,20,1,1,b'b',1)],version=2)
            with closing(sqlite3.connect(a)) as db:
                db.execute('DROP TABLE pipeline_tags');db.execute('DROP TABLE pipeline_origins');db.commit()
            result=seed.merge_caches([a,b],out)
            self.assertEqual(result['pipelines'],1);self.assertEqual(result['runs'],1)
            self.assertEqual(result['origins'],0);self.assertEqual(out.with_suffix('.core').read_text(),'1\n')

    def test_explicit_db_and_recursive_root_discovery(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);nested=root/'runs'/'a';nested.mkdir(parents=True)
            db=nested/'pipeline_cache.db';db.touch()
            self.assertEqual(seed.discover_sources([db,root],include_default=False),[db.resolve()])

class SweepTests(unittest.TestCase):
    def test_dynamic_stage_roster_and_item_manifest(self):
        plan=sweep.make_plan('ace','stage tables ready: 100 internal, 291 external', [0,34,237,'pickup'],24)
        self.assertEqual(len(plan['runs']),34)
        self.assertIn('stage=ext:290',plan['runs'][-1]['scene'])
        self.assertEqual(plan['enemies'],['goomba','koopa','redead','like_like','octorok','polar_bear','topi'])
        self.assertEqual(plan['items'],[0,34,237,'pickup'])
        self.assertTrue(plan['stage_roster_complete'])
        self.assertFalse(plan['item_roster_complete'])
        self.assertIn('gd.item_kinds',sweep.driver(plan))
    def test_missing_discovery_never_claims_full_coverage(self):
        plan=sweep.make_plan('ace','',[],24)
        self.assertFalse(plan['stage_roster_complete'])
        self.assertFalse(plan['item_roster_complete'])
    def test_invalid_item_is_rejected(self):
        with self.assertRaises(ValueError):sweep.make_plan('vanilla','',[-1],24)
    def test_export_is_only_files_and_driver_spawns_each_kind(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);plan=sweep.make_plan('vanilla','',[0,237],24)
            sweep.export_plan(plan,root)
            driver=(root/'mods'/'pipeline-sweep'/'scripts'/'main.lua').read_text()
            self.assertIn('gd.spawn_enemy',driver);self.assertIn('gd.item_spawn',driver)
            self.assertIn('gd.warm_done',driver)
            self.assertEqual(len(json.loads((root/'plan.json').read_text())['runs']),31)

class LuaTests(unittest.TestCase):
    def lua(self,text,*args):
        lua=shutil.which('lua');self.assertIsNotNone(lua,'Lua required')
        subprocess.run([lua,'-',*map(str,args)],input=text,text=True,check=True,cwd=seed.ROOT)
    def test_demo_waits_then_spawns_once_and_releases(self):
        path=seed.ROOT/'melee/pc/scripts/examples/demos/warm/scripts/main.lua'
        self.lua(r"""
local gd,S=dofile('tools/port/demo_gd_stub.lua')
local env=setmetatable({gd=gd},{__index=_G})
assert(loadfile(arg[1],'t',env))()
local function enemies() local n=0;for _,r in pairs(S.resources) do if r.kind=='enemy' then n=n+1 end end;return n end
assert(env.on_match_start);env.on_match_start()
for i=0,6 do S.frame=i;env.on_tick();assert(enemies()==0,'spawn before warm completion') end
S.frame=7;env.on_tick();assert(enemies()==1,'ready did not spawn')
for i=8,20 do S.frame=i;env.on_tick();assert(enemies()==1,'duplicate spawn') end
assert(S.players[2].cpu_mode=='stand')
env.on_unload();assert(next(S.resources)==nil,'owned handles leaked')
-- Failed warm must release the job and never spawn.
assert(loadfile(arg[1],'t',env))();S.warm_failure=true;env.on_match_start();env.on_tick()
assert(enemies()==0);env.on_unload();assert(next(S.resources)==nil)
print('warm demo wait/once/failure/cleanup PASS')
""",path)
    def test_generated_driver_enumerates_after_enemy_warm_and_skips_unsafe_spawn(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'driver.lua';path.write_text(sweep.driver(sweep.make_plan('vanilla','',[],24)))
            self.lua(r"""
local tick,serial,done,enumerated=0,0,false,false
local jobs,enemies,items={},0,0
local g={}
function g.match() return {active=true} end
function g.player() return nil end
function g.cpu_mode() end
function g.log(message) if message=='pipeline sweep complete' then done=true end end
function g.warm(spec) serial=serial+1;jobs[serial]=tick+3;return serial end
function g.warm_done(h) return tick>=jobs[h],nil end
function g.warm_release(h) jobs[h]=nil end
function g.spawn_enemy() assert(tick>=3);enemies=enemies+1;return enemies end
function g.enemy_remove() end
function g.item_kinds() assert(enemies==7,'enumeration before enemy preload/spawn coverage');enumerated=true;return {{kind=0,name='vanilla:0',spawnable=true},{kind=35,name='vanilla:35',spawnable=false},{kind=237,name='mex:237',spawnable=true}} end
function g.item_spawn(name) assert(enumerated and name~='vanilla:35');items=items+1;return items end
function g.item_despawn() end
local env=setmetatable({gd=g},{__index=_G});assert(loadfile(arg[1],'t',env))()
for i=1,1000 do tick=i;env.on_frame();if done then break end end
assert(done and enemies==7 and items==2,'incomplete coverage')
env.on_unload();assert(next(jobs)==nil,'warm handles leaked')
print('sweep ordered discovery/spawnable-only PASS')
""",path)

if __name__=='__main__':unittest.main()
