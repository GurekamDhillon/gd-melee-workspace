"""Build every Meta Knight costume: model/out/PlBm<cc>.dat for cc in Nr Ye Bu Re Gr Wh (Kirby-clone costume order).

All six Brawl costumes share the mesh (checked: identical geometry and materials, only the six body/eye/foot/mantle/
wing/BrkMask textures differ), so skeleton.py + mesh.py run once and mkbuild writes one file per costume with that
costume's textures. Colour matching by the mantle/body textures (BGRA averages, work/tex):
  00 navy (default) -> Nr   05 orange/yellow -> Ye   03 blue -> Bu   01 red -> Re   02 green -> Gr   04 white -> Wh
Steps: model_export.exe (BrawlLib, 32-bit; brawl/*.json) + brawl_matdump.exe (eye UV sets, eye SRT0) -> anim/tools/mk_eyes.py
(eye states) -> skeleton.py -> mesh.py -> mkbuild build -> mkbuild verify
(HSDRaw reload + HSD skinning of every vertex vs the source) -> cos.py structural parse (independent reader).
"""
import os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); MODEL = os.path.dirname(HERE)
ROOT = r"C:/Users/Gurek/Desktop/GD's Melee"
sys.path.insert(0, ROOT + "/tools/mex_port"); sys.path.insert(0, ROOT + "/experiment/Shadow/analysis/02_assets_scripts")
import mex_hsd, cos
from collections import Counter
MB = os.path.join(HERE, 'mkbuild', 'bin', 'Release', 'net8.0', 'mkbuild.exe')
MAP = [('Nr', '00'), ('Ye', '05'), ('Bu', '03'), ('Re', '01'), ('Gr', '02'), ('Wh', '04')]
KIRBY_NR = os.path.join(MODEL, 'work', 'vanilla', 'PlKbNr.dat')     # MObj template (ACE disc copy)


def check(path):
    raw = open(path, 'rb').read(); a = mex_hsd.Archive(raw).relocate(0)
    pj = [p for p, _ in a.publics if p.endswith('_Share_joint')][0]
    M = cos.Model(a, a.public(pj))
    return {'bytes': len(raw), 'publics': [p for p, _ in a.publics], 'joints': len(M.joints), 'dobjs': len(M.dobjs),
            'pobjs': len(M.pobjs), 'pobj_types': dict(Counter(p['type'] for _, _, p in M.pobjs)),
            'max_env_per_pobj': max(len(p['envs']) for _, _, p in M.pobjs),
            'images': len(M.images), 'formats': dict(Counter(cos.GXFMT.get(i['fmt']) for i in M.images.values()))}


def main():
    os.makedirs(os.path.join(MODEL, 'out'), exist_ok=True)
    if not os.path.exists(KIRBY_NR):
        os.makedirs(os.path.dirname(KIRBY_NR), exist_ok=True)
        open(KIRBY_NR, 'wb').write(mex_hsd.Gcm("C:/iso/SSBM ACE Build v2.0.0.iso").read('PlKbNr.dat'))
    for n in ('00', '01', '02', '03', '04', '05'):
        bj = os.path.join(MODEL, 'brawl', 'FitMetaknight%s.json' % n)
        if not os.path.exists(bj):
            subprocess.run([os.path.join(ROOT, 'experiment', 'brawl-kirby', 'tools', 'model', 'model_export.exe'),
                            r'C:\iso\brawl-extract\files\fighter\metaknight\FitMetaknight%s.pac' % n, bj], check=True)
    # every UV set of the eye object (model_export writes two; the eye's body layer is on the third) and the eye SRT0 clips
    MD = os.path.join(HERE, 'brawl_matdump.exe'); PAC = 'C:/iso/brawl-extract/files/fighter/metaknight'
    if not os.path.exists(os.path.join(MODEL, 'brawl', 'eye_uvs.json')):
        subprocess.run([MD, PAC + '/FitMetaknight00.pac', 'uvs', 'polygon5', os.path.join(MODEL, 'brawl', 'eye_uvs.json')], check=True)
    srt = os.path.join(os.path.dirname(MODEL), 'anim', 'brawl_srt0', 'srt0.json')
    if not os.path.exists(srt):
        os.makedirs(os.path.dirname(srt), exist_ok=True)
        subprocess.run([MD, PAC + '/FitMetaknightMotionEtc.pac', 'srt0', srt], check=True)
    subprocess.run([sys.executable, os.path.join(os.path.dirname(MODEL), 'anim', 'tools', 'mk_eyes.py')], check=True)
    subprocess.run([sys.executable, os.path.join(HERE, 'skeleton.py')], check=True)
    mesh = os.path.join(MODEL, 'work', 'mesh.json')
    subprocess.run([sys.executable, os.path.join(HERE, 'mesh.py'), mesh], check=True, stdout=subprocess.DEVNULL)
    rep = {'mapping': {cc: 'FitMetaknight%s' % nn for cc, nn in MAP}, 'costumes': {}}
    for cc, nn in MAP:
        out = os.path.join(MODEL, 'out', 'PlBm%s.dat' % cc)
        br = os.path.join(MODEL, 'work', 'PlBm%s_build.json' % cc)
        subprocess.run([MB, 'build', mesh, os.path.join(MODEL, 'brawl', 'FitMetaknight%s.json' % nn), out, KIRBY_NR, br], check=True)
        v = subprocess.run([MB, 'verify', out, mesh], capture_output=True, text=True)
        # the eyes, read back from the built file: two eye layers on opposite sides of the head, mirrored, and the
        # eye-state matanim tracks equal to anim/out/eye_states.json at every state (mkbuild EyeCheck.cs)
        e = subprocess.run([MB, 'eyecheck', out, os.path.join(os.path.dirname(MODEL), 'anim', 'out', 'eye_states.json'),
                            os.path.join(MODEL, 'work', 'PlBm%s_eyecheck.json' % cc)], capture_output=True, text=True)
        if e.returncode != 0: raise SystemExit('eyecheck failed for %s: %s' % (cc, e.stdout[-600:]))
        rep['costumes'][cc] = {'brawl': 'FitMetaknight%s.pac' % nn, 'file': 'PlBm%s.dat' % cc, 'check': check(out),
                               'eyecheck': e.stdout.strip().splitlines()[-2:],
                               'verify': v.stdout.strip().splitlines()[-1], 'verify_ok': v.returncode == 0}
        print(cc, nn, rep['costumes'][cc]['check']['bytes'], rep['costumes'][cc]['verify'], 'OK' if v.returncode == 0 else 'FAIL')
    rep['build'] = json.load(open(os.path.join(MODEL, 'work', 'PlBmNr_build.json')))
    rep['mesh_stats'] = json.load(open(mesh))['stats']
    json.dump(rep, open(os.path.join(MODEL, 'model_report.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
