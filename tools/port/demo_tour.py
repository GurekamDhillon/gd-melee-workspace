"""Integrator-only visible demo tour. This packet does not run the game.

python tools/port/demo_tour.py --iso C:/path/vanilla.iso --plan
python tools/port/demo_tour.py --iso C:/path/vanilla.iso --seconds 6
Requires an existing integrator-built EXE, Git Bash, Pillow, and free localhost port.
The default catalogue skips reference-only/asset-dependent/configured workloads.
All results live below --output. Its volume must support a hard link to the disc.
Each demo has an owned unattended launcher verdict and a 90s limit; tour limit 600s.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
import math
import threading

ROOT = Path(__file__).resolve().parents[2]
MELEE = Path(os.environ.get('GW_MELEE') or ROOT / 'melee').expanduser().resolve()
EXAMPLES = MELEE / 'pc/scripts/examples'
CATALOGUE = EXAMPLES / 'demos/catalogue.json'
DEFAULT_SCENE = 'mode=lab;stage=fd;p1=fox/hu;p2=marth/cpu0'


def admitted(rows):
    return [r for r in rows if not r.get('reference_only') and r.get('tour', True)]


def tour_environment(output, mods, port):
    env = dict(os.environ)
    # Do not inherit another task's pads, scripts, test wrapper or hidden-window state.
    for name in list(env):
        if name.startswith(('MELEE_SCRIPT', 'MELEE_PAD', 'MELEE_LAB_', 'MELEE_TEST')):
            env.pop(name)
    width, height = int(env.get('MELEE_WINDOW_W', '1024')), int(env.get('MELEE_WINDOW_H', '576'))
    if not 1 <= width <= 1080 or height < 1:
        raise ValueError('window dimensions must be positive; width must be <=1080')
    env.update(MELEE_WINDOW_X='-1080', MELEE_WINDOW_Y='-360', MELEE_WINDOW_W=str(width),
               MELEE_WINDOW_H=str(height), MELEE_WINDOW_HIDE='0', MELEE_RENDER_SCALE='1',
               MELEE_WIDESCREEN='1', MELEE_TURBO='0', MELEE_FPS='u', MELEE_VOLUME='0',
               MELEE_SCRIPTS='0', MELEE_CONSOLE_PORT=str(port), MELEE_MODS='1',
               MELEE_MODS_DIR=str(mods.resolve()), MELEE_SCRIPT_DATA_DIR=str((output/'data').resolve()),
               MELEE_SCENE=DEFAULT_SCENE, MELEE_LAB='1', GW_RUNS_KEEP='1000000',
               MELEE_UNATTENDED='1', MELEE_WATCHDOG_ACTION='exit', MELEE_RUN_OWNER='demo-tour')
    return env


def redact(text, disc):
    # Include JSON-escaped and both slash forms; inherited environment/errors count too.
    values = {str(disc), str(Path(disc).resolve())}
    values.update(v for k,v in os.environ.items()
                  if v and (k.startswith('GW_ISO') or k == 'MELEE_ISO'))
    variants = {variant for value in values for variant in
                (value,value.replace('\\','/'),value.replace('/','\\'))}
    variants.update(json.dumps(v,ensure_ascii=ascii)[1:-1]
                    for v in tuple(variants) for ascii in (True,False))
    for value in sorted(variants, key=len, reverse=True):
        if value:
            text = re.sub(re.escape(value), lambda _: '<disc>', text, flags=re.I)
    return text


def write_public(path, text, disc):
    path.write_text(redact(text, disc), encoding='utf-8')


def capture_public(stream, path, disc, alias=None):
    # Never direct child stdout/stderr to disk before redaction.
    with path.open('w', encoding='utf-8') as out:
        for line in stream:
            out.write(redact(redact(line,alias) if alias else line,disc)); out.flush()


def remaining(deadline):
    value = deadline-time.monotonic()
    if value <= 0:
        raise TimeoutError('tour/demo wall-clock budget exhausted')
    return value


def cpu_guard(row):
    if row.get('acting_cpu'):
        body = 'if not seen.allowed then gd.log("tour CPU policy: acting CPU allowed by catalogue"); seen.allowed=true end'
    else:
        body = '''for port=1,6 do
    local p=gd.player(port)
    if p and p.cpu then
      assert(gd.cpu_mode(port,"stand"),"tour CPU stand refused port "..port)
      if not seen[port] then gd.log("tour CPU proof: stand port "..port); seen[port]=true end
    end
  end'''
    return '''-- @id: demo_tour_guard
-- @gameplay: true
local frames,seen=0,{}
function on_match_start() frames=0; seen={} end
function on_stage_switch(e) if e.phase=="after" then frames=0; seen={} end end
function on_frame_pre()
  if not gd.match().active then frames=0; seen={}; return end
  frames=frames+1
  if frames < 2 then return end
  '''+body+'''
end
'''


def make_plan(output, iso, bash, port, seconds, demo_limit, tour_limit, rows):
    env=tour_environment(output,output/'mods',port)
    env['GW_BUILD_ROOT']=str(output/'runtime')
    command=[bash,str(ROOT/'tools/port/run.sh'),'--realtime','--max-seconds',str(demo_limit),
             'ENTRY-ID','--iso','<disc>']
    return {'command':command,'environment':{k:redact(v,iso) for k,v in env.items()
            if k.startswith('MELEE_') or k=='GW_BUILD_ROOT'},'entries':rows,
            'seconds':seconds,'demo_max_seconds':demo_limit,'max_seconds':tour_limit,
            'writes':'Only output: runtime baseline copies, runtime/runs/<id> native diagnostics and verdicts; mods, data, guard scripts, runner logs, plan, results, summary and contact sheet.',
            'disc_policy':'Temporary same-volume hard-link alias; no disc bytes copied; alias removed after owned processes exit.'}


def stage_runtime(build, runtime):
    runtime.mkdir()
    for name in ('melee-pc.exe','melee-pc.map'):
        source=build/name
        if source.is_file(): shutil.copy2(source,runtime/name)
        elif name.endswith('.exe'): raise RuntimeError('existing built EXE is required')


def command_before(client, line, deadline):
    client.sock.settimeout(min(10,remaining(deadline)))
    return client.command(line)


def wait_match(client, epoch, timeout=45, deadline=None):
    end=min(time.monotonic()+timeout, deadline or float('inf'))
    while remaining(end):
        reply=command_before(client,'= gd.match().active and gd.player(1) ~= nil and gd.scene().epoch ~= '+str(epoch),end)
        if any(line.strip()=='true' for line in reply): return
        time.sleep(min(0.15,remaining(end)))


def script_errors(log):
    # gs_report writes: script [id] <load|hook|task>: diagnostic.
    # Ordinary gd.log status lines use a different prefix and aren't exceptions.
    pattern = r'script \[[^\]]+\] (?:load|on_\w+|task|instruction budget|runtime)[^\n]*:'
    return re.findall(pattern + r'[^\n]*', log, re.I)


def wait_file(path, timeout=15):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if path.is_file() and path.stat().st_size>8:
            # Queued screenshots can appear before their final write; validate through Pillow.
            try:
                from PIL import Image
                with Image.open(path) as img:
                    img.verify()
                with Image.open(path) as img:
                    img.load()  # verify() does not necessarily inflate all pixel data.
                return
            except (OSError, ValueError):
                pass
        time.sleep(min(0.1,max(0,deadline-time.monotonic())))
    raise TimeoutError(f'queued screenshot never completed: {path}')


def contact_sheet(results, output):
    from PIL import Image, ImageDraw
    columns, width, height=3,356,238
    sheet=Image.new('RGB',(columns*width,max(1,(len(results)+columns-1)//columns)*height),'#101827')
    draw=ImageDraw.Draw(sheet)
    for i,row in enumerate(results):
        x,y=(i%columns)*width,(i//columns)*height
        if row.get('screenshot'):
            try:
                with Image.open(row['screenshot']) as img:
                    img=img.convert('RGB'); img.thumbnail((width-12,200)); sheet.paste(img,(x+6,y+6))
            except OSError:
                pass
        draw.text((x+6,y+211),row['status']+' '+row['id'],fill='white')
    sheet.save(output/'contact-sheet.png')


def prepare_mods(rows, output):
    if len(rows)!=1: raise ValueError('mount exactly one current demo at a time')
    mods=output/'mods'; mods.mkdir()
    enabled=[]
    for row in rows:
        if row.get('mount'):
            # New packages are only original packet text; source mods remain unchanged.
            shutil.copytree(EXAMPLES/row['path'],mods/row['id'],ignore=shutil.ignore_patterns('scripts','__pycache__'))
            enabled.append(row['id'])
    (mods/'enabled.txt').write_text('\n'.join(enabled)+'\n')
    return mods


def run_scenario(row, client, output, sandbox, deadline, disc, alias):
    """Audit-derived keys, state assertions and fully decoded A/B captures."""
    from demo_scenarios import SCENARIOS
    steps=SCENARIOS.get(row['id'])
    if not steps:
        raise RuntimeError('no behavior scenario for this entry; run existing reference manually')
    records=[]
    serialize='''local function S(v,d) d=d or 0; if type(v)~='table' then return tostring(v) end
      if d>2 then return '{..}' end; local t={}; local n=0
      for k,x in pairs(v) do n=n+1; if n>20 then break end; t[#t+1]=tostring(k)..'='..S(x,d+1) end
      table.sort(t); return '{'..table.concat(t,',')..'}' end; '''
    def hold(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            remaining(deadline); time.sleep(min(.1,max(0,end-time.monotonic())))
    for index,step in enumerate(steps):
        kind=step[0]; record={'step':step}; records.append(record)
        if kind=='k':
            epoch=None
            if row['id']=='demo_six_slots' and step[1]=='L':
                reply=command_before(client,'= gd.scene().epoch',deadline)
                epoch=int(next(line.strip() for line in reply if line.strip().isdigit()))
            record['reply']=command_before(client,'demo_key '+step[1],deadline)
            if epoch is not None: wait_match(client,epoch,deadline=deadline)
            hold(step[2] if len(step)>2 else .7)
        elif kind=='w': hold(step[1])
        elif kind in ('e','assert'):
            expression=step[1]
            if kind=='assert': expression='assert(('+expression+'),"behavior assertion failed"); return "ASSERT PASS"'
            else: expression='return '+expression
            record['reply']=command_before(client,'= (function() '+serialize+expression+' end)()',deadline)
            if kind=='assert' and not any('ASSERT PASS' in line for line in record['reply']):
                raise RuntimeError('behavior assertion produced no success proof')
        elif kind=='c': record['reply']=command_before(client,step[1],deadline)
        elif kind=='s':
            name=row['id']+'-'+str(index)+'-'+step[1]+'.png'
            command_before(client,'local ok,p=gd.screenshot('+json.dumps(name)+'); assert(ok,p)',deadline)
            shot=output/'data/console'/name
            wait_file(shot,timeout=min(15,remaining(deadline))); record['screenshot']=str(shot)
        elif kind=='probe':
            token=row['id']+'-'+str(index)
            command_before(client,'demo_state '+token,deadline)
            log=sandbox/'melee-pc.log'; end=min(deadline,time.monotonic()+5)
            marker='tour state '+token+' '
            while remaining(end):
                text=log.read_text(errors='replace') if log.exists() else ''
                lines=[line.split(marker,1)[1] for line in text.splitlines() if marker in line]
                if lines:
                    record['state']=lines[-1]
                    if not re.search(step[1],lines[-1]): raise RuntimeError('demo state assertion failed: '+step[1])
                    break
                hold(.05)
        else: raise RuntimeError('unsupported scenario step')
        write_public(output/(row['id']+'-scenario.json'),redact(json.dumps(records,indent=2),alias),disc)
    return {'status':'PASS','steps':len(records),'evidence':str(output/(row['id']+'-scenario.json'))}


def load_console_class():
    path=EXAMPLES/'demos/console-socket/client.py'
    spec=importlib.util.spec_from_file_location('demo_console_client',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.Console


def run_entry(row, n, output, env, args, tour_deadline, iso_alias):
    """One owned launch gives each demo an authoritative native launcher verdict."""
    ident=row['id']; sandbox=output/'runtime/runs'/ident
    result={'id':ident,'status':'FAIL','screenshot':None,'verdict':'NOT_LAUNCHED'}
    deadline=min(tour_deadline,time.monotonic()+args.demo_max_seconds)
    limit=remaining(deadline)
    guard=output/(ident+'-guard.lua')
    guard.write_text(cpu_guard(row),encoding='utf-8')
    entry_output=output/'entries'/ident; entry_output.mkdir(parents=True)
    mounts=prepare_mods([row],entry_output)
    child_env=dict(env,MELEE_SCRIPT=str(guard),MELEE_RUN_OWNER=env['MELEE_RUN_OWNER']+'/'+ident,
                   MELEE_MODS_DIR=str(mounts),
                   MELEE_RUN_LABEL='demo-tour / '+ident,
                   MELEE_MAX_SECONDS=str(limit),MELEE_SCENE=row.get('tour_scene',DEFAULT_SCENE))
    command=[args.bash,str(ROOT/'tools/port/run.sh'),'--realtime','--max-seconds',str(limit),
             ident,'--iso',str(iso_alias)]
    process=None; client=None; pump=None; loaded=False
    try:
        with socket.socket() as probe: probe.bind(('127.0.0.1',args.port))
        process=subprocess.Popen(command,cwd=ROOT,env=child_env,stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,text=True,errors='replace')
        pump=threading.Thread(target=capture_public,args=(process.stdout,output/(ident+'-runner.log'),args.iso,iso_alias),daemon=True)
        pump.start()
        Console=load_console_class()
        startup=min(deadline,time.monotonic()+45)
        while remaining(startup):
            if process.poll() is not None: raise RuntimeError('launcher exited before console ready')
            try:
                client=Console(args.port,timeout=min(2,remaining(startup))); break
            except OSError: time.sleep(min(0.2,remaining(startup)))
        wait_match(client,-1,deadline=deadline)
        command_before(client,'load '+str((EXAMPLES/row['path']).resolve()),deadline); loaded=True
        epoch_reply=command_before(client,'= gd.scene().epoch',deadline)
        epoch=int(next(line.strip() for line in epoch_reply if line.strip().isdigit()))
        command_before(client,'scene '+row.get('tour_scene',DEFAULT_SCENE),deadline)
        wait_match(client,epoch,deadline=deadline)
        # Let both demo initialization and the guard run on completed match frames.
        command_before(client,'gd.run(function() gd.wait(2); gd.log("tour demo loaded; CPU guard active") end)',deadline)
        result['scenario']=run_scenario(row,client,output,sandbox,deadline,args.iso,iso_alias)
        if result['scenario'].get('status')!='PASS': raise RuntimeError('behavior scenario did not pass')
        end=min(deadline,time.monotonic()+args.seconds)
        while time.monotonic()<end:
            remaining(deadline)
            if process.poll() is not None: raise RuntimeError('launcher exited during demo')
            time.sleep(min(0.1,end-time.monotonic()))
        remaining(deadline)
        name=f'{n:02d}-{ident}.png'
        command_before(client,'local ok,path=gd.screenshot('+json.dumps(name)+'); assert(ok,path)',deadline)
        shot=output/'data/console'/name
        wait_file(shot,timeout=min(15,remaining(deadline)))
        result['screenshot']=str(shot)
        command_before(client,'unload '+ident,deadline); loaded=False
        command_before(client,'quit',deadline)
        process.wait(timeout=remaining(deadline))
    except (OSError,RuntimeError,TimeoutError,ValueError,StopIteration,subprocess.TimeoutExpired) as exc:
        result['reason']=redact(redact(str(exc),iso_alias),args.iso)
    finally:
        # The launcher's exact child lives in a kill-on-close Job. Never kill by name.
        if process and process.poll() is None:
            if client and time.monotonic()<deadline:
                try:
                    if loaded: command_before(client,'unload '+ident,deadline)
                    command_before(client,'quit',deadline)
                except (OSError,RuntimeError,TimeoutError): pass
            try: process.wait(timeout=max(0.1,deadline-time.monotonic())+3)
            except subprocess.TimeoutExpired:
                # Ending this exact wrapper causes the native supervisor to close its job.
                process.terminate()
                try: process.wait(timeout=3)
                except subprocess.TimeoutExpired: result['reason']='owned wrapper did not exit'
        if client: client.close()
        if pump: pump.join(timeout=3)
    # The supervisor can finish just after its Bash wrapper exits; await its final record.
    verdict_path=sandbox/'verdict.json'
    verdict_deadline=time.monotonic()+3
    while process and not verdict_path.exists() and time.monotonic()<verdict_deadline:
        time.sleep(0.05)
    log=sandbox/'melee-pc.log'
    segment=log.read_text(errors='replace') if log.exists() else ''
    errors=script_errors(segment)
    if errors: result['reason']='; '.join(errors)
    proof=[line for line in segment.splitlines() if 'tour CPU proof:' in line or 'tour CPU policy:' in line]
    result['cpu_policy']='acting' if row.get('acting_cpu') else 'stand'
    result['cpu_proof']=proof
    if not proof: result['reason']='missing CPU policy proof in native log'
    if verdict_path.exists():
        verdict=json.loads(verdict_path.read_text())
        result['verdict']=verdict.get('verdict','MISSING')
        result['launcher_code']=verdict.get('code')
    elif process:
        result['verdict']='MISSING'
    if result['verdict']!='OK': result['reason']='launcher verdict: '+result['verdict']
    if not result.get('reason') and result['screenshot']: result['status']='PASS'
    write_public(output/(ident+'.log'),redact(segment,iso_alias),args.iso)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso',type=Path,required=True)
    parser.add_argument('--seconds',type=float,default=6)
    parser.add_argument('--demo-max-seconds',type=float,default=90)
    parser.add_argument('--max-seconds',type=float,default=600)
    parser.add_argument('--port',type=int,default=51707)
    parser.add_argument('--only',help='comma-separated catalogue ids')
    parser.add_argument('--bash',default='C:/Program Files/Git/bin/bash.exe')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--plan',action='store_true',help='print redacted plan; never launch')
    args=parser.parse_args()
    if not all(math.isfinite(v) and v>0 for v in (args.seconds,args.demo_max_seconds,args.max_seconds)) or args.seconds>600 or not 1<=args.port<=65535:
        parser.error('limits must be positive finite; seconds <=600; port 1..65535')
    rows=json.loads(CATALOGUE.read_text(encoding='utf-8')); selected=admitted(rows)
    if args.only:
        wanted=set(args.only.split(',')); known={r['id'] for r in selected}
        if wanted-known: parser.error('unknown or excluded ids')
        selected=[r for r in selected if r['id'] in wanted]
    stamp=time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())
    output=(args.output or ROOT/'_build/demo-tour'/stamp).resolve()
    # Baseline is read-only; stage a runtime root beneath the ONLY result directory.
    build=Path(os.environ.get('GW_BUILD_ROOT',str(ROOT/'_build'))).resolve()
    try:
        plan=make_plan(output,args.iso,args.bash,args.port,args.seconds,args.demo_max_seconds,args.max_seconds,selected)
        plan['skipped']=[r['id'] for r in rows if r not in admitted(rows)]
        if args.plan:
            print(redact(json.dumps(plan,indent=2),args.iso)); return 0
        if not args.iso.is_file(): raise ValueError('configured disc does not exist')
        if output.exists(): raise ValueError('output must be a new directory')
        from PIL import Image
        with socket.socket() as probe: probe.bind(('127.0.0.1',args.port))
        output.mkdir(parents=True)
        # Hard links contain no target path, unlike symlinks; no disc bytes are copied.
        alias=output/'disc.iso'
        try: os.link(args.iso,alias)
        except OSError: raise ValueError('disc alias unavailable; choose an output on the disc volume supporting hard links') from None
        results=[]; tour_deadline=time.monotonic()+args.max_seconds
        try:
            stage_runtime(build,output/'runtime')
            env=tour_environment(output,output/'mods',args.port)
            env['GW_BUILD_ROOT']=str(output/'runtime'); env['MELEE_RUN_OWNER']='demo-tour-'+stamp
            # Do not let inherited ISO variables appear in metadata or select another disc.
            for key in list(env):
                if key.startswith(('GW_ISO','MELEE_ISO')): env.pop(key)
            write_public(output/'plan.json',json.dumps(plan,indent=2),args.iso)
            results=[{'id':r['id'],'status':'SKIP','verdict':'NOT_LAUNCHED','reason':r.get('skip_reason','See catalogue')} for r in rows if r not in admitted(rows) and not args.only]
            for n,row in enumerate(selected):
                if time.monotonic()>=tour_deadline:
                    results.append({'id':row['id'],'status':'FAIL','verdict':'NOT_LAUNCHED','reason':'whole-tour wall limit exhausted'}); continue
                result=run_entry(row,n,output,env,args,tour_deadline,alias)
                results.append(result)
                print(redact(result['status']+' '+row['id']+' verdict='+result['verdict']+' '+result.get('reason','load/capture/unload; manual acceptance pending'),args.iso),flush=True)
                write_public(output/'results.json',json.dumps(results,indent=2),args.iso)
        finally:
            alias.unlink(missing_ok=True)
            # Native logs use the safe alias; also sanitize inherited diagnostics/JSON.
            for file in output.rglob('*'):
                if file.is_file() and file.suffix in ('.json','.log','.txt'):
                    text=file.read_text(errors='replace')
                    write_public(file,redact(text,alias),args.iso)
        write_public(output/'results.json',json.dumps(results,indent=2),args.iso)
        tour_verdict='TIMEOUT' if time.monotonic()>=tour_deadline else ('FAIL' if any(r['status']=='FAIL' for r in results) else 'OK')
        write_public(output/'tour-verdict.json',json.dumps({'verdict':tour_verdict,'max_seconds':args.max_seconds,
                     'owner':env['MELEE_RUN_OWNER'],'demo_verdicts':[{ 'id':r['id'],'verdict':r['verdict']} for r in results]},indent=2),args.iso)
        write_public(output/'summary.txt','TOUR verdict='+tour_verdict+'\n'+'\n'.join(r['status']+' '+r['id']+' verdict='+r['verdict']+' '+r.get('reason','') for r in results)+'\n',args.iso)
        contact_sheet(results,output)
        print(redact(str(output),args.iso))
        return int(tour_verdict!='OK')
    except (OSError,RuntimeError,ValueError,TimeoutError) as exc:
        print('FAIL: '+redact(str(exc),args.iso)); return 1


if __name__=='__main__':
    raise SystemExit(main())
