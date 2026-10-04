#!/usr/bin/env python3
"""Own Windows game lifetimes; inspect/reap only verified process identities.

The supervisor alone owns a non-inheritable kill-on-close Job Object. The game
is created suspended inside that job atomically, then resumed. The wrapper's native process
handle is also watched: MSYS timeout may kill bash without killing Python.
No third party packages or shell-built commands are used.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
import math
import os
import re
import shutil
from pathlib import Path
import subprocess
import sys
import time

HUNG_EXIT, TIMEOUT_EXIT = 86, 124
_command_discs = set()


def redact(text):
    secrets = _command_discs | {v for k, v in os.environ.items()
        if v and (k.startswith('GW_ISO') or k == 'MELEE_ISO')}
    for secret in sorted(secrets, key=len, reverse=True):
        variants = {secret, secret.replace('\\', '/'), secret.replace('/', '\\')}
        variants |= {json.dumps(v, ensure_ascii=False)[1:-1] for v in list(variants)}
        for variant in sorted(variants, key=len, reverse=True):
            text = re.sub(re.escape(variant), lambda _: '<disc>', text, flags=re.IGNORECASE)
    return text


def safe_value(value):
    if isinstance(value, str): return redact(value)
    if isinstance(value, dict): return {redact(str(k)): safe_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [safe_value(v) for v in value]
    return value


def same_created(a, b):
    # CIM rounds FILETIME to microseconds. Retain PID and executable checks.
    return isinstance(a, int) and isinstance(b, int) and abs(a-b) <= 10000


def atomic_json(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(safe_value(value), indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def normalized(path):
    return str(Path(path).resolve()).replace('\\', '/').casefold()


def heartbeat_state(h, now=None):
    now = time.time() if now is None else now
    if not h or not isinstance(h.get('wall_clock'), (int, float)):
        return 'unknown'
    limit = h.get('watchdog_seconds', 10)
    if limit == 0:
        return 'disabled'
    limit = limit if isinstance(limit, (int, float)) and limit > 0 else 10
    if now - h['wall_clock'] > limit + 5:
        return 'hung'
    if h.get('debugger') or h.get('modal'):
        return 'paused'
    main_age = h.get('main_age_seconds', 0)
    logic_age = h.get('logic_age_seconds', 0)
    present_age = h.get('present_age_seconds', 0)
    if not all(isinstance(v, (int, float)) for v in (main_age, logic_age, present_age)):
        return 'unknown'
    if main_age >= limit:
        return 'hung'
    if h.get('hidden') or h.get('minimized') or h.get('occluded'):
        return 'hidden'
    if h.get('paused'):
        return 'paused'
    if h.get('state') == 'scene-transition' and 0 <= h.get('transition_age_seconds', 31) < 30:
        return 'scene-transition'
    script = h.get('script_watchdog', {})
    if isinstance(script, dict) and script.get('expired', 0):
        return 'script-stalled'
    if logic_age >= limit:
        return 'logic-stalled'
    if present_age >= limit:
        return 'not-presenting'
    return 'running'


def classify(code, log, forced=None):
    if forced:
        return forced
    code = code & 0xffffffff
    if code == HUNG_EXIT:
        return 'HUNG'
    if 'TESTS: TIMEOUT' in log:
        return 'TIMEOUT'
    if code >= 0x80000000 or 'FATAL' in log or 'PANIC' in log:
        return f'CRASH code={code}'
    if 'final exit reason=' not in log and 'melee-pc: exit ' not in log and 'tests complete' not in log:
        return 'SILENT_EXIT' + (f' code={code}' if code else '')
    return 'OK' if code == 0 else f'EXIT code={code}'


def live_processes():
    # CIM includes games launched outside run.sh; never attribute an unverified
    # PID to stale metadata. Inventory failure is an error, never an empty list.
    script = """$ErrorActionPreference='Stop';
    ConvertTo-Json -Compress -Depth 4 -InputObject @(Get-CimInstance Win32_Process -Filter "Name='melee-pc.exe'" | ForEach-Object {
      @{pid=[int]$_.ProcessId; path=$_.ExecutablePath; created=$_.CreationDate.ToFileTimeUtc(); memory=[long]$_.WorkingSetSize}
    })"""
    p = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                       capture_output=True, text=True, check=True)
    rows = json.loads(p.stdout)
    if not isinstance(rows, list):
        raise RuntimeError('invalid process inventory')
    return rows


def inventory(root, processes):
    records = {}
    root = Path(root)
    for file in root.rglob('run.json') if root.exists() else []:
        r = read_json(file)
        if (isinstance(r.get('pid'), int) and isinstance(r.get('process_created'), int)
            and isinstance(r.get('command'), list) and r['command']
            and isinstance(r.get('start'), (int, float)) and isinstance(r.get('owner'), str)):
            records.setdefault((r['pid'], normalized(file.parent/'melee-pc.exe')), []).append((file.parent, r))
    rows = []
    for p in processes:
        row = dict(p, owner='untracked', sandbox=str(Path(p['path']).parent) if p.get('path') else '?',
                   state='unknown', age=0, tracked=False)
        matches = [r for r in records.get((p['pid'], normalized(p['path'])), [])
                   if same_created(r[1]['process_created'], p.get('created'))] if p.get('path') else []
        match = matches[0] if len(matches) == 1 else None
        if match:
            path, record = match
            h = read_json(path/'heartbeat.json')
            # Heartbeats from a previous use of the directory are not evidence.
            if h.get('pid') != p['pid'] or not same_created(h.get('process_created'), p.get('created')):
                h = {}
            row.update(owner=record.get('owner', 'untracked'), sandbox=str(path), tracked=True,
                       age=max(0, time.time()-record.get('start', time.time())),
                       heartbeat=h, state=heartbeat_state(h), label=record.get('label', path.name))
        rows.append(row)
    return rows


def select(rows, owner=None, sandbox=None, hung=False, older_than=None):
    return [r for r in rows if r.get('tracked')
            and (owner is None or r.get('owner') == owner)
            and (sandbox is None or Path(r['sandbox']).name == sandbox or normalized(r['sandbox']) == normalized(sandbox))
            and (not hung or r['state'] == 'hung')
            and (older_than is None or r['age'] >= older_than)]


def reap_rows(rows, terminate):
    for row in rows:
        if not row.get('tracked'):
            raise RuntimeError('refusing to reap an untracked process')
        terminate(row)


class WinAPI:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('lifetime supervision requires native Windows Python')
        self.k = C.WinDLL('kernel32', use_last_error=True)
        signatures = {
            'CreateJobObjectW': (W.HANDLE, [C.c_void_p, W.LPCWSTR]),
            'SetInformationJobObject': (W.BOOL, [W.HANDLE, C.c_int, C.c_void_p, W.DWORD]),
            'AssignProcessToJobObject': (W.BOOL, [W.HANDLE, W.HANDLE]),
            'CloseHandle': (W.BOOL, [W.HANDLE]),
            'OpenProcess': (W.HANDLE, [W.DWORD, W.BOOL, W.DWORD]),
            'WaitForSingleObject': (W.DWORD, [W.HANDLE, W.DWORD]),
            'TerminateProcess': (W.BOOL, [W.HANDLE, W.UINT]),
            'ResumeThread': (W.DWORD, [W.HANDLE]),
            'GetExitCodeProcess': (W.BOOL, [W.HANDLE, C.POINTER(W.DWORD)]),
            'GetProcessTimes': (W.BOOL, [W.HANDLE] + [C.POINTER(W.FILETIME)]*4),
            'QueryFullProcessImageNameW': (W.BOOL, [W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)]),
            'CreateProcessW': (W.BOOL, [W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL,
                                      W.DWORD, C.c_void_p, W.LPCWSTR, C.c_void_p, C.c_void_p]),
            'InitializeProcThreadAttributeList': (W.BOOL, [C.c_void_p, W.DWORD, W.DWORD, C.POINTER(C.c_size_t)]),
            'UpdateProcThreadAttribute': (W.BOOL, [C.c_void_p, W.DWORD, C.c_size_t, C.c_void_p, C.c_size_t, C.c_void_p, C.c_void_p]),
            'DeleteProcThreadAttributeList': (None, [C.c_void_p]),
            'IsProcessInJob': (W.BOOL, [W.HANDLE, W.HANDLE, C.POINTER(W.BOOL)]),
        }
        for name, (restype, argtypes) in signatures.items():
            fn = getattr(self.k, name); fn.restype = restype; fn.argtypes = argtypes

    def check(self, value):
        if not value:
            raise C.WinError(C.get_last_error())
        return value

    def created(self, handle):
        values = [W.FILETIME() for _ in range(4)]
        self.check(self.k.GetProcessTimes(handle, *[C.byref(x) for x in values]))
        return (values[0].dwHighDateTime << 32) | values[0].dwLowDateTime

    def path(self, handle):
        buf, size = C.create_unicode_buffer(32768), W.DWORD(32768)
        self.check(self.k.QueryFullProcessImageNameW(handle, 0, buf, C.byref(size)))
        return buf.value


class JobChild:
    def __init__(self, api, command, cwd):
        # ABI-sized SIZE_T and pointer fields matter on 64-bit Python.
        class Basic(C.Structure):
            _fields_ = [('process_time', C.c_int64), ('job_time', C.c_int64), ('flags', W.DWORD),
                        ('min_ws', C.c_size_t), ('max_ws', C.c_size_t), ('active', W.DWORD),
                        ('affinity', C.c_size_t), ('priority', W.DWORD), ('scheduling', W.DWORD)]
        class IO(C.Structure):
            _fields_ = [(n, C.c_uint64) for n in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
        class Extended(C.Structure):
            _fields_ = [('basic', Basic), ('io', IO)] + [(n, C.c_size_t) for n in ('process_mem','job_mem','peak_process','peak_job')]
        class Startup(C.Structure):
            _fields_ = [('cb', W.DWORD), ('reserved', W.LPWSTR), ('desktop', W.LPWSTR), ('title', W.LPWSTR)] + [
                (n, W.DWORD) for n in ('x','y','width','height','chars_x','chars_y','fill','flags')] + [
                ('show', W.WORD), ('reserved_size', W.WORD), ('reserved_ptr', C.c_void_p),
                ('stdin', W.HANDLE), ('stdout', W.HANDLE), ('stderr', W.HANDLE)]
        class Process(C.Structure):
            _fields_ = [('process', W.HANDLE), ('thread', W.HANDLE), ('pid', W.DWORD), ('tid', W.DWORD)]
        class StartupEx(C.Structure):
            _fields_ = [('startup', Startup), ('attributes', C.c_void_p)]
        self.api, self.job, self.process = api, None, None
        self.job = api.check(api.k.CreateJobObjectW(None, None))
        info = Extended(); info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        pi, si = Process(), StartupEx(); si.startup.cb = C.sizeof(si)
        try:
            api.check(api.k.SetInformationJobObject(self.job, 9, C.byref(info), C.sizeof(info)))
            # Atomic kernel assignment removes the kill-between-create-and-assign
            # window. Windows 10+ JOB_LIST is required; never fall back to a child
            # born outside the job. Child cannot inherit the supervisor's job handle.
            size = C.c_size_t()
            api.k.InitializeProcThreadAttributeList(None, 1, 0, C.byref(size))
            if not size.value:
                raise C.WinError(C.get_last_error())
            attributes = C.create_string_buffer(size.value)
            api.check(api.k.InitializeProcThreadAttributeList(attributes, 1, 0, C.byref(size)))
            try:
                jobs = (W.HANDLE * 1)(self.job)
                api.check(api.k.UpdateProcThreadAttribute(attributes, 0, 0x2000D, jobs,
                                                        C.sizeof(jobs), None, None))
                si.attributes = C.cast(attributes, C.c_void_p)
                api.check(api.k.CreateProcessW(command[0], C.create_unicode_buffer(subprocess.list2cmdline(command)),
                           None, None, False, 0x80000 | 0x4, None, str(cwd), C.byref(si), C.byref(pi)))
            finally:
                api.k.DeleteProcThreadAttributeList(attributes)
            self.process, self.pid = pi.process, pi.pid
            try:
                assigned = W.BOOL()
                api.check(api.k.IsProcessInJob(self.process, self.job, C.byref(assigned)))
                if not assigned.value:
                    raise RuntimeError('child was not created inside its lifetime job')
                self.created = api.created(self.process)
                # Caller writes run.json before resume, closing metadata-start race.
                self.thread = pi.thread
            except BaseException:
                api.k.TerminateProcess(self.process, 125)
                api.k.CloseHandle(pi.thread)
                raise
        except BaseException:
            self.close()
            raise

    def resume(self):
        try:
            if self.api.k.ResumeThread(self.thread) == 0xffffffff:
                raise C.WinError(C.get_last_error())
        finally:
            self.api.k.CloseHandle(self.thread); self.thread = None

    def kill(self, code):
        if self.api.k.WaitForSingleObject(self.process, 0) == 0:
            return
        ok = self.api.k.TerminateProcess(self.process, code)
        # Ctrl+C may also reach the child. A natural exit between the first
        # check and TerminateProcess is already the required end state.
        if not ok and self.api.k.WaitForSingleObject(self.process, 0) != 0:
            self.api.check(ok)

    def code(self):
        code = W.DWORD()
        self.api.check(self.api.k.GetExitCodeProcess(self.process, C.byref(code)))
        return code.value

    def close(self):
        if getattr(self, 'thread', None):
            self.api.k.CloseHandle(self.thread); self.thread = None
        if self.job:
            self.api.k.CloseHandle(self.job); self.job = None
        if self.process:
            # Kill-on-close is asynchronous. Keep the handle until termination
            # so the sandbox/adapter cannot still be held when launch returns.
            self.api.k.WaitForSingleObject(self.process, 5000)
            self.api.k.CloseHandle(self.process); self.process = None


def tail_log(path):
    try:
        with Path(path).open('rb') as f:
            f.seek(0, 2); f.seek(max(0, f.tell()-256*1024))
            return '\n'.join(f.read().decode('utf-8', errors='replace').splitlines()[-200:])
    except OSError:
        return ''


def diagnose(sandbox, verdict, h):
    atomic_json(sandbox/'diagnosis.json', dict(verdict=verdict, heartbeat=h, wall_clock=time.time()))
    (sandbox/'diagnosis-log.txt').write_text(redact(tail_log(sandbox/'melee-pc.log')), encoding='utf-8')
    try:
        (sandbox/'diagnosis-hang.txt').write_text(redact((sandbox/'hang.txt').read_text(encoding='utf-8', errors='replace')), encoding='utf-8')
    except OSError:
        pass


class ProgressWatch:
    """Supervisor measures progress itself; fresh wall clocks alone do not help."""
    def __init__(self, started):
        self.changed = started
        self.main = None
        self.seen = False

    def hung(self, h, now, enabled=True):
        if not enabled:
            return False
        limit = h.get('watchdog_seconds', 10)
        if not isinstance(limit, (int, float)) or limit < 0:
            limit = 10
        if limit == 0:
            return False
        if h.get('debugger') or h.get('modal'):
            self.changed = now
            self.main = h.get('main_ticks')
            return False
        tick = h.get('main_ticks')
        if h and (not self.seen or tick != self.main):
            self.main, self.changed, self.seen = tick, now, True
        age = h.get('main_age_seconds', 0)
        wall = h.get('wall_clock', now)
        return now-self.changed > limit+5 or (
            isinstance(age, (int, float)) and age > limit+5) or (
            isinstance(wall, (int, float)) and now-wall > limit+5)


def launch(args):
    api = WinAPI()
    sandbox = args.sandbox.resolve()
    command = [str(sandbox/'melee-pc.exe')] + args.command
    for i, arg in enumerate(command):
        if i and command[i-1] == '--iso': _command_discs.add(arg)
        elif arg.startswith('--iso='): _command_discs.add(arg[6:])
        elif i and ('.iso' in arg.lower() or '.gcm' in arg.lower()): _command_discs.add(arg)
    if _command_discs:
        # Native sinks also redact the CLI-selected path, including error messages.
        os.environ['MELEE_ISO'] = next(iter(_command_discs))
    args.unattended = args.unattended or os.getenv('MELEE_UNATTENDED') == '1'
    if args.unattended:
        os.environ['MELEE_UNATTENDED'] = '1'
        os.environ.setdefault('MELEE_VOLUME', '0')
    else:
        os.environ.setdefault('MELEE_VOLUME', '3')
    parent_pid = os.getppid()
    parent = api.check(api.k.OpenProcess(0x100000 | 0x1000, False, parent_pid))
    parent_name = api.path(parent)
    child, forced, code = None, None, 125
    start = time.time()
    progress = ProgressWatch(start)
    record = dict(launcher_pid=os.getpid(), parent_pid=parent_pid, parent_name=parent_name,
                  label=os.getenv('MELEE_RUN_LABEL', sandbox.name), start=start, command=command,
                  timeout=args.max_seconds, owner=os.getenv('MELEE_RUN_OWNER', sandbox.name), sandbox=str(sandbox))
    try:
        # Remove stale diagnostics before suspended launch; log is truncated by engine.
        for name in ('run.json','heartbeat.json','hang.txt','exit.json','verdict.json','termination.json'):
            (sandbox/name).unlink(missing_ok=True)
        child = JobChild(api, command, sandbox)
        record.update(pid=child.pid, process_created=child.created)
        atomic_json(sandbox/'run.json', record)
        child.resume()
        while api.k.WaitForSingleObject(child.process, 250) == 258:
            h = read_json(sandbox/'heartbeat.json')
            if h.get('pid') != child.pid or h.get('process_created') != child.created:
                h = {}
            if api.k.WaitForSingleObject(parent, 0) != 258:
                forced, code = 'WRAPPER_EXIT', 125
            elif args.max_seconds and time.time()-start >= args.max_seconds:
                forced, code = 'TIMEOUT', TIMEOUT_EXIT
            elif progress.hung(h, time.time(), args.unattended):
                forced = f"HUNG presenting={h.get('presented_frames', '?')} logic={h.get('logic_frames', '?')}"
                code = HUNG_EXIT
            if forced:
                diagnose(sandbox, forced, h)
                child.kill(code)
                break
        api.k.WaitForSingleObject(child.process, 5000)
        code = child.code()
        request = read_json(sandbox/'termination.json')
        if request.get('pid') == child.pid and request.get('process_created') == child.created:
            forced = request.get('reason', forced)
    except KeyboardInterrupt:
        forced, code = 'INTERRUPTED', 130
        if child:
            child.kill(code)
    except (OSError, ValueError, RuntimeError) as error:
        forced, code = f'LAUNCH_ERROR {error}', 125
        if child:
            child.kill(code)
    finally:
        if child:
            child.close()  # closes job even on metadata/IO/monitor failure
        api.k.CloseHandle(parent)
        try:
            (sandbox/'.active-run').rmdir()
        except OSError:
            pass
    verdict = classify(code, tail_log(sandbox/'melee-pc.log'), forced)
    with (sandbox/'melee-pc.log').open('a', encoding='utf-8') as log:
        log.write(redact(f'gw: launcher final reason={verdict} code={code}\n'))
    atomic_json(sandbox/'verdict.json', dict(verdict=verdict, code=code, ended=time.time(),
                pid=record.get('pid'), process_created=record.get('process_created')))
    print(redact(verdict), flush=True)
    return code if 0 <= code <= 255 else 1


def terminate_verified(row):
    api = WinAPI()
    handle = api.check(api.k.OpenProcess(0x100000 | 0x1000 | 1, False, row['pid']))
    try:
        created = api.created(handle)
        if not same_created(created, row['created']) or normalized(api.path(handle)) != normalized(row['path']):
            raise RuntimeError(f"process identity changed: {row['pid']}")
        diagnose(Path(row['sandbox']), 'REAPED', row.get('heartbeat', {}))
        atomic_json(Path(row['sandbox'])/'termination.json', dict(pid=row['pid'],
                    process_created=created, reason='REAPED'))
        api.check(api.k.TerminateProcess(handle, 125))
        if api.k.WaitForSingleObject(handle, 5000) != 0:
            raise RuntimeError(f"termination not observed: {row['pid']}")
    finally:
        api.k.CloseHandle(handle)


def windows_and_memory():
    api = WinAPI()
    user = C.WinDLL('user32', use_last_error=True)
    callback = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    user.EnumWindows.argtypes = [callback, W.LPARAM]
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user.GetWindowRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
    user.IsWindowVisible.argtypes = [W.HWND]; user.IsWindowVisible.restype = W.BOOL
    user.IsIconic.argtypes = [W.HWND]; user.IsIconic.restype = W.BOOL
    user.MonitorFromWindow.argtypes = [W.HWND, W.DWORD]; user.MonitorFromWindow.restype = W.HANDLE
    result, areas = {}, {}
    @callback
    def visit(hwnd, _):
        pid, rect = W.DWORD(), W.RECT()
        user.GetWindowThreadProcessId(hwnd, C.byref(pid))
        user.GetWindowRect(hwnd, C.byref(rect))
        width, height = rect.right-rect.left, rect.bottom-rect.top
        area = width*height
        if area > areas.get(pid.value, -1):
            areas[pid.value] = area
            result[pid.value] = f'{rect.left},{rect.top} {width}x{height} monitor={user.MonitorFromWindow(hwnd, 2)} hidden={not bool(user.IsWindowVisible(hwnd))} minimized={bool(user.IsIconic(hwnd))}'
        return True
    user.EnumWindows(visit, 0)
    class Memory(C.Structure):
        _fields_ = [('length', W.DWORD), ('load', W.DWORD)] + [(n, C.c_uint64) for n in
                    ('total','available','total_page','available_page','total_virtual','available_virtual','extended')]
    m = Memory(); m.length = C.sizeof(m)
    api.k.GlobalMemoryStatusEx.argtypes = [C.POINTER(Memory)]
    api.check(api.k.GlobalMemoryStatusEx(C.byref(m)))
    return result, m.available


def seed_cache(root, sandbox, processes):
    """Copy the largest inactive cache without shell splitting or grep/fork pipelines."""
    sandbox = Path(sandbox)
    if (sandbox/'dawn_cache.db').exists(): return
    live = {normalized(p['path']) for p in processes if p.get('path')}
    # An inaccessible executable path makes safe cache selection impossible.
    if any(not p.get('path') for p in processes): return
    candidates = [p for p in Path(root).glob('*/dawn_cache.db')
        if p.parent != sandbox and not (p.parent/'.active-run').exists()
        and normalized(p.parent/'melee-pc.exe') not in live]
    for source in sorted(candidates, key=lambda p: p.stat().st_size, reverse=True):
        lock = source.parent/'.active-run'
        try: lock.mkdir() # share run.sh/prune_runs.py's atomic claim
        except (FileExistsError, FileNotFoundError): continue
        try:
            shutil.copyfile(source, sandbox/'dawn_cache.db')
            wal = source.with_name(source.name+'-wal')
            (sandbox/'dawn_cache.db-wal').unlink(missing_ok=True)
            (sandbox/'dawn_cache.db-shm').unlink(missing_ok=True)
            if wal.exists(): shutil.copyfile(wal, sandbox/wal.name)
        finally:
            lock.rmdir()
        break


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2]/'_build')
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('status', 'reap'):
        p = sub.add_parser(name)
        p.add_argument('--owner'); p.add_argument('--sandbox'); p.add_argument('--hung', action='store_true')
        p.add_argument('--older-than', type=float, help='minimum age in seconds')
    p = sub.add_parser('wait'); p.add_argument('name')
    p = sub.add_parser('seed-cache'); p.add_argument('--sandbox', type=Path, required=True)
    p = sub.add_parser('launch'); p.add_argument('--sandbox', type=Path, required=True)
    p.add_argument('--max-seconds', type=float, default=0); p.add_argument('--unattended', action='store_true')
    p.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == 'seed-cache':
        seed_cache(args.root, args.sandbox, live_processes())
        return 0
    if args.action == 'launch':
        if not math.isfinite(args.max_seconds) or args.max_seconds < 0:
            parser.error('--max-seconds must be finite and nonnegative')
        if args.command[:1] == ['--']: args.command.pop(0)
        return launch(args)
    if args.action == 'reap' and not (args.owner or args.sandbox or args.hung or args.older_than is not None):
        parser.error('reap requires an explicit selector')
    if args.action == 'wait':
        matches = [f.parent for f in args.root.rglob('run.json') if f.parent.name == args.name]
        if len(matches) != 1: raise RuntimeError('run name missing or ambiguous; select a narrower --root')
        path = matches[0]; r = read_json(path/'run.json')
        api = WinAPI(); h = api.k.OpenProcess(0x100000 | 0x1000, False, r['pid'])
        if h:
            try:
                if api.created(h) == r['process_created'] and normalized(api.path(h)) == normalized(path/'melee-pc.exe'):
                    while api.k.WaitForSingleObject(h, 1000) == 258: pass
            finally: api.k.CloseHandle(h)
        for _ in range(20):
            v = read_json(path/'verdict.json')
            if v.get('process_created') == r['process_created']: break
            time.sleep(.1)
        else:
            e = read_json(path/'exit.json')
            v = {'verdict': classify(e.get('code', 125), tail_log(path/'melee-pc.log')) if e.get('pid') == r['pid'] else 'SILENT_EXIT (supervisor gone; exit code unavailable)'}
        print(redact(v['verdict'])); return 0 if v['verdict'] == 'OK' else 1
    rows = inventory(args.root, live_processes())
    if args.action == 'reap':
        chosen = select(rows, args.owner, args.sandbox, args.hung, args.older_than)
        if not chosen:
            print('No matching tracked games; nothing reaped.')
            return 1
        reap_rows(chosen, terminate_verified)
        for r in chosen: print(redact(f"REAPED pid={r['pid']} owner={r['owner']} sandbox={r['sandbox']}"))
    else:
        windows, available = windows_and_memory()
        chosen = select(rows, args.owner, args.sandbox, args.hung, args.older_than) if any(
            (args.owner, args.sandbox, args.hung, args.older_than is not None)) else rows
        for r in chosen:
            print(redact(f"pid={r['pid']} owner={r['owner']} age={r['age']:.0f}s state={r['state']} memory={r.get('memory',0)//1048576}MiB window={windows.get(r['pid'],'none')} sandbox={r['sandbox']}"))
        if available < 2*1024**3: print('WARNING available memory below 2 GiB', file=sys.stderr)
        if len(rows) >= 8: print('WARNING 8-game concurrency cap reached', file=sys.stderr)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(redact(f'runs: {error}'), file=sys.stderr)
        raise SystemExit(125)
