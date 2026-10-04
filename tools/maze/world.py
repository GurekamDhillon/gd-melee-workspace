"""Build a continuous seeded region world without launching the game."""
import argparse
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.maze.generate import world, materialize


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('seed', type=int)
    p.add_argument('--regions', type=int, default=4)
    p.add_argument('--size', type=int, default=12)
    p.add_argument('--name', default='world')
    p.add_argument('--library', type=Path)
    p.add_argument('--reroll-region', type=int)
    p.add_argument('--region-seed', type=int)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--kit', type=Path, required=True)
    p.add_argument('--prepare-mod', action='store_true')
    a = p.parse_args()
    files = world(a.seed, a.regions, a.size, a.name, a.library, a.reroll_region, a.region_seed)
    target = materialize(files, a.output, a.kit, a.name, a.prepare_mod)
    print(files['maze-map.txt'].decode())
    print(target)


if __name__ == '__main__':
    main()
