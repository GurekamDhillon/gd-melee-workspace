"""Drive a running training session (MELEE_CONSOLE_PORT) through MK's moves and record, per move, the action
states entered and the animation frames reached - proof that MK's own clips play (their lengths differ from
Kirby's) without relying on screenshots. Pauses the game, steps frames, resumes at the end.

usage: python ingame_check.py <port> [out.json]
"""
import socket, sys, json, time

PORT = int(sys.argv[1]); OUT = sys.argv[2] if len(sys.argv) > 2 else None
s = socket.create_connection(('127.0.0.1', PORT), timeout=60); f = s.makefile('r', encoding='utf-8', errors='replace'); f.readline()


def cmd(line):
    s.sendall((line + '\n').encode()); out = []
    while True:
        r = f.readline().rstrip('\n')
        if r in ('>>> ok', '>>> error'): return out, r == '>>> ok'
        out.append(r)


def p1():
    o, _ = cmd("= (function() local p=gd.player(1) return string.format('%d %.1f %d %.2f %.2f %s', p.action, p.anim_frame, p.action_frame, p.x, p.y, tostring(p.airborne)) end)()")
    a = o[-1].split()
    return {'action': int(a[0]), 'anim': float(a[1]), 'aframe': int(a[2]), 'x': float(a[3]), 'y': float(a[4]), 'air': a[5] == 'true'}


# (name, input command args or None, frames to watch). Stick: x y 0..255, 128 = neutral (docs: input 1 none 40 127 0 = walk right)
MOVES = [   # stick x y are signed: 0 neutral, 127 right/up, -128 left/down (docs: input 1 none 40 127 0 = walk right)
    ('wait', None, 30),
    ('jab (A)', 'A 3', 40),
    ('ftilt', 'A 3 60 0', 45),
    ('dtilt', 'A 3 0 -60', 40),
    ('utilt', 'A 3 0 60', 50),
    ('fsmash', 'A 3 127 0', 70),
    ('usmash', 'A 3 0 127', 70),
    ('dsmash', 'A 3 0 -128', 60),
    ('shield', 'R 40', 45),
    ('spotdodge', 'R 4 0 -128', 40),
    ('roll', 'R 4 127 0', 45),
    ('grab', 'Z 3', 50),
    ('jump', 'X 3', 20),
    ('double jump', 'X 3', 20),
    ('triple jump', 'X 3', 20),
    ('nair', 'A 3', 50),
    ('fair', 'A 3 127 0', 50),
    ('fall', None, 60),
    ('neutral B', 'B 3', 60),
    ('side B', 'B 3 127 0', 60),
    ('down B', 'B 3 0 -128', 80),
    ('up B', 'B 3 0 127', 90),
    ('land/recover', None, 90),
    ('taunt', 'DUP 3', 70),
    ('walk', 'none 40 60 0', 40),
    ('dash', 'none 30 127 0', 30),
    ('wait long', None, 280),
]


def main():
    res = []
    cmd('pause')
    for name, inp, n in MOVES:
        if inp: cmd('input 1 %s' % inp)
        seen = []; last = None
        for k in range(n):
            cmd('step 1'); st = p1()
            key = st['action']
            if key != last: seen.append({'action': key, 'at': k, 'air': st['air']}); last = key
            seen[-1]['max_anim'] = max(seen[-1].get('max_anim', 0), st['anim'])
        res.append({'move': name, 'input': inp, 'states': seen})
        print('%-22s %s' % (name, ' -> '.join('%d(anim<=%.0f)' % (x['action'], x['max_anim']) for x in seen)))
    o, _ = cmd('state'); print('\n'.join(o))
    cmd('resume')
    if OUT: json.dump(res, open(OUT, 'w'), indent=1)


if __name__ == '__main__':
    main()
