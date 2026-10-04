#!/usr/bin/env python3
"""Run two isolated Linux clients over loopback and compare confirmed rollback hashes."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import socket

def main():
    root = Path(__file__).resolve().parents[2]
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('disc',type=Path)
    ap.add_argument('--seconds',type=int,default=90)
    ap.add_argument('--conditions',default='off')
    a=ap.parse_args()
    build=Path(os.environ.get('GW_BUILD_ROOT',root/'_build/agents/linux'))
    pair=Path(tempfile.mkdtemp(prefix='netplay-',dir=build))
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    processes=[]
    print(f'RUN {pair}',flush=True)
    try:
        for role in ('host','guest'):
            run=pair/role;run.mkdir()
            for name in ('melee','melee-pc.msvc.map'):
                subprocess.run(['cp','--reflink=auto',str(build/name),str(run/name)],check=True)
            for name in ('assets','ui'):shutil.copytree(build/name,run/name)
            env=os.environ.copy()
            env.update(MELEE_NET_SIM=a.conditions,MELEE_NETPLAY=f'host:{port}' if role=='host' else f'join:127.0.0.1:{port}',
                       MELEE_NETPLAY_BIND='127.0.0.1',MELEE_RB_HASHLOG=str(run/'hashes.csv'),
                       MELEE_VOLUME='3',MELEE_WINDOW_W='640',MELEE_WINDOW_H='480',
                       MELEE_CACHE_DIR=str(run))
            log=open(run/'run.log','w')
            process=subprocess.Popen([str(run/'melee'),'--iso',str(a.disc.resolve())],cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT)
            log.close();processes.append(process)
        deadline=time.monotonic()+a.seconds
        while time.monotonic()<deadline and all(p.poll() is None for p in processes):time.sleep(.5)
    finally:
        for p in processes:
            if p.poll() is None:p.terminate()
        for p in processes:
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.kill();p.wait()

    def hashes(role):
        p=pair/role/'hashes.csv'
        if not p.exists():return {}
        return {int(f):h for f,h in (s.split(',') for s in p.read_text().splitlines())}
    host,guest=hashes('host'),hashes('guest')
    shared=sorted(host.keys()&guest.keys())
    mismatch=[f for f in shared if host[f]!=guest[f]]
    report={'shared_confirmed_frames':len(shared),'mismatching_frames':mismatch[:30],
            'exit_codes':[p.returncode for p in processes]}
    (pair/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    raise SystemExit(0 if len(shared)>=300 and not mismatch else 1)


if __name__ == "__main__":
    main()
