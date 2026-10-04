"""Prune inactive stamped sandboxes; preserve evidence when process status is unknown."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def normalized(path):
    return str(Path(path).resolve()).replace('\\','/').casefold()


def live_games():
    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
            "$ErrorActionPreference='Stop'; $p=@(Get-CimInstance Win32_Process -Filter \"Name='melee-pc.exe'\"); "
            "if (@($p | Where-Object { -not $_.ExecutablePath }).Count) { exit 2 }; "
            "ConvertTo-Json -Compress -InputObject @($p | ForEach-Object { $_.ExecutablePath })"],
            capture_output=True,text=True,check=True)
        paths=json.loads(result.stdout)
        return paths if isinstance(paths,list) and all(isinstance(p,str) and p for p in paths) else None
    except (OSError,ValueError,subprocess.CalledProcessError):
        return None


def prune(root, keep, current, live):
    root=Path(root).resolve()
    if live is None:
        print('run pruning skipped: active process paths could not be verified',file=sys.stderr)
        return
    active={normalized(p) for p in live}
    if normalized(root/current/'melee-pc.exe') in active:
        raise RuntimeError(f'sandbox {current!r} already running; choose another name')
    candidates=[]
    for path in root.iterdir():
        # Resolve and validate every recursive deletion target, including junctions.
        if not path.is_dir() or path.is_symlink() or path.resolve().parent != root:
            continue
        stamp=path/'.last_run'
        if stamp.is_file():
            candidates.append((stamp.stat().st_mtime_ns,path))
    for _,path in sorted(candidates,key=lambda item:item[0],reverse=True)[max(0,keep):]:
        if path.name == current or normalized(path/'melee-pc.exe') in active:
            continue
        lock=path/'.active-run'
        try:
            # The runner claims the same directory before copying or launching.
            # This atomic claim closes the start-versus-prune race.
            lock.mkdir()
        except FileExistsError:
            continue
        except FileNotFoundError:
            continue
        try:
            if path.resolve().parent != root:
                continue
            shutil.rmtree(path)
        finally:
            if lock.exists():
                lock.rmdir()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--keep',type=int,default=50)
    parser.add_argument('--current',required=True)
    args=parser.parse_args()
    try:
        prune(args.root,args.keep,args.current,live_games())
    except (OSError,RuntimeError) as error:
        print(f'run refused: {error}',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__': raise SystemExit(main())
