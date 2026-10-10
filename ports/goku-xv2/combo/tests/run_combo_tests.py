"""Run Goku's authored combo route tests (geno 11) and write the per-route tables.

    python ports/goku-xv2/combo/tests/run_combo_tests.py [--vs fox,captain,purin,mars] [--specs id,id] [--visible] [--name tag]

For each victim fighter: puts the goku-combo-tests script mod beside the combo package (_build/goku-xv2/combo-package/mods),
writes its missions/combo-run.txt, runs the game through tools/port/run.sh (turbo by default, with --visible at 60 Hz; the window is
always on screen at 40,40 so the owner can watch), and collects the COMBOTEST lines from the run's log. Writes
_build/goku-xv2/combo/results/<name>.md (one table per route: percent x DI per victim, TRUE links / links, the gaps, where it
drops, the intent check) and <name>.json. Exit 1 when any expected cell fails. Uses GW_MELEE / GW_BUILD_ROOT from the env.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PKG = ROOT / '_build/goku-xv2/combo-package/mods'
OUT = ROOT / '_build/goku-xv2/combo/results'
GIT_BASH = os.environ.get('GW_GIT_BASH', 'C:/Program Files/Git/bin/bash.exe')  # Python's plain 'bash' can be WSL's
NAMES = {'fox': 'Fox', 'captain': 'Captain Falcon', 'purin': 'Jigglypuff', 'mars': 'Marth'}
SHIELD = re.compile(r'COMBOSHIELD cell spec=(\S+) vs=(\S+) mode=(\S+) blocks=(\d+) moves=(\d+) routes=(\d+) chain=(\d+) adv=\[([^\]]*)\] '
                    r'hp=\[([^\]]*)\] push=\[([^\]]*)\] gap=\[([^\]]*)\] oos=(\S+) connects=(\S+) break=(\S+) hits=(\d+) fired=<(.*?)> -> (\w+)(.*)')
LINE = re.compile(r'COMBOTEST cell spec=(\S+) vs=(\S+) pct=(\d+) di=(\S+) hits=(\d+) true=(\d+)/(\d+) gaps=(\S*) drop=(\S+) '
                  r'intent=(.+?) taken=\[([^\]]*)\] ki=(\S+) expect=(\S+) -> (\w+)')


def env_iso():
    for line in (ROOT / '.env').read_text(encoding='utf-8').splitlines():
        m = re.match(r'\s*(?:export\s+)?GW_ISO_VANILLA\s*=\s*(.+)', line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    raise SystemExit('GW_ISO_VANILLA missing from .env')


def build_root():
    return Path(os.environ.get('GW_BUILD_ROOT') or ROOT / '_build')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--vs', default='fox,captain,purin,mars')
    ap.add_argument('--specs', default='')
    ap.add_argument('--visible', action='store_true')
    ap.add_argument('--trace', action='store_true', help='log the attacker/victim motion every frame after the 5th input (debug)')
    ap.add_argument('--name', default='')
    ap.add_argument('--reparse', action='store_true', help='do not run the game: rebuild the tables from the logs of an earlier run of the same --name')
    ap.add_argument('--shield', action='store_true', help='SHIELD cells instead of the route cells (the dummy shields, the attacker mashes)')
    ap.add_argument('--modes', default='single,hold,grab,spot,roll,jump', help='shield dummy modes')
    args = ap.parse_args(argv)
    name = args.name or datetime.datetime.now().strftime('combo-%Y%m%d-%H%M%S')
    mod = PKG / 'goku-combo-tests'
    if mod.exists():
        shutil.rmtree(mod)
    shutil.copytree(HERE / 'goku-combo-tests', mod)
    enabled = [e for e in (PKG / 'enabled.txt').read_text(encoding='utf-8').split() if not e.startswith('goku-combo-')]  # one driver script at a time
    (PKG / 'enabled.txt').write_text(chr(10).join(enabled + ['goku-combo-tests']) + chr(10), encoding='utf-8')
    iso = env_iso()
    cells, results, shields = [], {}, []
    for vs in [v.strip() for v in args.vs.split(',') if v.strip()]:
        (mod / 'missions/combo-run.txt').write_text(f'vs = {vs}\nspecs = {args.specs}\nvisible = {1 if args.visible else 0}\ntrace = {1 if args.trace else 0}\n'
                                                       f'shield = {1 if args.shield else 0}\nmodes = {args.modes}\n', encoding='utf-8')
        env = dict(os.environ)
        env.update({'MELEE_MODS_DIR': str(PKG), 'MELEE_SCENE': f'mode=lab;p1=geno:goku-xv2/hu;p2={vs}/hu;stage=fd;items=off;time=0',
                    'MELEE_UNATTENDED': '1', 'MELEE_MAX_SECONDS': '1800' if args.visible else '1500', 'MELEE_LAB_UI': '0'})
        # always on screen at 40,40 (the owner watches tests); --visible plays at 60 Hz, the default runs turbo
        env.update({'MELEE_WINDOW_X': '40', 'MELEE_WINDOW_Y': '40', 'MELEE_WINDOW_W': '1280', 'MELEE_WINDOW_H': '720',
                    'MELEE_RUN_LABEL': f'Goku combo tests vs {NAMES.get(vs, vs)}', 'MELEE_TURBO': '0' if args.visible else '1',
                'MELEE_PAD_SCRIPT': '' if args.visible else (HERE / 'turbo_pad.lua').as_posix()})
        cmd = [GIT_BASH, (ROOT / 'tools/port/run.sh').as_posix(), '--realtime' if args.visible else '--max-seconds', *([] if args.visible else ['1500']),
               f'{name}-{vs}', '--iso', iso]
        print('run', vs, ' '.join(cmd[2:4]))
        OUT.mkdir(parents=True, exist_ok=True)
        if not args.reparse:
            with open(OUT / f'{name}-{vs}.run.txt', 'w', encoding='utf-8') as fh:
                subprocess.run(cmd, cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT)
        log = build_root() / 'runs' / f'{name}-{vs}' / 'melee-pc.log'
        text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
        result = re.findall(r'COMBOTEST RESULT: (.*)', text)
        results[vs] = result[-1] if result else 'NO RESULT (see ' + str(log) + ')'
        for m in LINE.finditer(text):
            spec, v, pct, di, hits, tr, links, gaps, drop, intent, taken, ki, expect, verdict = m.groups()
            cells.append(dict(spec=spec, vs=v, pct=int(pct), di=di, hits=int(hits), true=int(tr), links=int(links), gaps=gaps,
                              drop=drop, intent=intent, taken=taken, ki=float(ki), expect=expect, verdict=verdict, log=str(log)))
        for m in SHIELD.finditer(text):
            g = m.groups()
            shields.append(dict(spec=g[0], vs=g[1], mode=g[2], blocks=int(g[3]), moves=int(g[4]), routes=int(g[5]), chain=int(g[6]), adv=g[7], hp=g[8],
                                push=g[9], gap=g[10], oos=g[11], connects=g[12], broke=g[13], hits=int(g[14]), fired=g[15], verdict=g[16], why=g[17].strip(), log=str(log)))
        print('  ', results[vs])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{name}.json').write_text(json.dumps({'results': results, 'cells': cells, 'shield': shields}, indent=1), encoding='utf-8')
    md = [f'# Goku combo route tests: {name}', '',
          'Each cell: TRUE links / links (a link is TRUE when the next hit lands before the victim can act, the LAB COMBO reading), '
          'the per-link gap (T-n: true with n frames to spare; En: escapable for n frames), where it drops, and the intent check '
          '(the combo routes taken, in order, against the spec). PASS/FAIL only judges cells the spec expects to be true; the rest are reads.', '']
    for vs, r in results.items():
        md.append(f'- vs {NAMES.get(vs, vs)}: {r}')
    by_spec = {}
    for c in cells:
        by_spec.setdefault(c['spec'], []).append(c)
    for spec, rows in by_spec.items():
        md += ['', f'## {spec}', '', '| vs | % | DI | true | gaps | drop | intent | routes taken | ki | expect | |', '|---|---|---|---|---|---|---|---|---|---|---|']
        for c in rows:
            md.append(f"| {NAMES.get(c['vs'], c['vs'])} | {c['pct']} | {c['di']} | {c['true']}/{c['links']} | {c['gaps']} | {c['drop']} | "
                      f"{c['intent']} | {c['taken']} | {c['ki']:.0f} | {c['expect']} | {c['verdict']} |")
    if shields:
        md += ['', '# SHIELD cells', '',
               'The dummy shields (hold = the whole run; grab / spot dodge / roll / jump + aerial / up-B = at its first actionable frame after a blocked hit); the attacker mashes the '
               'spec tokens every 6 frames. adv = the attacker\'s frame advantage on block per blocked move (victim free minus attacker free; + = the attacker acts first), '
               'hp = shield HP lost, push = the defender\'s pushback, gap = frames the defender was actionable before the next blocked move (lock = never), '
               'chain = the longest run of blocked moves with no actionable frame between them (must be <= 2), routes = combo routes taken on block (must be 0), '
               'oos = the option and the frame after the first block, connects = it hit/grabbed the attacker.', '']
        by = {}
        for c in shields:
            by.setdefault(c['spec'], []).append(c)
        for spec, rows in by.items():
            md += [f'## {spec}', '', '| vs | mode | blocks | moves | routes | chain | adv | hp | push | gap | oos | connects | fired | verdict |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
            for c in rows:
                md.append(f"| {NAMES.get(c['vs'], c['vs'])} | {c['mode']} | {c['blocks']} | {c['moves']} | {c['routes']} | {c['chain']} | {c['adv']} | {c['hp']} | {c['push']} | "
                          f"{c['gap']} | {c['oos']} | {c['connects']} | {c['fired']} | {c['verdict']} {c['why']} |")
    (OUT / f'{name}.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('tables:', OUT / f'{name}.md')
    return 0 if (cells or shields) and all(r.startswith('PASS') for r in results.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
