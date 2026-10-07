"""Validate the demo catalogue against live source; never build or launch the game.

Run: python tools/port/test_demo_mods.py
Static call validation includes references passed to pcall and nested gd.kit methods.
The named Lua prelude helpers are source registrations too, not C luaL_Reg rows.
"""
from pathlib import Path
import argparse
import json
import re
import shutil
import subprocess
import unittest
import tempfile
import io
from types import SimpleNamespace
import time
import struct
import zlib
from tools.test_support import GAME, require_game
from contextlib import redirect_stdout
from unittest.mock import patch


class TourSafetyTests(unittest.TestCase):
    def test_boot_mount_is_one_demo_without_boot_scripts(self):
        require_game('pc/scripts/examples/demos/catalogue.json')
        import demo_tour
        rows=json.loads(CATALOGUE.read_text())
        row=next(r for r in rows if r['id']=='demo_effects')
        with tempfile.TemporaryDirectory() as tmp:
            mods=demo_tour.prepare_mods([row],Path(tmp))
            self.assertEqual((mods/'enabled.txt').read_text().strip(),'demo_effects')
            self.assertFalse(list(mods.rglob('scripts')),'mounted demo must not boot a second script')
            self.assertFalse((mods/'demo_gauntlet').exists())

    def test_png_must_decode_pixels_not_just_verify_chunks(self):
        import demo_tour
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'shot.png'; Image.new('RGB',(32,32)).save(path)
            demo_tour.wait_file(path,timeout=.1)
            with patch('PIL.Image.Image.load',side_effect=OSError('truncated pixels')):
                with self.assertRaises(TimeoutError): demo_tour.wait_file(path,timeout=.01)
            data=path.read_bytes(); offset=8
            while offset<len(data):
                size=struct.unpack('>I',data[offset:offset+4])[0]
                if data[offset+4:offset+8]==b'IDAT':
                    payload=b'IDAT'+b'bad zlib data'
                    data=data[:offset]+struct.pack('>I',len(payload)-4)+payload+struct.pack('>I',zlib.crc32(payload)&0xffffffff)+data[offset+12+size:]
                    break
                offset+=12+size
            path.write_bytes(data)
            with Image.open(path) as image: image.verify()  # CRC is valid; pixels are not.
            with self.assertRaises(TimeoutError): demo_tour.wait_file(path,timeout=.02)

    def test_tour_is_silent_and_has_behavior_scenarios_for_every_new_mod(self):
        require_game('pc/scripts/examples/demos/catalogue.json')
        import demo_tour
        from demo_scenarios import SCENARIOS
        env=demo_tour.tour_environment(Path('out'),Path('mods'),51707)
        self.assertEqual(env['MELEE_VOLUME'],'0')
        self.assertTrue(env['MELEE_RUN_OWNER'])
        rows=json.loads(CATALOGUE.read_text())
        for row in rows:
            if row.get('new'):
                self.assertIn(row['id'],SCENARIOS)
                steps=SCENARIOS[row['id']]
                self.assertTrue(any(s[0] in ('assert','probe') for s in steps),row['id'])

    def test_scenario_assertions_and_owner_state_are_required(self):
        import demo_tour
        import demo_scenarios
        for state,answer,passes in [('false','ASSERT PASS',True),('true','ASSERT PASS',False),('false','false',False)]:
            with self.subTest(state=state,answer=answer), tempfile.TemporaryDirectory() as tmp:
                out=Path(tmp); sandbox=out/'native'; sandbox.mkdir()
                commands=[]
                client=SimpleNamespace(sock=SimpleNamespace(settimeout=lambda n:None))
                def command(line):
                    commands.append(line)
                    if line.startswith('demo_state '):
                        token=line.split(' ',1)[1]
                        (sandbox/'melee-pc.log').write_text('tour state '+token+' '+state+' | toggle\n')
                    return [answer]
                client.command=command
                steps=[('k','K',0),('probe','^false'),('assert','true')]
                with patch.dict(demo_scenarios.SCENARIOS,{'fixture':steps}):
                    if passes:
                        result=demo_tour.run_scenario({'id':'fixture'},client,out,sandbox,time.monotonic()+1,'private.iso','alias.iso')
                        self.assertEqual(result['status'],'PASS')
                        self.assertEqual(result['steps'],3)
                    else:
                        with self.assertRaises(RuntimeError):
                            demo_tour.run_scenario({'id':'fixture'},client,out,sandbox,time.monotonic()+1,'private.iso','alias.iso')
                self.assertIn('demo_key K',commands)

    def test_all_scenario_api_calls_are_registered(self):
        from demo_scenarios import SCENARIOS
        names=registered_api()
        for ident,steps in SCENARIOS.items():
            for step in steps:
                if step[0] in ('e','assert','c'):
                    for name in lua_calls(step[1]):
                        self.assertIn('gd.'+name,names,ident+' '+name)

    def test_weak_demo_defaults_are_deliberately_visible(self):
        base=require_game('pc/scripts/examples/demos/post-bloom/scripts/main.lua').parents[2]
        bloom=(base/'post-bloom/scripts/main.lua').read_text()
        outline=(base/'post-outline/scripts/main.lua').read_text()
        self.assertIn('threshold=0.2,intensity=4,radius=4',bloom)
        self.assertIn('width=4,threshold=0.002,strength=1',outline)
        self.assertIn('params={3}',(base/'surface-fighter/scripts/main.lua').read_text())
        parts=(base/'parts/scripts/main.lua').read_text()
        self.assertIn('0xff10dfff',parts)
        self.assertNotIn('break end',parts.split('for _,part in ipairs(parts) do')[1].split('\n')[0])
    def test_plan_never_contains_private_disc_in_either_slash_form(self):
        require_game('pc/scripts/examples/demos/catalogue.json')
        import demo_tour
        with tempfile.TemporaryDirectory() as tmp:
            iso = Path(tmp)/'private-disc.iso'
            iso.write_text('fixture, not a game disc')
            output = Path(tmp)/'results'
            stream = io.StringIO()
            with patch('sys.argv', ['demo_tour', '--iso', str(iso), '--output', str(output), '--plan']), redirect_stdout(stream):
                self.assertEqual(demo_tour.main(), 0)
            for variant in (str(iso.resolve()), str(iso.resolve()).replace('\\','/')):
                self.assertNotIn(variant, stream.getvalue())
                self.assertNotIn(json.dumps(variant)[1:-1], stream.getvalue())
            self.assertIn('<disc>', stream.getvalue())

    def test_window_dimensions_and_unattended(self):
        import demo_tour
        with patch.dict('os.environ', {'MELEE_WINDOW_W':'960','MELEE_WINDOW_H':'540'}):
            env = demo_tour.tour_environment(Path('out'), Path('mods'), 51707)
        self.assertEqual((env['MELEE_WINDOW_W'],env['MELEE_WINDOW_H']), ('960','540'))
        self.assertEqual(env['MELEE_UNATTENDED'], '1')
        self.assertTrue(env['MELEE_RUN_OWNER'])

    def test_redacted_artifacts_and_stream(self):
        import demo_tour
        with tempfile.TemporaryDirectory() as tmp:
            private = str(Path(tmp)/'private.iso')
            path = Path(tmp)/'runner.log'
            text = private+'\n'+private.replace('\\','/')+'\n'+private.replace('\\','/').replace('/','\\')
            demo_tour.write_public(path, text, private)
            demo_tour.capture_public(io.StringIO(text), path, private)
            for file in Path(tmp).rglob('*'):
                if file.is_file():
                    content=file.read_text()
                    self.assertNotIn(private,content)
                    self.assertNotIn(private.replace('\\','/'),content)

    def test_budget_guard_and_output_routing(self):
        import demo_tour
        with self.assertRaises(TimeoutError): demo_tour.remaining(0)
        guard=demo_tour.cpu_guard({'id':'fixture'})
        self.assertIn('gd.cpu_mode(port,"stand")', guard)
        self.assertIn('on_frame_pre', guard)
        self.assertIn('frames < 2', guard)
        self.assertIn('acting CPU', demo_tour.cpu_guard({'id':'fixture','acting_cpu':True}))
        plan=demo_tour.make_plan(Path('out').resolve(),Path('private.iso'), 'bash',1,6,90,300,[])
        self.assertEqual(plan['environment']['GW_BUILD_ROOT'],str(Path('out').resolve()/'runtime'))
        self.assertIn('--max-seconds', plan['command'])
        self.assertEqual(plan['command'][-1], '<disc>')

    def test_complete_mocked_tour_outputs_are_private_and_local(self):
        require_game('pc/scripts/examples/demos/catalogue.json')
        import demo_tour
        with tempfile.TemporaryDirectory() as tmp:
            iso=Path(tmp)/'private.iso'; iso.write_text('test fixture')
            output=Path(tmp)/'review'
            paths=[]
            def entry(row,n,out,env,args,deadline,alias):
                self.assertTrue(alias.is_file())
                self.assertEqual(env['GW_BUILD_ROOT'],str(out/'runtime'))
                self.assertEqual(env['MELEE_UNATTENDED'],'1')
                native=out/'runtime/runs'/row['id']; native.mkdir(parents=True)
                paths.append(native)
                (native/'verdict.json').write_text(json.dumps({'verdict':'OK','command':str(alias)}))
                # Mock native diagnostics to exercise final sanitization as well as public writers.
                (native/'melee-pc.log').write_text(str(iso)+'\n'+str(iso).replace('\\','/')+'\n'+str(alias))
                return {'id':row['id'],'status':'PASS','verdict':'OK','screenshot':None}
            with patch('sys.argv',['demo_tour','--iso',str(iso),'--only','demo_input','--output',str(output)]), \
                    patch.object(demo_tour,'run_entry',side_effect=entry), \
                    patch.object(demo_tour,'stage_runtime',side_effect=lambda build,runtime: runtime.mkdir()), \
                    patch.object(demo_tour,'contact_sheet'), redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(demo_tour.main(),0)
            self.assertFalse((output/'disc.iso').exists())
            variants={str(iso),str(iso).replace('\\','/'),str(iso).replace('/','\\')}
            outputs=[stdout.getvalue()]+[f.read_text() for f in output.rglob('*') if f.is_file()]
            for text in outputs:
                for variant in variants:
                    self.assertNotIn(variant,text)
                    self.assertNotIn(json.dumps(variant)[1:-1],text)
            self.assertEqual(json.loads((output/'results.json').read_text())[0]['verdict'],'OK')
            self.assertTrue(all(p.is_relative_to(output) for p in paths))

    def test_cpu_guard_runs_after_two_frames_and_reasserts_after_switch(self):
        import demo_tour
        fixture='''local calls,logs=0,{}
gd={match=function() return {active=true} end,
player=function(port) if port==2 or port==6 then return {cpu=true} end end,
cpu_mode=function(port,mode) assert(mode=="stand"); calls=calls+1; return true end,
log=function(text) logs[#logs+1]=text end}
'''+demo_tour.cpu_guard({'id':'fixture'})+'''
on_match_start(); on_frame_pre(); assert(calls==0)
on_frame_pre(); assert(calls==2 and #logs==2)
on_frame_pre(); assert(calls==4)
on_stage_switch{phase="after"}; on_frame_pre(); assert(calls==4)
on_frame_pre(); assert(calls==6 and #logs==4)
on_frame_pre(); assert(calls==8) -- still reasserts for a respawn/recycled CPU
'''
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'guard.lua'; path.write_text(fixture)
            result=subprocess.run(['lua',str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_per_demo_requires_launcher_ok_and_cpu_proof(self):
        import demo_tour
        for verdict,proof in [('OK',True),('HUNG',True),('TIMEOUT',True),('OK',False)]:
            with self.subTest(verdict=verdict,proof=proof), tempfile.TemporaryDirectory() as tmp:
                out=Path(tmp); native=out/'runtime/runs/fixture'; native.mkdir(parents=True)
                log='tour CPU proof: stand port 2\n' if proof else ''
                (native/'melee-pc.log').write_text(log)
                (native/'verdict.json').write_text(json.dumps({'verdict':verdict,'code':0 if verdict=='OK' else 124}))
                class Process:
                    stdout=io.StringIO('launcher final '+verdict+'\n')
                    def poll(self): return None
                    def wait(self,timeout): return 0
                commands=[]
                client=SimpleNamespace(sock=SimpleNamespace(settimeout=lambda n: None),close=lambda:None)
                def command(line):
                    commands.append(line)
                    return ['1'] if line=='= gd.scene().epoch' else ['true']
                client.command=command
                args=SimpleNamespace(iso=out/'private.iso',seconds=.001,demo_max_seconds=2,port=51707,bash='bash')
                env=demo_tour.tour_environment(out,out/'mods',51707)
                with patch.object(demo_tour.subprocess,'Popen',return_value=Process()) as launch, \
                        patch.object(demo_tour,'load_console_class',return_value=lambda *a,**k:client), \
                        patch.object(demo_tour,'run_scenario',return_value={'status':'PASS'}), \
                        patch.object(demo_tour,'wait_file'):
                    result=demo_tour.run_entry({'id':'fixture','path':'demos/input'},0,out,env,args,time.monotonic()+3,out/'disc.iso')
                self.assertEqual(result['verdict'],verdict)
                self.assertEqual(result['status'],'PASS' if verdict=='OK' and proof else 'FAIL')
                self.assertIn('--max-seconds',launch.call_args.args[0])
                self.assertNotIn(str(args.iso),str(launch.call_args))
                self.assertEqual(launch.call_args.kwargs['env']['MELEE_UNATTENDED'],'1')
                self.assertTrue(any(c.startswith('scene ') for c in commands))
                self.assertIn('unload fixture',commands)
                self.assertIn('quit',commands)

    def test_invalid_width_and_nonfinite_budget_fail_without_launch(self):
        import demo_tour
        with patch.dict('os.environ',{'MELEE_WINDOW_W':'1920'}):
            with self.assertRaises(ValueError): demo_tour.tour_environment(Path('out'),Path('mods'),51707)
        with patch.dict('os.environ',{},clear=True):
            env=demo_tour.tour_environment(Path('out'),Path('mods'),51707)
            self.assertEqual((env['MELEE_WINDOW_W'],env['MELEE_WINDOW_H']),('1024','576'))
        with patch('sys.argv',['demo_tour','--iso','fixture.iso','--max-seconds','nan']), \
                patch.object(demo_tour.subprocess,'Popen') as launch, patch('sys.stderr',io.StringIO()):
            with self.assertRaises(SystemExit): demo_tour.main()
            launch.assert_not_called()

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = GAME / 'pc/scripts/examples'
CATALOGUE = EXAMPLES / 'demos/catalogue.json'


def registered_api():
    require_game('pc/platform/gw_script.c')
    names = set()
    for path in (GAME / 'pc/platform').glob('gw_script*'):
        if path.suffix not in ('.c', '.inc'):
            continue
        source = path.read_text(encoding='utf-8')
        for table, body in re.findall(
                r'luaL_Reg\s+(gs_gd_funcs|gs_kit_funcs)\[\]\s*=\s*\{(.*?)\{NULL,\s*NULL\}',
                source, re.S):
            prefix = 'gd.kit.' if table == 'gs_kit_funcs' else 'gd.'
            names.update(prefix + name for name in re.findall(r'\{\s*"([\w]+)"\s*,', body))
        # Helpers declared in the embedded prelude/comm module.
        names.update('gd.' + name for name in re.findall(r'function gd\.([\w]+)\(', source))
    return names


def lua_calls(source):
    # Strip comments and quoted strings before scanning (preserve newlines).
    source = re.sub(r'--\[\[.*?\]\]|--[^\n]*|\[\[.*?\]\]|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                    '', source, flags=re.S)
    # Includes method references used by pcall, without treating gd fields as calls.
    return set(re.findall(r'\bgd\.((?:kit\.)?[a-z_]\w*)\s*(?=[({,\)])', source))


def validate(catalogue=CATALOGUE, syntax=True):
    rows = json.loads(catalogue.read_text(encoding='utf-8'))
    index = catalogue.with_name('README.md').read_text(encoding='utf-8')
    names = registered_api()
    assert 'gd.player' in names and 'gd.kit.text' in names, 'registration parser found no API'
    errors, lua_files, seen = [], set(), set()
    for row in rows:
        ident = row['id']
        if ident in seen:
            errors.append(f'duplicate catalogue id: {ident}')
        seen.add(ident)
        if f'`{ident}`' not in index:
            errors.append(f'{ident}: absent from index')
        folder = (EXAMPLES / row['path']).resolve()
        if not folder.is_relative_to(ROOT):
            errors.append(f'{ident}: path escapes workspace')
            continue
        if row.get('reference_only'):
            if not folder.exists():
                errors.append(f'{ident}: reference does not exist')
            continue
        try:
            manifest = json.loads((folder / 'mod.json').read_text(encoding='utf-8'))
            entry = (folder / manifest.get('entry', 'main.lua')).resolve()
            assert entry.is_relative_to(folder) and entry.is_file(), 'entry missing or escapes mod'
            assert manifest['id'] == ident, 'manifest id differs'
            assert manifest['kind'] == 'script' and manifest['api_version'] == 1
        except (OSError, KeyError, ValueError, AssertionError) as exc:
            errors.append(f'{ident}: {exc}')
            continue
        files = list(folder.rglob('*.lua'))
        lua_files.update(files)
        for path in files:
            source = path.read_text(encoding='utf-8')
            if row.get('new') and row['category'] == 'demo' and path == entry and len(source.splitlines()) > 150:
                errors.append(f'{ident}: entry exceeds 150 lines')
            for call in sorted(lua_calls(source)):
                if 'gd.' + call not in names:
                    errors.append(f'{path.relative_to(ROOT)}: unregistered gd.{call}')
    # Every newly supplied mod must be indexed, including showcases.
    for manifest in catalogue.parent.rglob('mod.json'):
        ident = json.loads(manifest.read_text(encoding='utf-8'))['id']
        if ident not in seen:
            errors.append(f'{ident}: mod missing from catalogue')
    if syntax:
        compiler = shutil.which('luac')
        if not compiler:
            errors.append('luac is required for syntax validation')
        else:
            for path in sorted(lua_files):
                result = subprocess.run([compiler, '-p', str(path)], capture_output=True, text=True)
                if result.returncode:
                    errors.append(result.stderr.strip())
    return errors, len(rows), len(lua_files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-syntax', action='store_true')
    args = parser.parse_args()
    try:
        errors, count, files = validate(syntax=not args.no_syntax)
    except (OSError, ValueError) as exc:
        print(f'FAIL: {exc}')
        return 1
    for error in errors:
        print('FAIL:', error)
    print(f'{"FAIL" if errors else "PASS"}: {count} catalogue entries; {files} Lua files')
    safety = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(TourSafetyTests))
    return bool(errors) or not safety.wasSuccessful()


if __name__ == '__main__':
    raise SystemExit(main())
