"""Charge-ball placement check. Parses the KBALL lines of a run of lua/kame_ball.lua (a package built with `kame_pkg.py --probe`) and reports,
per frame, how far the ball is from the midpoint of the two hands (world units).

    python ports/goku-xv2/tools/kame_ball.py RUNLOG [--old OFFSET]

Probe P0 = a point at the hand.R joint (no offset), probe M = a point at the origin of a binding with joint2 = hand.L (the ball's anchor). The template's per-spawn
jitter is removed by differencing: |(M - P0) - (mid - hR)| is the ball's miss against the hands' midpoint, per frame, from the same spawn instant. hR / hL are
gd.joints positions; with --old Z also the distance an effect at hand.R + (0,0,Z) in the hand frame (the pre-fix ball, Z = 4) would have been, from the hitbox axes.
"""
import math, re, sys


def v(s):
    return [float(x) for x in s.split(',')] if s and s != 'nil' else None


def sub(a, b): return [x - y for x, y in zip(a, b)]
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def norm(a): return math.sqrt(dot(a, a))


def main():
    log = sys.argv[1]
    old = float(sys.argv[sys.argv.index('--old') + 1]) if '--old' in sys.argv else None
    rows = []
    for line in open(log, encoding='utf-8', errors='replace'):
        m = re.search(r'KBALL t=(\d+) .* hR=(\S+) hL=(\S+) o=(\S+) ax=(\S+) ay=(\S+) az=(\S+) fx=(\S*)', line)
        if not m:
            continue
        t = int(m.group(1)); st = re.search(r' st=(\S+)', line).group(1)
        hR, hL = v(m.group(2)), v(m.group(3))
        fx = dict(p.split('=') for p in m.group(8).split(';') if '=' in p)
        if '0' not in fx or 'M' not in fx:
            continue
        P0, M = v(fx['0']), v(fx['M'])
        mid = [(a + b) / 2 for a, b in zip(hR, hL)]
        miss = norm(sub(sub(M, P0), sub(mid, hR)))
        rec = dict(t=t, st=st, M=M, P0=P0, dmid=sub(mid, hR), miss=miss, gap=norm(sub(hL, hR)), M_to_mid=norm(sub(M, mid)))
        if old is not None and all(v(m.group(i)) for i in (4, 5, 6, 7)):
            o = v(m.group(4)); ex = [x / 10 / 1.43 * 1.0 for x in sub(v(m.group(5)), o)]; ey = sub(v(m.group(6)), o); ez = sub(v(m.group(7)), o)
            ez = [x / norm(ez) for x in ez]
            ball_old = [h + old * z for h, z in zip(hR, ez)]
            rec['old_miss'] = norm(sub(ball_old, mid))
        rows.append(rec)
    if not rows:
        print('no KBALL rows with both probes in', log); return 1
    by = {}
    for r in rows:
        by.setdefault(r['st'], []).append(r['miss'])
    print('per state (frames, mean miss, max miss): ' + '; '.join('%s %d %.3f %.3f' % (k, len(v), sum(v) / len(v), max(v)) for k, v in by.items()))
    ms = [r['miss'] for r in rows]
    print('frames %d  hand gap %.2f  ball(M-P0) vs hands-midpoint miss: mean %.3f max %.3f  (M_to_mid incl. spawn jitter: mean %.3f)' % (
        len(rows), rows[0]['gap'], sum(ms) / len(ms), max(ms), sum(r['M_to_mid'] for r in rows) / len(rows)))
    if old is not None and 'old_miss' in rows[0]:
        print('pre-fix ball (hand.R + (0,0,%g)) distance to the midpoint: %.2f (every frame; the pose is static)' % (old, rows[0]['old_miss']))
    # the effect runtime scatters a point spawn along one line by up to +-0.8 (visual_pos; the same for both probes, different draws), so the per-frame miss above is
    # that scatter. The scatter is zero-mean: a 12-frame window mean of (M - P0) against (mid - hR) is the real placement error
    W = 12
    wins = []
    for i in range(0, len(rows) - W + 1, W):
        w = rows[i:i + W]
        mm = [sum(r['M'][k] - r['P0'][k] for r in w) / W for k in range(3)]
        dm = [sum(r['dmid'][k] for r in w) / W for k in range(3)]
        wins.append(norm(sub(mm, dm)))
    print('12-frame window means of the ball-to-midpoint miss: %s  (mean %.3f, max %.3f)' % (' '.join('%.2f' % x for x in wins), sum(wins) / len(wins), max(wins)))
    for r in rows[::max(1, len(rows) // 12)]:
        print('  t=%3d miss %.3f%s' % (r['t'], r['miss'], '  old %.2f' % r['old_miss'] if 'old_miss' in r else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
