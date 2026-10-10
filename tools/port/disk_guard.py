"""Refuse to start a run, build or sweep when the target drive is nearly full.

    python tools/port/disk_guard.py [--path DIR] [--min-gb N] [--allow-low-disk]

Exit 0 when enough space is free (or the guard is overridden), 1 with a message otherwise.
MELEE_MIN_FREE_GB sets the default threshold (20). Override per call with --allow-low-disk, or for a
whole shell with MELEE_ALLOW_LOW_DISK=1. Used by run.sh, build.sh and tools/sweep/crash_sweep.py.
"""
import argparse
import os
from pathlib import Path
import shutil
import sys

GIB = 1024 ** 3
DEFAULT_MIN_GB = 20.0


def min_free_gb(env=None):
    env = os.environ if env is None else env
    try:
        return float(env.get('MELEE_MIN_FREE_GB', DEFAULT_MIN_GB))
    except ValueError:
        return DEFAULT_MIN_GB


def free_bytes(path):
    """Free bytes on the drive holding `path` (walks up to the nearest existing parent)."""
    p = Path(path).absolute()
    while not p.exists() and p.parent != p:
        p = p.parent
    return shutil.disk_usage(p).free


def check(path, min_gb=None, allow=False):
    """Return (ok, message). `allow` turns a refusal into a warning (ok stays True)."""
    need = min_free_gb() if min_gb is None else float(min_gb)
    free = free_bytes(path) / GIB
    if free >= need:
        return True, ''
    msg = (f'disk guard: only {free:.1f} GB free on the drive holding {path} (need {need:g} GB; '
           f'MELEE_MIN_FREE_GB). Free space first: `python tools/port/disk_report.py` lists what to '
           f'clean (it deletes nothing); finished run sandboxes shrink with '
           f'`python tools/port/prune_runs.py --root <build root>/runs --keep 10 --current none`. '
           f'To proceed anyway pass --allow-low-disk (or set MELEE_ALLOW_LOW_DISK=1).')
    if allow:
        return True, 'warning: ' + msg
    return False, msg


def allowed_by_env():
    return os.environ.get('MELEE_ALLOW_LOW_DISK', '0') not in ('', '0')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--path', default='.')
    ap.add_argument('--min-gb', type=float, default=None)
    ap.add_argument('--allow-low-disk', action='store_true')
    a = ap.parse_args(argv)
    ok, msg = check(a.path, a.min_gb, a.allow_low_disk or allowed_by_env())
    if msg:
        print(msg, file=sys.stderr)
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
