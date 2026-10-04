"""Run isolated Lua stub checks. Does not execute the game or claim native acceptance."""
from pathlib import Path
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main():
    lua = shutil.which('lua')
    if not lua:
        raise SystemExit('lua is required')
    rows = json.loads((ROOT / 'melee/pc/scripts/examples/demos/catalogue.json').read_text())
    jobs = [(r, 'basic') for r in rows if r.get('new')]
    extras = {'demo_pickup_juice':['pickup-juice'], 'demo_models': ['models'], 'demo_materials': ['models'],
              'demo_gauntlet': ['gauntlet', 'bench-refusal', 'old-match-refusal', 'retry-refusal', 'best-read-refusal', 'staged','staging-failure','staging-cancel'],
              'demo_training_card': ['drill', 'drill-timeout','safe-moves'],
              'demo_rewind': ['snapshot-proof'], 'demo_six_slots': ['recycle-visible','recycle-hidden'],
              'demo_stage_tour': ['tour','tour-cover'], 'demo_data': ['save-refusal'],
              'demo_fly': ['fly-refusal']}
    for row in rows:
        jobs.extend((row, scenario) for scenario in extras.get(row['id'], []))
    failures = 0
    for row, scenario in jobs:
        folder = ROOT / 'melee/pc/scripts/examples' / row['path']
        result = subprocess.run([lua, 'tools/port/demo_smoke.lua', str(folder), scenario],
                                cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            failures += 1
            print('FAIL', row['id'], scenario, result.stderr.strip())
        else:
            print('PASS', row['id'], scenario)
    print(f'{len(jobs)-failures}/{len(jobs)} stub runs passed; physics/GPU/scene acceptance untested')
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
