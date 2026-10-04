"""Initialize an absent Envoy profile offline without overwriting any file.

Run with the game stopped, naming the exact engine script-data destination.
The Lua schema owns the format/defaults; Python only creates the file exclusively.
"""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'melee/pc/scripts/examples/envoy/scripts'


def default_bytes(lua='lua'):
    code = ['local D = {}']
    for name in ('genetics', 'companion', 'save'):
        source = (SCRIPTS / (name + '.lua')).read_text(encoding='utf-8')
        code.append(f'D.{name} = (function()\n{source}\nend)()(D)')
    code.append('io.write(D.save.encode(D.save.new_profile()))')
    result = subprocess.run([lua, '-'], input='\n'.join(code).encode('utf-8'),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    # Windows Lua's stdout may translate LF to CRLF, whereas the strict format
    # is LF only, just like the runtime atomic writer's binary string.
    return result.stdout.replace(b'\r\n', b'\n')


def initialize(target, lua='lua'):
    data = default_bytes(lua)
    # No existence pre-check: exclusive creation closes the check/write race.
    # Parents must already exist; the caller identifies the engine's directory.
    with Path(target).open('xb') as stream:
        stream.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--lua', default='lua')
    args = parser.parse_args()
    try:
        initialize(args.destination, args.lua)
    except (OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Profile initialization refused: {error}\n')
    print(f'Created {args.destination}; reload Envoy in the game.')


if __name__ == '__main__':
    main()
