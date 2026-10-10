"""Which limb strikes in a library clip at its XV2 BAC hit frames (offline pose evidence for the combo states' hitboxes).

python ports/goku-xv2/combo/limbs.py xGOK_ATC_009:12:4 ...     clip:first_hit_frame:duration (BAC frames, 0-based)
Prints, per frame of the hit window, each role's chest-relative position (forward Z, up Y) and picks the role that reaches
farthest forward. Reuses audit_gameplay's pose context (check_hitbox_positions' native FigaTree readers).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools'))
import audit_gameplay as A  # noqa: E402  (sets up the import paths)

G, HP, figatree = A.G, A.HP, A.figatree
PKG = G.ROOT / '_build/goku-xv2/author-source/package/mods/goku-xv2'
ART = G.ROOT / '_build/goku-xv2/author-source/package/build'


def main(args):
    plan = G.load(PKG / 'files/plan.json')
    mesh = G.load(next(ART.glob('mesh_*.json')))
    rest, native, _ = A.rest_context(mesh, plan)
    bank = (PKG / 'files' / plan['bank']['file']).read_bytes()
    out = {}
    for spec in args:
        clip, f0, dur = spec.split(':')
        f0, dur = int(f0), int(dur)
        rec = plan['bank']['clips'][clip]
        _, tree = figatree.parse_archive(bank[rec['offset']:rec['offset'] + rec['bytes']])
        best = None
        rows = []
        for f in range(f0, f0 + dur):
            pose = HP.pose_matrices(tree, native, rest, min(f, tree['frames']))
            chest = pose[plan['roles']['chest'][0]][:3, 3]
            rel = {role: (pose[plan['roles'][role][0]][:3, 3] - chest).tolist() for role in G.ROLE.values() if role != 'chest'}
            for role, v in rel.items():
                if best is None or v[2] > best[2]:
                    best = (role, f, v[2], v[1])
            rows.append({'frame': f, 'rel': {k: [round(x, 2) for x in v] for k, v in rel.items()}})
        out[clip] = {'hit': [f0, dur], 'frames': tree['frames'], 'reach': {'role': best[0], 'frame': best[1], 'z': round(best[2], 2), 'y': round(best[3], 2)}, 'samples': rows}
        print(f"{clip}: {tree['frames']} frames; farthest forward {best[0]} z {best[2]:+.2f} y {best[3]:+.2f} at f{best[1]}")
    (G.ROOT / '_build/goku-xv2/combo').mkdir(parents=True, exist_ok=True)
    (G.ROOT / '_build/goku-xv2/combo/limbs.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1:])
