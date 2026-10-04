"""Extract unchanged production functions for the standalone arena-spawn fixture."""
from pathlib import Path
import sys


def function(source, signature):
    start = source.index('\n' + signature) + 1
    depth, i = 0, source.index('{', start)
    while True:
        depth += {'{': 1, '}': -1}.get(source[i], 0)
        i += 1
        if depth == 0:
            return source[start:i]


melee = Path(sys.argv[1])
mtx = (melee/'pc/gameworld/mtx_pc.c').read_text(encoding='utf-8')
lb = (melee/'src/melee/lb/lb_00B0.c').read_text(encoding='utf-8')
sections = [function(mtx, sig) for sig in ('static float mtx_madd(', 'void PSMTXCopy(', 'void PSMTXConcat(',
                                           'u32 PSMTXInverse(', 'void PSMTXMultVec(')]
sections.append(function(lb, 'void lb_8000B1CC('))
Path(sys.argv[2]).write_text('\n\n'.join(sections) + '\n', encoding='utf-8')
