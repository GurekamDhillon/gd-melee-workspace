import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
import shutil
from unittest import mock
import contextlib
import io
HERE=Path(__file__).parent

def module(name):
    spec=importlib.util.spec_from_file_location(name,HERE/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
run=module('run');compare=module('compare')

class HarnessTests(unittest.TestCase):
    def test_admission_fallback_uses_fresh_sandbox_without_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            shutil.copytree(run.ROOT/'melee/pc/scripts/examples/bench',root/'melee/pc/scripts/examples/bench')
            iso=root/'synthetic.iso';iso.write_bytes(b'synthetic runner fixture, not a disc')
            commands=[]
            def execute(command,env,directory,timeout):
                commands.append(command);(directory/'profile.json').write_text('{}')
                return (0 if directory.name.endswith('a1') else 1),{}
            def status(directory):return {'complete':directory.name.endswith('a1'),'frames':10,'roster':[]}
            with mock.patch.object(run,'ROOT',root),mock.patch.object(run,'prepare_mission'),mock.patch.object(run,'execute',execute),mock.patch.object(run,'read_status',status),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run.main(['steady_worst','--iso',str(iso),'--frames','10']),0)
            self.assertEqual(len(commands),2)
            self.assertNotEqual(commands[0][3],commands[1][3])
            self.assertIn('--realtime',commands[0]);self.assertNotIn('--test',commands[0])
    def test_legacy_percentiles(self):
        stats=run.legacy_metrics([{'logic_ms':n} for n in range(1,101)])['logic_ms']
        self.assertEqual(stats['p95'],95);self.assertEqual(stats['max'],100)
    def test_event_trace_preservation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=root/'script-data/bench';data.mkdir(parents=True)
            (data/'status.json').write_text(json.dumps({'trace_capture':{'sequence':1,'feature':'shader_bloom','logic_frame':40}}))
            (root/'trace.json').write_text(json.dumps({'traceEvents':[{'name':'frame','ph':'X','dur':25000,'args':{'frame':42}}]}))
            copied={};run.capture_event_trace(root,copied)
            self.assertEqual(copied[1]['worst_cpu_frame_ms'],25)
            self.assertTrue((root/copied[1]['trace']).exists())
    def test_scripted_physical_and_virtual_scene(self):
        value=run.scene(['fox']*6,{'mode':'lab'})
        self.assertIn('p4=fox/hu',value);self.assertIn('p5=fox/cpu9',value)
        self.assertNotIn('cpu0',value)
    def test_invalid_roster(self):
        for roster in (['fox'],['fox']*7,['fox;mode=title','marth']):
            with self.assertRaises(ValueError):run.scene(roster,{})
    def test_visible_paced_and_seeded(self):
        env=run.environment({'roster':['fox','marth'],'seed':23},Path('out'),Path('script'),True,
                            {'MELEE_TURBO':'1','MELEE_HEADLESS':'1','MELEE_WINDOW_HIDE':'1','MELEE_PAD_SCRIPT':'stale'})
        self.assertEqual(env['MELEE_TURBO'],'0');self.assertEqual(env['MELEE_TEST_SEED'],'23')
        self.assertEqual(env['MELEE_WINDOW_X'],'-1080');self.assertLessEqual(int(env['MELEE_WINDOW_W']),1080)
        self.assertEqual(env['MELEE_WINDOW_HIDE'],'0');self.assertNotIn('MELEE_HEADLESS',env);self.assertNotIn('MELEE_PAD_SCRIPT',env)
    def test_no_env_override_of_pacing(self):
        with self.assertRaises(ValueError):run.environment({'roster':['fox','marth'],'seed':1,'env':{'MELEE_TURBO':1}},Path('o'),Path('s'),True,{})
    def test_inherited_forced_rollback_removed(self):
        env=run.environment({'roster':['fox','marth'],'seed':1},Path('o'),Path('s'),True,{'MELEE_SYNCTEST_BENCH':'1','MELEE_SYNCTEST':'12'})
        self.assertNotIn('MELEE_SYNCTEST_BENCH',env);self.assertNotIn('MELEE_SYNCTEST',env)
    def test_baseline_removes_inherited_workload_and_normalizes_video(self):
        inherited={'MELEE_RENDER_SCALE':'8','MELEE_MSAA':'4','MELEE_SLP':'capture.slp',
                   'MELEE_NETPLAY':'host','MELEE_SHADER_TEST':'1','MELEE_TRAINING':'fox',
                   'MELEE_BACKEND':'d3d12','PATH':'test'}
        env=run.environment({'roster':['fox','marth'],'seed':1},Path('o'),Path('s'),True,inherited)
        self.assertEqual(env['MELEE_RENDER_SCALE'],'1');self.assertEqual(env['MELEE_MSAA'],'1')
        self.assertEqual(env['MELEE_BACKEND'],'d3d12');self.assertEqual(env['PATH'],'test')
        for key in ('MELEE_SLP','MELEE_NETPLAY','MELEE_SHADER_TEST','MELEE_TRAINING'):self.assertNotIn(key,env)
    def test_workload_identity_controls_and_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle=Path(temp);(bundle/'main.lua').write_text('return 1')
            config={'roster':['fox','marth'],'seed':1,'setup':[],'events':[]}
            env=run.environment(config,Path('a'),bundle,True,{})
            base,_=run.workload_identity(config,env,bundle)
            off=run.environment(config,Path('b'),bundle,False,{})
            self.assertEqual(base,run.workload_identity(config,off,bundle)[0])
            for key,value in [('MELEE_RENDER_SCALE','8'),('MELEE_MSAA','4')]:
                changed=dict(env);changed[key]=value
                self.assertNotEqual(base,run.workload_identity(config,changed,bundle)[0])
            altered=dict(config);altered['events']=[{'frame':20,'api':'savestate','args':[1]}]
            self.assertNotEqual(base,run.workload_identity(altered,env,bundle)[0])
            (bundle/'main.lua').write_text('return 2')
            self.assertNotEqual(base,run.workload_identity(config,env,bundle)[0])
    def test_off_profile(self):
        env=run.environment({'roster':['fox','marth'],'seed':1},Path('o'),Path('s'),False,{})
        self.assertEqual(env['MELEE_PROFILER'],'0')
    def test_lua_config_escaping(self):
        self.assertIn('\\010',run.lua({'a':'x\ny"'}));self.assertIn('true',run.lua([True]))
    def test_summary_off_missing_metrics(self):
        report={'bench':{'status':{'complete':True,'frames':10},'scenario':'baseline','profiler':False,'seed':1}}
        self.assertIn('complete=True',run.summarize(report))
    def test_scenarios_extensible_and_requests_honest(self):
        for path in (HERE/'scenarios').glob('*.json'):
            cfg=json.loads(path.read_text());run.scene(cfg['roster'],cfg)
        cfg=json.loads((HERE/'scenarios/steady_worst.json').read_text())
        self.assertEqual(len(cfg['roster']),6);self.assertTrue(cfg['fallback_rosters'])

class CompareTests(unittest.TestCase):
    budgets={'zones':{'logic':4.75},'absolute_tolerance_ms':0.02}
    def report(self,n):return {'zones':{'logic':{'p95':n}}}
    def test_identical_failed_runs_rejected(self):
        for status,rc,error in [({'complete':False,'frames':10},0,None),({'complete':True,'frames':9},0,None),({'complete':True,'frames':10},1,None),({'complete':True,'frames':10},0,'profile missing')]:
            a=self.report(3);a['bench']={'status':status,'exit_code':rc,'requested_frames':10,'profile_error':error}
            self.assertTrue(compare.compare(a,a,self.budgets)[1])
    def test_complete_reports_allowed(self):
        a=self.report(3);a['bench']={'status':{'complete':True,'frames':10},'exit_code':0,'requested_frames':10,'workload_fingerprint':'same-workload'}
        self.assertFalse(compare.compare(a,a,self.budgets)[1])
    def test_equal_metrics_different_effective_workloads_rejected(self):
        a,b=self.report(3),self.report(3)
        valid={'status':{'complete':True,'frames':10},'exit_code':0,'requested_frames':10}
        a['bench']={**valid,'workload_fingerprint':'scale1-msaa1-no-events'}
        b['bench']={**valid,'workload_fingerprint':'scale8-msaa4-savestate-event'}
        self.assertIn('incomparable bench field: workload_fingerprint',compare.compare(a,b,self.budgets)[1])
    def test_improvement(self):self.assertFalse(compare.compare(self.report(4),self.report(3),self.budgets)[1])
    def test_regression(self):self.assertTrue(compare.compare(self.report(3),self.report(3.3),self.budgets)[1])
    def test_budget_overrun(self):self.assertTrue(compare.compare(self.report(5),self.report(5),self.budgets)[1])
    def test_missing_budgeted_zone(self):self.assertTrue(compare.compare(self.report(3),{'zones':{}},self.budgets)[1])
    def test_small_noise(self):self.assertFalse(compare.compare(self.report(0),self.report(0.01),self.budgets)[1])
    def test_incomparable_roster_backend_features(self):
        for key in ('actual_roster','backend','feature_statuses','mods_fingerprint'):
            a,b=self.report(3),self.report(3);a['bench']={key:'a'};b['bench']={key:'b'}
            self.assertTrue(compare.compare(a,b,self.budgets)[1])
    def test_incomparable_seed(self):
        a,b=self.report(3),self.report(3);a['bench']={'seed':1};b['bench']={'seed':2}
        self.assertTrue(compare.compare(a,b,self.budgets)[1])

if __name__=='__main__':unittest.main()
