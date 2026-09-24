"""Rebuild Meta Knight Phases 2 + 3 end to end (model, animations, visibility events, report):

    python ports/halberd/model/tools/build_p23.py
    python ports/halberd/model/tools/install_mk.py <mod dir>      # then install into a slot (copy)

Inputs: C:/iso/brawl-extract/files/fighter/metaknight/*.pac (dumped with the Brawl Kirby BrawlLib tools, 32-bit),
the ACE disc (Kirby template MObj, Kirby's PlCo tables), brawl-kirby/phase2 (row map, bone map, encoder).
"""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(os.path.dirname(HERE))
K = os.path.join(os.path.dirname(os.path.dirname(MK)), 'experiment', 'brawl-kirby', 'tools')
PAC = r'C:\iso\brawl-extract\files\fighter\metaknight'
def run(*a): print('==', ' '.join(os.path.basename(str(x)) for x in a)); subprocess.run(list(a), check=True)
A = os.path.join(MK, 'anim')
if not os.path.exists(os.path.join(A, 'brawl', 'chr0_index.json')):
    run(os.path.join(K, 'anim', 'anim_dump.exe'), PAC + r'\FitMetaknight00.pac', PAC + r'\FitMetaknightMotionEtc.pac', os.path.join(A, 'brawl'), 'FitMetaknight00')
if not os.path.exists(os.path.join(A, 'brawl_mantle', 'chr0_index.json')):
    run(os.path.join(K, 'anim', 'anim_dump.exe'), PAC + r'\FitMetaknight00.pac', PAC + r'\FitMetaknight00.pac', os.path.join(A, 'brawl_mantle'), 'WpnMetaknightMantle')
mj = os.path.join(MK, 'model', 'brawl', 'WpnMetaknightMantle00.json')
if not os.path.exists(mj):
    run(os.path.join(K, 'model', 'model_export.exe'), PAC + r'\FitMetaknight00.pac', mj, 'WpnMetaknightMantle')
run('dotnet', 'build', '-c', 'Release', os.path.join(HERE, 'mkbuild', 'mkbuild.csproj'))
run(sys.executable, os.path.join(HERE, 'build_model.py'))
run(sys.executable, os.path.join(A, 'tools', 'mk_anim.py'))
run(sys.executable, os.path.join(A, 'tools', 'mk_vis.py'))
MB = os.path.join(HERE, 'mkbuild', 'bin', 'Release', 'net8.0', 'mkbuild.exe')
run(MB, 'ajcheck', os.path.join(A, 'out', 'PlBmAJ.dat'), '105')
for cc in ('Nr', 'Ye', 'Bu', 'Re', 'Gr', 'Wh'): run(MB, 'roundtrip', os.path.join(MK, 'model', 'out', 'PlBm%s.dat' % cc))
run(sys.executable, os.path.join(HERE, 'report.py'))
