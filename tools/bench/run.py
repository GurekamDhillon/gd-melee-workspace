"""Visible, paced benchmark runner. Never builds or invokes a bare executable."""
from __future__ import annotations
import argparse
import math
import datetime as dt
import json
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import time
import sys

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = Path(__file__).parent / 'scenarios'

def lua(value):
    if value is None: return 'nil'
    if isinstance(value, bool): return 'true' if value else 'false'
    if isinstance(value, (int, float)): return repr(value)
    if isinstance(value, str):
        return '"' + ''.join('\\' + c if c in '\\"' else '\\%03d' % ord(c) if ord(c) < 32 else c for c in value) + '"'
    if isinstance(value, list): return '{' + ','.join(map(lua, value)) + '}'
    if isinstance(value, dict): return '{' + ','.join('[' + lua(k) + ']=' + lua(v) for k, v in value.items()) + '}'
    raise TypeError(type(value))

def scene(roster, scenario):
    if not 2 <= len(roster) <= 6: raise ValueError('roster must contain 2-6 fighters')
    fields = ['mode=' + scenario.get('mode', 'vs'), 'stage=' + scenario.get('stage', 'fd'),
              'time=0', 'items=' + str(scenario.get('items', 'off'))]
    for i, fighter in enumerate(roster, 1):
        if not isinstance(fighter, str) or any(c in fighter for c in ';/\\'):
            raise ValueError('fighter must be one scene character token')
        # Physical scripted slots must be human; slots 5-6 use native virtual claims.
        fields.append(f'p{i}={fighter}/' + ('hu' if i <= 4 else 'cpu9') + '/stocks99')
    return ';'.join(fields)

def environment(config, directory, script, profiler, inherited=None):
    env = dict(os.environ if inherited is None else inherited)
    # Benchmarks own the workload. A caller may select a renderer backend; all
    # other inherited game switches (replay, netplay, training, shader tests, etc.)
    # are removed so an unrelated shell session cannot change this scenario.
    for key in list(env):
        if key.startswith('MELEE_') and key != 'MELEE_BACKEND': env.pop(key)
    env.update(MELEE_SCENE=scene(config['roster'], config), MELEE_TEST_SEED=str(config['seed']),
               MELEE_TURBO='0', MELEE_FPS='u', MELEE_RENDER_SCALE='1', MELEE_MSAA='1',
               MELEE_WIDESCREEN='1', MELEE_BACKEND=env.get('MELEE_BACKEND', 'd3d11'), MELEE_WINDOW_X='-1080', MELEE_WINDOW_Y='-360',
               MELEE_WINDOW_HIDE='0', MELEE_WINDOW_W='1066', MELEE_WINDOW_H='600', MELEE_SCRIPTS='0',
               MELEE_SCRIPT=str(script), MELEE_SCRIPT_DATA_DIR=str(directory / 'script-data'),
               MELEE_PROFILER='1' if profiler else '0', MELEE_PROF_REPORT=str(directory / 'profile.json'),
               MELEE_PROF_TRACE=str(directory / 'trace.json'), MELEE_PROF_HITCH_MS=str(config.get('hitch_ms', 16.66)),
               GW_DAWN_CACHE_SEED='0' if config.get('cold') else '1')
    # Scenario-specific switches must not replace pacing, seed, routing, or visibility.
    allowed = {'MELEE_RENDER_SCALE', 'MELEE_SYNCTEST', 'MELEE_SYNCTEST_BENCH', 'MELEE_PROF_TRACE', 'MELEE_MSAA'}
    for key, value in config.get('env', {}).items():
        if key not in allowed: raise ValueError('unsupported scenario env: ' + key)
        env[key] = str(value)
    return env

def workload_identity(config, env, bundle):
    # Paths and profiler enable/output selection vary in the controlled off/on experiment.
    # Compare the actual workload settings and script/assets content, not output locations.
    excluded = {'MELEE_PROFILER', 'MELEE_PROF_REPORT', 'MELEE_PROF_TRACE',
                'MELEE_SCRIPT', 'MELEE_SCRIPT_DATA_DIR', 'MELEE_MODS_DIR'}
    effective = {key:value for key,value in env.items() if key.startswith('MELEE_') and key not in excluded}
    effective['GW_DAWN_CACHE_SEED'] = env['GW_DAWN_CACHE_SEED']
    assets = []
    for path in sorted(x for x in bundle.rglob('*') if x.is_file()):
        assets.append((path.relative_to(bundle).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    workload = {'effective_environment':effective, 'config':config, 'bundle_content':assets}
    digest=hashlib.sha256(json.dumps(workload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return digest,workload

def discover_mods(directory):
    entries, fighters, stamps = [], [], []
    enabled_path = directory / 'enabled.txt'
    enabled = set(enabled_path.read_text().split()) if enabled_path.exists() else None
    if directory.exists():
        for folder in sorted(x for x in directory.iterdir() if x.is_dir()):
            path = folder / 'mod.json'
            if not path.exists(): continue
            try: manifest = json.loads(path.read_text())
            except (OSError, ValueError): continue
            active = enabled is None or folder.name in enabled or manifest.get('id') in enabled
            entries.append({'id': manifest.get('id', folder.name), 'name': manifest.get('name', folder.name), 'kind': manifest.get('kind'), 'enabled': active})
            for file in sorted(x for x in folder.rglob('*') if x.is_file()):
                st=file.stat();stamps.append((str(file.relative_to(directory)),st.st_size,st.st_mtime_ns))
            install = folder / 'INSTALL.json'
            if active and manifest.get('kind') == 'fighter' and install.exists():
                try:
                    data = json.loads(install.read_text())
                    name = data.get('name', '')
                    token = ''.join(c for c in name.lower() if c.isascii() and c.isalnum())
                    if token: fighters.append({'token': token, 'name': name, 'mod': folder.name})
                except (OSError, ValueError): pass
    fingerprint = hashlib.sha256(json.dumps(stamps, sort_keys=True).encode()).hexdigest()
    return {'entries': entries, 'fighter_candidates': fighters, 'stamp_fingerprint': fingerprint}

def prepare_mission(bundle, directory, config, kit):
    if not config.get('mission_stress'): return
    source = Path(os.environ.get('GW_MELEE') or ROOT / 'melee') / 'pc/scripts/examples/missions'
    for sub in ('missions', 'maze-chunks'):
        shutil.copytree(source / sub, bundle / sub, dirs_exist_ok=True)
    # Execute the same bundled runtime in a separate Lua environment, retaining its callbacks.
    text = (source / 'scripts/main.lua').read_text(encoding='utf-8')
    (bundle / 'scripts/mission_bundle.lua').write_text(text + '\nreturn runtime\n', encoding='utf-8')
    try:
        spec = importlib.util.spec_from_file_location('bench_maze_generate', ROOT / 'tools/maze/generate.py')
        generator = importlib.util.module_from_spec(spec); spec.loader.exec_module(generator)
        files = generator.generate(config['seed'], config.get('maze_size', 12), 'bench_maze')
        generated = directory / 'generated-mission'
        generator.materialize(files, generated, kit, 'bench_maze', prepare_mod=False)
        shutil.copytree(generated / 'missions', bundle / 'missions', dirs_exist_ok=True)
        config['mission_preparation'] = {'ok': True, 'name': 'bench_maze', 'kit': str(kit)}
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        config['mission_preparation'] = {'ok': False, 'reason': str(exc)}

def read_status(directory):
    path = directory / 'script-data' / 'bench' / 'status.json'
    return json.loads(path.read_text()) if path.exists() else {'complete': False, 'reason': 'bench status missing; inspect run log'}

def capture_event_trace(directory, copied):
    status = read_status(directory)
    event = status.get('trace_capture')
    trace = directory / 'trace.json'
    if not event or event['sequence'] in copied or not trace.exists(): return
    name = ''.join(c if c.isalnum() or c in '_-' else '_' for c in event['feature'])
    destination = directory / f"event-{event['logic_frame']}-{name}.trace.json"
    shutil.copy2(trace, destination)
    data=json.loads(destination.read_text())
    frames=[e for e in data.get('traceEvents',[]) if e.get('name')=='frame' and e.get('ph')=='X']
    worst=max(frames,key=lambda e:e.get('dur',0),default={})
    copied[event['sequence']]={'feature':event['feature'],'requested_logic_frame':event['logic_frame'],
                             'trace':destination.name,'scope':'8 native frames around event; report worst neighbouring CPU frame',
                             'worst_cpu_frame_ms':worst.get('dur',0)/1000,
                             'worst_native_frame':worst.get('args',{}).get('frame')}

def execute(command, env, directory, timeout):
    copied={}
    with (directory / 'runner.log').open('w') as output:
        process=subprocess.Popen(command,env=env,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,text=True)
        deadline=time.monotonic()+timeout
        while True:
            try:
                rc=process.wait(timeout=0.1)
                capture_event_trace(directory,copied)
                return rc,copied
            except subprocess.TimeoutExpired:
                try: capture_event_trace(directory,copied)
                except (OSError,ValueError): pass # next atomic status publication retries
                if time.monotonic()>=deadline:
                    # Do not kill unrelated Windows game processes; preserve the labelled window.
                    output.write('runner timeout; close this labelled game window before retrying\n')
                    return 124,copied

def legacy_metrics(samples):
    result = {}
    for name in ('logic_ms', 'gx_ms', 'total_ms', 'worker_ms'):
        values = sorted(float(x[name]) for x in samples if isinstance(x.get(name), (int, float)) and math.isfinite(x[name]))
        if values:
            result[name] = {'count': len(values), 'mean': sum(values)/len(values),
                            **{key: values[max(0, math.ceil(q*len(values))-1)] for key,q in [('p50',.5),('p95',.95),('p99',.99)]}, 'max': values[-1]}
    return result

def summarize(report):
    status = report['bench']['status']
    zones = report.get('zones', {})
    if isinstance(zones, list): zones = {z['name']: z for z in zones}
    lines = [f"{report['bench']['scenario']} / profiler={report['bench']['profiler']} / complete={status.get('complete', False)}",
             'actual roster: ' + ', '.join(p.get('name', '?') for p in status.get('roster', [])),
             f"logic frames: {status.get('frames', 0)}; seed: {report['bench']['seed']}; turbo=0; presentation uncapped",
             'profile scope: ' + report['bench'].get('profile_scope', 'unknown')]
    for name, stats in sorted(zones.items()):
        lines.append(f"{name:32} p50 {stats.get('p50', 0):8.3f} p95 {stats.get('p95', 0):8.3f} p99 {stats.get('p99', 0):8.3f} max {stats.get('max', 0):8.3f} ms")
        if len(lines) >= 20: break
    legacy = report['bench'].get('legacy_metrics', {})
    if 'logic_ms' in legacy: lines.append(f"legacy callback-sampled logic p95 {legacy['logic_ms']['p95']:.3f} ms (off/on observer active)")
    limitations = [x['feature'] + ': ' + x.get('reason', x['status']) for x in status.get('features', []) if x['status'] != 'applied']
    lines.extend(limitations[:8])
    return '\n'.join(lines) + '\n'

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('scenario', choices=[x.stem for x in SCENARIOS.glob('*.json')])
    p.add_argument('--iso', required=True, type=Path)
    p.add_argument('--frames', type=int, default=1800)
    p.add_argument('--seed', type=int, default=12345)
    p.add_argument('--profiler', choices=['on', 'off', 'both'], default='on')
    p.add_argument('--mods-dir', type=Path)
    p.add_argument('--kit', type=Path, default=ROOT / 'menu/out_roguelite/room-kit', help='mission maze kit assets')
    p.add_argument('--config', type=Path, help='JSON scenario overrides including stress setup/events and asset paths')
    p.add_argument('--timeout', type=int, default=300)
    p.add_argument('--bash', default='bash')
    p.add_argument('--plan', action='store_true', help='write launch plan without launching')
    args = p.parse_args(argv)
    if args.frames < 1 or args.timeout < 1: p.error('frames and timeout must be positive')
    config = json.loads((SCENARIOS / (args.scenario + '.json')).read_text())
    overrides = json.loads(args.config.read_text()) if args.config else {}
    config.update(overrides)
    config.update(frames=args.frames, seed=args.seed, scenario=args.scenario)
    # Discover mission generator availability without claiming geometry is mounted.
    config['mission_generator_available'] = (Path(os.environ.get('GW_MELEE') or ROOT / 'melee') / 'pc/scripts/examples/missions/scripts/maze.lua').exists()
    mods_dir = (args.mods_dir or Path(os.environ.get('MELEE_MODS_DIR', str(ROOT / '_build/mods')))).resolve()
    config['mods'] = discover_mods(mods_dir)
    if args.scenario != 'baseline' and 'roster' not in overrides and config['mods']['fighter_candidates']:
        candidate = config['mods']['fighter_candidates'][0]
        config['roster'][1] = candidate['token']
        config['ported_candidate'] = candidate
    original_roster = config['roster'][:]
    modes = [False, True] if args.profiler == 'both' else [args.profiler == 'on']
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    exit_code = 0
    for profiler in modes:
        config['roster'] = original_roster[:]
        admitted = args.plan
        candidates = [config['roster']] + config.get('fallback_rosters', [])
        for attempt, roster in enumerate(candidates):
            config['roster'] = roster
            directory = ROOT / '_build/bench' / args.scenario / (stamp + ('-on' if profiler else '-off') + '-a' + str(attempt))
            directory.mkdir(parents=True)
            bundle = directory / 'bench'
            shutil.copytree(Path(os.environ.get('GW_MELEE') or ROOT / 'melee') / 'pc/scripts/examples/bench', bundle)
            prepare_mission(bundle, directory, config, args.kit)
            (bundle / 'scripts/config.lua').write_text('return ' + lua(config) + '\n', encoding='utf-8')
            env = environment(config, directory, bundle, profiler)
            env['MELEE_MODS_DIR'] = str(mods_dir)
            workload_fingerprint,workload = workload_identity(config, env, bundle)
            sandbox = 'bench-' + stamp + ('-on' if profiler else '-off') + '-a' + str(attempt)
            command = [args.bash, str(ROOT / 'tools/port/run.sh'), '--realtime', sandbox, '--iso', str(args.iso.resolve())]
            plan = {'command': command, 'config': config, 'workload_fingerprint':workload_fingerprint, 'workload':workload, 'environment': {k: v for k, v in env.items() if k.startswith('MELEE_') or k == 'GW_DAWN_CACHE_SEED'}}
            (directory / 'plan.json').write_text(json.dumps(plan, indent=2))
            if args.plan:
                print(directory / 'plan.json'); continue
            if not args.iso.is_file(): p.error('ISO does not exist')
            rc,event_traces = execute(command, env, directory, args.timeout)
            status = read_status(directory)
            log = Path(env.get('GW_BUILD_ROOT', str(ROOT / '_build'))) / 'runs' / sandbox / 'melee-pc.log'
            if log.exists(): shutil.copy2(log, directory / 'melee-pc.log')
            profile = directory / 'profile.json'
            report = json.loads(profile.read_text()) if profile.exists() else {}
            report['bench'] = {'scenario': args.scenario, 'seed': args.seed, 'profiler': profiler,
                               'requested_frames': args.frames, 'status': status, 'exit_code': rc,
                               'sandbox': sandbox, 'plan': plan,
                               'requested_roster': roster, 'actual_roster': status.get('roster', []),
                               'mods_fingerprint': config['mods']['stamp_fingerprint'],
                               'backend': env.get('MELEE_BACKEND', 'd3d11'),
                               'disc': {'path': str(args.iso.resolve()), 'size': args.iso.stat().st_size, 'mtime_ns': args.iso.stat().st_mtime_ns},
                               'feature_statuses': status.get('features', []),
                               'event_traces': list(event_traces.values()),
                               'workload_fingerprint': workload_fingerprint, 'workload': workload,
                               'legacy_metrics': legacy_metrics(status.get('legacy_samples', [])),
                               'legacy_scope': 'latest presented sample once per completed live logic callback; may repeat/skip presentations',
                               'profile_scope': 'bench_reset_to_shutdown' if status.get('measurement_reset') else 'process_lifetime_including_startup_and_setup'}
            if profiler and not profile.exists(): report['bench']['profile_error'] = 'profile.json missing'
            (directory / 'report.json').write_text(json.dumps(report, indent=2))
            summary = summarize(report)
            (directory / 'summary.txt').write_text(summary)
            print(summary, str(directory / 'report.json'))
            if status.get('complete') and not rc and (not profiler or profile.exists()):
                admitted = True
                break
            if rc == 124: break
        if not admitted: exit_code = 1
    return exit_code

if __name__ == '__main__': sys.exit(main())
