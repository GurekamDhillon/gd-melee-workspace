#!/usr/bin/env python3
"""Judge a run's perf record (perf.json, written by the engine's always-on summary).

    python tools/port/perfjudge.py <run-folder> [--bench <name>] [--json] [--judge-noisy]
    python tools/port/perfjudge.py --update-baseline <run-folder> --bench <name>

Verdicts: PASS, WARN, FAIL, NOISY (never judged), N/A (nothing to judge). See tools/port/README.md
("Reading the perf verdict"). Stdlib only; the engine side is melee/pc/platform/gw_profiler.c.

Two families of check:
  budget      needs no baseline: script time, frame-work p95 against the 120 fps budget (benchmark
              scenes), any hitch after warm-up, draw calls against a per-scene ceiling;
  regression  against a stored per-machine baseline (benchmark scenes only): mean +10%/+0.5 ms WARN,
              +20%/+1.0 ms FAIL; p99 with 30% slack.
A run is NOISY, and never judged, when another melee-pc instance was present at the start or end of
the scene, or the machine's CPU load from OTHER processes was high. Timings are only comparable under
the same conditions, so the conditions are stored next to the numbers and a baseline is only used
when its clock, fps cap, window and render scale match.
"""
import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUDGET_MS = 1000.0 / 120.0            # the project target: 120 fps with ported fighters
SCRIPT_BUDGET_MS = 1.0                # script time per frame
HITCH_FAIL_MS = 100.0                 # a hitch this long after warm-up is a FAIL, any other over the hitch line a WARN
NOISY_LOAD_MEAN = 35.0                # % of all logical CPUs used by OTHER processes (mean over the scene)
NOISY_LOAD_MAX = 70.0
WARN_REL, WARN_ABS = 0.10, 0.5        # mean regression: warn
FAIL_REL, FAIL_ABS = 0.20, 1.0        # mean regression: fail
P99_WARN, P99_FAIL = 1.30, 1.60       # p99 slack
BASELINE_ROOT = ROOT / '_build' / 'perf-baselines'   # git-ignored; one folder per machine

# Fixed benchmark scenes. `key` names baselines. Ported scenes need a mods dir (GW_BENCH_MODS) that
# holds the ported fighter's slot mod; they are skipped, not failed, without one. Draw ceilings catch
# an explosion (a ported fighter once issued about 1,300 draw calls to a retail fighter's 100); they
# are generous on purpose, tighten them when a fix lands.
BENCH = {
    'retail2': dict(scene='mode=lab;p1=fox/cpu9;p2=marth/cpu9;stage=fd', setup='', ported=False, draw_ceiling=700),
    'ported1': dict(scene='mode=lab;p1=ultimatesora;p2=marth/cpu9;stage=fd', setup='pf combat 1 40', ported=True, draw_ceiling=2200),
    'ported2': dict(scene='mode=lab;p1=ultimatesora;p2=ultimatesora;stage=fd', setup='pf combat 1 40;;pf combat 2 47', ported=True, draw_ceiling=3400),
    # two ported fighters and two retail ones: the heaviest realistic Versus
    'mixed4': dict(scene='mode=lab;p1=ultimatesora;p2=ultimatesora;p3=fox/cpu9;p4=marth/cpu9;stage=fd', setup='pf combat 1 40;;pf combat 2 47', ported=True, draw_ceiling=4200),
}
DEFAULT_DRAW_CEILING = 3600
MATCH_CONDITIONS = ('clock', 'fps_cap', 'window', 'render_scale', 'turbo_render')


def machine():
    return (os.environ.get('COMPUTERNAME') or platform.node() or 'machine').replace('/', '_')


def baseline_path(key, fps):
    return BASELINE_ROOT / machine() / f'{key}-{"u" if str(fps) in ("u", "0") else fps}.json'


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None


def pick_scene(perf, bench=None):
    """The scene to judge: the benchmark window's scene, else the longest recorded scene."""
    scenes = perf.get('scenes') or []
    if not scenes:
        return None
    with_window = [s for s in scenes if (s.get('window') or {}).get('complete')]
    if with_window:
        return with_window[-1]
    return max(scenes, key=lambda s: s.get('frames', 0))


def stats_of(scene):
    """(stats, label): the benchmark window when complete, else steady state, else first-use."""
    w = scene.get('window') or {}
    if w.get('complete') and (w.get('stats') or {}).get('frames'):
        return w['stats'], 'window'
    if (scene.get('steady') or {}).get('frames', 0) >= 120:
        return scene['steady'], 'steady'
    return scene.get('first_use') or {}, 'first-use'


def noisy_reasons(scene, perf):
    m = scene.get('machine') or {}
    out = []
    a, b = m.get('other_melee_instances_start', -1), m.get('other_melee_instances_end', -1)
    if a > 0 or b > 0:
        out.append(f'other melee-pc instances present (start {a}, end {b})')
    load = m.get('other_cpu_load_pct') or {}
    if load.get('mean', 0) > NOISY_LOAD_MEAN or load.get('max', 0) > NOISY_LOAD_MAX:
        out.append(f'other CPU load mean {load.get("mean", 0):.0f}% max {load.get("max", 0):.0f}%')
    if scene.get('in_progress'):
        out.append('scene still in progress (run did not end cleanly)')
    return out


def baseline_for(key, fps, scene):
    if not key:
        return None, 'no benchmark scene'
    path = baseline_path(key, fps)
    base = load_json(path)
    if not base:
        return None, f'no baseline for {key} at {fps} on this machine (create: bench.sh --update-baseline)'
    cond, bcond = scene.get('conditions') or {}, base.get('conditions') or {}
    diff = [k for k in MATCH_CONDITIONS if str(cond.get(k)) != str(bcond.get(k))]
    if diff:
        return None, 'baseline conditions differ (' + ', '.join(f'{k}: {bcond.get(k)} -> {cond.get(k)}' for k in diff) + ')'
    return base, ''


def judge(perf, bench=None, fps=None, judge_noisy=False):
    """Returns dict(verdict, reasons, checks, scene, label, numbers)."""
    scene = pick_scene(perf, bench)
    if not scene:
        return dict(verdict='N/A', reasons=['no scene reached 120 frames'], checks=[], numbers={})
    st, label = stats_of(scene)
    if not st.get('frames'):
        return dict(verdict='N/A', reasons=['no frames recorded'], checks=[], numbers={})
    fw = st['frame_work']
    num = dict(scene=scene.get('name'), basis=label, frames=st['frames'], mean=fw['mean'], p95=fw['p95'], p99=fw['p99'],
               max=fw['max'], script=st['buckets']['script']['mean'], draws=st['draw_calls']['mean'],
               draws_max=st['draw_calls']['max'], hitches=st['hitches']['count'], hitch_worst=st['hitches']['worst_ms'])
    noisy = noisy_reasons(scene, perf)
    checks = []  # (level, text); level 0 ok, 1 warn, 2 fail

    def add(level, text):
        checks.append((level, text))

    spec = BENCH.get(bench or '')
    # ---- budget checks ----
    sc = st['buckets']['script']['mean']
    add(2 if sc > SCRIPT_BUDGET_MS else 0, f'script {sc:.2f} ms/frame (budget {SCRIPT_BUDGET_MS:.1f})')
    if spec:
        add(2 if fw['p95'] > BUDGET_MS else 0, f'frame work p95 {fw["p95"]:.2f} ms (budget {BUDGET_MS:.2f})')
    over = st['hitches']
    steady_hitch = over['count'] if label != 'first-use' else 0
    worst = over['worst_ms']
    if label != 'first-use' and over['count']:
        add(2 if worst > HITCH_FAIL_MS else 1, f'{over["count"]} hitch(es) over {over["over_ms"]:.1f} ms after warm-up, worst {worst:.1f} ms')
    else:
        add(0, 'no hitches after warm-up' if label != 'first-use' else 'warm-up not passed: hitches not judged')
    ceiling = (spec or {}).get('draw_ceiling', DEFAULT_DRAW_CEILING)
    dc = st['draw_calls']['mean']
    add(2 if dc > ceiling else 0, f'draw calls {dc:.0f}/frame (ceiling {ceiling})')
    # ---- regression ----
    note = ''
    if spec:
        base, why = baseline_for(bench, fps if fps is not None else '60', scene)
        if base:
            bs = base['stats']['frame_work']
            d = fw['mean'] - bs['mean']
            warn_at, fail_at = max(WARN_REL * bs['mean'], WARN_ABS), max(FAIL_REL * bs['mean'], FAIL_ABS)
            add(2 if d > fail_at else 1 if d > warn_at else 0,
                f'mean {fw["mean"]:.2f} vs baseline {bs["mean"]:.2f} ms ({d:+.2f}; warn +{warn_at:.2f}, fail +{fail_at:.2f})')
            r = fw['p99'] / bs['p99'] if bs['p99'] else 1
            add(2 if r > P99_FAIL else 1 if r > P99_WARN else 0, f'p99 {fw["p99"]:.2f} vs baseline {bs["p99"]:.2f} ms (x{r:.2f}; slack x{P99_WARN:.2f})')
        else:
            note = 'regression not checked: ' + why
    level = max([c[0] for c in checks] or [0])
    verdict = ['PASS', 'WARN', 'FAIL'][level]
    reasons = [t for lv, t in checks if lv]
    if noisy and not judge_noisy:
        verdict, reasons = 'NOISY', noisy
    elif noisy:
        reasons = ['judged despite noise (' + '; '.join(noisy) + ')'] + reasons
        verdict += '*'
    if note:
        reasons.append(note)
    return dict(verdict=verdict, reasons=reasons, checks=checks, numbers=num, noisy=noisy, label=label)


def line(res):
    n = res.get('numbers') or {}
    head = res['verdict']
    if n:
        head += (f' | {n["scene"]} [{n["basis"]}, {n["frames"]} frames] frame work mean {n["mean"]:.2f} p95 {n["p95"]:.2f} '
                 f'p99 {n["p99"]:.2f} max {n["max"]:.1f} ms | script {n["script"]:.2f} | draws {n["draws"]:.0f}')
    if res['reasons']:
        head += ' | ' + '; '.join(res['reasons'])
    return head


def update_baseline(run, bench, fps):
    perf = load_json(Path(run) / 'perf.json')
    if not perf:
        raise SystemExit('no perf.json in the run folder')
    scene = pick_scene(perf, bench)
    st, label = stats_of(scene) if scene else ({}, '')
    if label != 'window':
        raise SystemExit('baselines come from a complete benchmark window (bench.sh), not a free run')
    noisy = noisy_reasons(scene, perf)
    if noisy:
        raise SystemExit('refusing to store a baseline from a noisy run: ' + '; '.join(noisy))
    path = baseline_path(bench, fps)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(bench=bench, fps=fps, written=time.strftime('%Y-%m-%d %H:%M:%S'), machine=machine(),
                                    stats=st, conditions=scene.get('conditions'), scene=scene.get('name')), indent=1) + '\n')
    return path


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('run', help='run folder (contains perf.json)')
    p.add_argument('--bench', help='benchmark scene key (retail2, ported1, ported2); read from bench.json when absent')
    p.add_argument('--fps', help='fps mode of the run (60 or u); read from bench.json when absent')
    p.add_argument('--json', action='store_true')
    p.add_argument('--judge-noisy', action='store_true', help='judge a noisy run anyway (marked with *)')
    p.add_argument('--update-baseline', action='store_true')
    a = p.parse_args(argv)
    run = Path(a.run)
    meta = load_json(run / 'bench.json') or {}
    bench, fps = a.bench or meta.get('bench'), a.fps or meta.get('fps') or '60'
    if a.update_baseline:
        if not bench:
            raise SystemExit('--update-baseline needs --bench')
        print('baseline written:', update_baseline(run, bench, fps))
        return 0
    perf = load_json(run / 'perf.json')
    if not perf:
        print('N/A | no perf.json in ' + str(run))
        return 0
    res = judge(perf, bench, fps, a.judge_noisy)
    if a.json:
        print(json.dumps(res, indent=1, default=str))
    else:
        print('perf ' + line(res))
    return {'PASS': 0, 'WARN': 0, 'FAIL': 3, 'NOISY': 4}.get(res['verdict'].rstrip('*'), 0)


if __name__ == '__main__':
    sys.exit(main())
