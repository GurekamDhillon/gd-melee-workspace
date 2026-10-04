"""Compare profiler JSON reports; thresholds are provisional CPU allocations."""
import argparse
import json
from pathlib import Path
import sys

def zones(report):
    value = report.get('zones', {})
    return {x['name']: x for x in value} if isinstance(value, list) else value

def compare(a, b, budgets, tolerance=0.05):
    za, zb = zones(a), zones(b)
    lines, failures = [], []
    for label,report in [('A',a),('B',b)]:
        if 'bench' in report:
            bench=report['bench'];status=bench.get('status',{})
            if not status.get('complete'): failures.append(label+': benchmark incomplete')
            if bench.get('exit_code') != 0: failures.append(label+': benchmark process failed or exit code missing')
            if not isinstance(bench.get('requested_frames'),int) or status.get('frames') != bench['requested_frames']: failures.append(label+': completed frame count does not match request')
            if bench.get('profile_error'): failures.append(label+': '+str(bench['profile_error']))
            if not isinstance(bench.get('workload_fingerprint'),str) or not bench['workload_fingerprint']: failures.append(label+': workload fingerprint missing')
    for name in sorted(set(za) | set(zb) | set(budgets['zones'])):
        if name not in za or name not in zb:
            lines.append(name + ': MISSING in ' + ('A' if name not in za else 'B'))
            if name in budgets['zones']: failures.append(name + ': missing budgeted zone')
            continue
        old, new = float(za[name]['p95']), float(zb[name]['p95'])
        delta = new - old
        lines.append(f'{name:32} {old:8.3f} -> {new:8.3f} ms {delta:+8.3f} ({delta/old*100:+.1f}%)' if old else f'{name}: {old:.3f} -> {new:.3f} ms (zero baseline)')
        if name in budgets['zones']:
            budget = budgets['zones'][name]
            if new > budget: failures.append(f'{name}: p95 {new:.3f} exceeds proposed {budget:.3f} ms')
            if delta > max(abs(old) * tolerance, budgets.get('absolute_tolerance_ms', 0.02)):
                failures.append(name + ': regression beyond tolerance')
    # Comparing unlike scenarios/input/measurement scope can look deceptively meaningful.
    for key in ('scenario', 'seed', 'requested_frames', 'profile_scope', 'requested_roster', 'actual_roster', 'mods_fingerprint', 'backend', 'disc', 'feature_statuses', 'workload_fingerprint'):
        if a.get('bench', {}).get(key) != b.get('bench', {}).get(key): failures.append('incomparable bench field: ' + key)
    return lines, failures

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reportA', type=Path); p.add_argument('reportB', type=Path)
    p.add_argument('--budgets', type=Path, default=Path(__file__).with_name('budgets.json'))
    p.add_argument('--legacy', action='store_true', help='compare built-in callback-sampled diagnostics for baseline profiler overhead; no native zone budgets')
    p.add_argument('--tolerance', type=float, default=0.05)
    args = p.parse_args(argv)
    if args.tolerance < 0: p.error('tolerance must be nonnegative')
    a,b=json.loads(args.reportA.read_text()),json.loads(args.reportB.read_text())
    budgets=json.loads(args.budgets.read_text())
    if args.legacy:
        a['zones']=a.get('bench',{}).get('legacy_metrics',{});b['zones']=b.get('bench',{}).get('legacy_metrics',{})
        if not a['zones'] or not b['zones']: p.error('legacy callback metrics missing')
        budgets={'zones':{name:float('inf') for name in a['zones']},'absolute_tolerance_ms':0.02}
    lines, failures = compare(a, b, budgets, args.tolerance)
    print('\n'.join(lines + ['FAIL: ' + x for x in failures]))
    return bool(failures)
if __name__ == '__main__': sys.exit(main())
