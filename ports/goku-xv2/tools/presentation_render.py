"""Render Goku's CSS icon, CSP portrait and stock icon for every costume (tools/csp own backend, retail framing, outline and shadow).

    python ports/goku-xv2/tools/presentation_render.py [--pose Wait:0] [--blender blender.exe]

Writes _build/goku-xv2/presentation/<costume>/{icon,portrait,stock}.png (what build.py write_presentation converts to .gxtex per
costume), reading the package built in _build/goku-xv2/author-source. Output stays under _build; nothing is committed.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
ROOT = PORT.parents[1]
AUTHOR = ROOT / '_build/goku-xv2/author-source'
OUT = ROOT / '_build/goku-xv2/presentation'
FIELDS = ('icon', 'portrait', 'stock', 'results')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pose', default='Wait:0')
    ap.add_argument('--blender')
    ap.add_argument('--costume', default='all')
    args = ap.parse_args(argv)
    fighter = json.loads((AUTHOR / 'fighter.json').read_text(encoding='utf-8'))
    names = [c['name'] for c in fighter['costumes']]
    package = AUTHOR / 'package/mods/goku-xv2'
    cmd = [sys.executable, str(ROOT / 'tools/csp/render_ui.py'), '--project', str(PORT), '--package', str(package), '--fighter',
           str(AUTHOR / 'fighter.json'), '--art', str(AUTHOR / 'goku.blend'), '--backend', 'own', '--no-publish',
           '--costume', args.costume, '--pose', args.pose]
    if args.blender:
        cmd += ['--blender', args.blender]
    r = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    print(r.stdout[-1500:], r.stderr[-800:])
    if r.returncode:
        return r.returncode
    runs = sorted((ROOT / '_build/csp-render').glob('*/*/final'), key=lambda p: p.stat().st_mtime)
    if not runs:
        print('no final/ output under _build/csp-render')
        return 1
    final = runs[-1]
    for i, name in enumerate(names):
        (OUT / name).mkdir(parents=True, exist_ok=True)
        for f in FIELDS:
            src = final / ('c%03d-%s.png' % (i, f))
            if src.is_file():
                shutil.copy2(src, OUT / name / (f + '.png'))
    print('presentation: wrote', OUT, 'from', final)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
