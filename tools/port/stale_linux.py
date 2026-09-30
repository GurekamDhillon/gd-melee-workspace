#!/usr/bin/env python3
"""Track Linux object inputs by content, including compiler, transformer and build flags."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def fingerprint(mode):
    cached = os.environ.get('GW_LINUX_FINGERPRINT_' + mode.upper())
    if cached:
        return cached
    compiler = shutil.which(os.environ.get('GW_CLANG', 'clang'))
    version = subprocess.check_output([compiler, '--version'], text=True)
    if '22.1.8' not in version.splitlines()[0]:
        raise SystemExit('Linux port requires LLVM/Clang 22.1.8')
    inputs = [Path(compiler).resolve(), Path(__file__), ROOT / 'tools/port/build_linux.sh']
    if mode == 'tu':
        inputs += [ROOT / 'tools/port/pipe_linux.sh', Path(os.environ.get('GW_GWTOOL', ROOT / '_build/gwtool_linux/gwtool'))]
    else:
        inputs += [ROOT / 'tools/port/shim_linux.sh', ROOT / 'tools/port/linux_shims.txt']
    env = {k: v for k, v in os.environ.items() if k.startswith(('GW_', 'CPATH', 'CPLUS_INCLUDE_PATH', 'C_INCLUDE_PATH')) and k not in {'GW_JOBS', 'GW_LINUX_FINGERPRINT_TU', 'GW_LINUX_FINGERPRINT_SHIM'}}
    payload = [version, env, [(str(p), digest(p)) for p in inputs]]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

def object_for(mode, source, root=None):
    return source.replace('/', '_') + '.obj' if mode == 'tu' else Path(source).stem + '.obj'

def snapshot(obj, source, root, fp):
    dep = Path(str(obj) + '.d').read_text().replace('\\\n', ' ')
    _, sep, right = dep.partition(':')
    if not sep:
        raise ValueError('invalid dependency file')
    paths = {str((Path(root) / name).resolve()) for name in shlex.split(right)}
    paths.add(str((Path(root) / source).resolve()))
    return {'fingerprint': fp, 'inputs': {p: digest(p) for p in sorted(paths)}}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode', choices=('tu', 'shim'))
    ap.add_argument('--fingerprint', choices=('tu', 'shim'))
    ap.add_argument('--sources'); ap.add_argument('--source'); ap.add_argument('--objects')
    ap.add_argument('--root', default='.')
    ap.add_argument('--record'); ap.add_argument('--all', action='store_true'); ap.add_argument('--why', action='store_true')
    a = ap.parse_args()
    fp = fingerprint(a.fingerprint or a.mode)
    if a.fingerprint:
        print(fp); return
    if a.record:
        data = snapshot(a.record, a.source, a.root, fp)
        dest = Path(a.record + '.inputs.json')
        tmp = dest.with_name(dest.name + f'.{os.getpid()}.tmp')
        tmp.write_text(json.dumps(data, sort_keys=True))
        tmp.replace(dest)
        return
    for line in Path(a.sources).read_text().splitlines():
        source = line.strip()
        if not source or source.startswith('#'): continue
        obj = Path(a.objects) / object_for(a.mode, source)
        reason = ''
        try:
            if a.all: reason = 'forced'
            elif not obj.is_file(): reason = 'no object'
            elif snapshot(obj, source, a.root, fp) != json.loads(Path(str(obj) + '.inputs.json').read_text()): reason = 'inputs changed'
        except (OSError, ValueError):
            reason = 'missing or invalid input record'
        if reason: print(source + ('\t' + reason if a.why else ''))

if __name__ == '__main__':
    main()
