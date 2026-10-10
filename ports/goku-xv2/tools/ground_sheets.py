"""Before/after contact sheets for the ground audit: side-view silhouettes of the posed mesh on six frames of a row, floor line y=0.

python ports/goku-xv2/tools/ground_sheets.py [--n 10]
Needs _build/goku-xv2/ground-before/ (a GOKU_GROUND=0 build, see FIDELITY.md) and the built package. Writes
_build/goku-xv2/ground-sheets/<row>.png (top strip = before, bottom strip = after) and index.json (worst rows by BELOW depth).
Not disc data: the points are Goku's converted mesh posed offline through the installed FigaTree.
"""
import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

PORT = Path(__file__).resolve().parents[1]
ROOT = PORT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'ports/ir/tools'))
sys.path.insert(0, str(PORT / 'tools'))
import check_hitbox_positions as HP  # noqa: E402
import figatree  # noqa: E402
from audit_gameplay import rest_context, mesh_points  # noqa: E402

B = ROOT / '_build/goku-xv2'
AFTER = (B / 'author-source/package/mods/goku-xv2/files', next((B / 'author-source/package/build').glob('mesh_*.json')))
BEFORE = (B / 'ground-before/files', B / 'ground-before/mesh_default.json')


class Rig:
    def __init__(self, files, mesh_path):
        self.plan = json.loads((files / 'plan.json').read_text(encoding='utf-8'))
        mesh = json.loads(mesh_path.read_text(encoding='utf-8'))
        self.bank = (files / self.plan['bank']['file']).read_bytes()
        self.rest, self.native, worlds = rest_context(mesh, self.plan)
        self.points, weights = mesh_points(mesh)
        n = len(self.points)
        self.J, self.W = np.zeros((n, 2), dtype=int), np.zeros((n, 2))
        for i, ww in enumerate(weights):
            for k, (j, w) in enumerate(ww[:2]):
                self.J[i, k], self.W[i, k] = j, w
        self.inv = [np.linalg.inv(w) for w in worlds]
        self.ph = np.hstack([self.points, np.ones((n, 1))])

    def tree(self, clip):
        rec = self.plan['bank']['clips'][clip]
        return figatree.parse_archive(self.bank[rec['offset']:rec['offset'] + rec['bytes']])[1]

    def posed(self, tree, frame):
        pose = HP.pose_matrices(tree, self.native, self.rest, frame)
        skin = np.array([pose[i] @ self.inv[i] for i in range(len(pose))])
        out = np.zeros((len(self.points), 3))
        for k in range(2):
            m = skin[self.J[:, k]]
            out += self.W[:, k, None] * np.einsum('nij,nj->ni', m[:, :3, :], self.ph)
        return out


def draw_strip(ax_row, rig, clip, frames, title):
    tree = rig.tree(clip)
    for ax, f in zip(ax_row, frames):
        p = rig.posed(tree, f)
        ax.scatter(p[:, 2], p[:, 1], s=0.15, c='#2b6cb0')
        ax.axhline(0, color='#c53030', lw=1)
        ax.set_xlim(-14, 14)
        ax.set_ylim(-6, 24)
        ax.set_aspect('equal')
        ax.set_xticks([])
        ax.set_yticks([0, 10, 20])
        ax.set_title('%s f%d  low %.1f' % (title, f, p[:, 1].min()), fontsize=7)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=10)
    args = ap.parse_args()
    before = json.loads((B / 'ground-before/audit-before.json').read_text(encoding='utf-8'))['rows']
    after = json.loads((B / 'ground-audit.json').read_text(encoding='utf-8'))['rows']
    worst = sorted([(v['min_y'], k) for k, v in before.items() if not v['ledge'] and k in after])[:args.n]
    rb, ra = Rig(*BEFORE), Rig(*AFTER)
    out = B / 'ground-sheets'
    out.mkdir(exist_ok=True)
    index = []
    for depth, row in worst:
        n = before[row]['frames']
        frames = [int(round(i * (n - 1) / 5)) for i in range(6)]
        fig, axes = plt.subplots(2, 6, figsize=(12, 5))
        draw_strip(axes[0], rb, before[row]['clip'], frames, 'BEFORE')
        draw_strip(axes[1], ra, after[row]['clip'], frames, 'AFTER')
        fig.suptitle('%s: before low %.1f, after low %.1f (%s)' % (row, depth, after[row]['min_y'], after[row]['mode']), fontsize=9)
        fig.tight_layout()
        fig.savefig(out / (row + '.png'), dpi=80)
        plt.close(fig)
        index.append({'row': row, 'before_min_y': depth, 'after_min_y': after[row]['min_y'], 'mode': after[row]['mode'], 'sheet': 'ground-sheets/%s.png' % row})
    (out / 'index.json').write_text(json.dumps(index, indent=1), encoding='utf-8')
    print(len(index), 'sheets in', out)


if __name__ == '__main__':
    main()
