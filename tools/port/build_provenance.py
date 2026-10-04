"""Record/verify the source snapshot and final binaries produced by build.sh."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

SOURCE_SUFFIXES = {'.c', '.cpp', '.cc', '.h', '.hpp', '.inc', '.s', '.asm', '.def',
                   '.ld', '.lcf', '.py', '.sh', '.bat', '.cmake', '.json', '.yml',
                   '.yaml', '.txt', '.lua'}
GENERATED_BRIDGE = {'pc/platform/gw_mex_bridge.c', 'pc/platform/gw_mex_bridge.h'}
ARTIFACTS = ('melee-pc.exe', 'melee-pc.map')


def git(melee, *args):
    return subprocess.check_output(['git', '-C', str(melee), *args], stderr=subprocess.PIPE)


def source_digest(melee, *, omit_bridge=False):
    paths = git(melee, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').decode('utf-8').split('\0')
    digest = hashlib.sha256()
    for name in sorted(set(paths)):
        path = melee/name
        if not name or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if omit_bridge and name in GENERATED_BRIDGE:
            continue
        digest.update(name.encode('utf-8')+b'\0')
        # Deleted tracked inputs must invalidate the stamp, too.
        digest.update(hashlib.sha256(path.read_bytes()).digest() if path.is_file() else b'MISSING')
    return digest.hexdigest()


def fingerprint(melee, build):
    header = (melee/'pc/platform/gw_net.h').read_text(encoding='utf-8')
    match = re.search(r'^\s*#define\s+GW_NET_PROTOCOL_VERSION\s+(\d+)[uU]?\b', header, re.M)
    if not match:
        raise ValueError('cannot read GW_NET_PROTOCOL_VERSION from pc/platform/gw_net.h')
    files = {name: hashlib.sha256((build/name).read_bytes()).hexdigest() for name in ARTIFACTS}
    return dict(format=1, melee_commit=git(melee, 'rev-parse', 'HEAD').decode().strip(),
                netplay_protocol=int(match[1]), source_sha256=source_digest(melee),
                source_dirty=bool(git(melee, 'status', '--porcelain', '--untracked-files=normal').strip()),
                files=files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--melee', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--verify', action='store_true')
    mode.add_argument('--snapshot', action='store_true', help='print pre-build source token excluding generated bridge')
    parser.add_argument('--expect-source', help='refuse a stamp if non-generated inputs changed during the build')
    parser.add_argument('--require-clean', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.snapshot:
            print(source_digest(args.melee, omit_bridge=True))
            return 0
        if args.expect_source and source_digest(args.melee, omit_bridge=True) != args.expect_source:
            raise ValueError('source changed during the build; rebuild before recording provenance')
        current = fingerprint(args.melee, args.build)
        if args.require_clean and current['source_dirty']:
            raise ValueError('game source has uncommitted changes')
        stamp = args.build/'build-provenance.json'
        if args.verify:
            saved = json.loads(stamp.read_text(encoding='utf-8'))
            for key in ('format', 'melee_commit', 'netplay_protocol', 'source_sha256', 'files'):
                if saved.get(key) != current[key]:
                    raise ValueError(f'build provenance mismatch: {key}; rebuild the game')
            if args.require_clean and saved.get('source_dirty') is not False:
                raise ValueError('artifact was built from uncommitted game source')
            print('build provenance verified')
        else:
            temporary = stamp.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(current, indent=2)+'\n', encoding='utf-8')
            temporary.replace(stamp)
            print(f'build provenance recorded: {stamp}')
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'build provenance refused: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
