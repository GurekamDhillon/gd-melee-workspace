"""Compare retail fighter-light setup with the production switch helpers."""
import subprocess
from test_stage_switch import ROOT, OUT, compile_test
from test_stage_switch_retail import function

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    gr = ROOT / 'melee/src/melee/gr'
    ft = ROOT / 'melee/src/melee/ft/kinds/ftCommon/ftCo_09F4.c'
    pieces = [function((gr / 'ground.c').read_text(), 'Ground_801C2374')]
    pieces += [function(ft.read_text(), name) for name in
               ['ftCo_8009F480', 'ftCo_8009F4A4', 'ftCo_8009F54C']]
    pieces += [function((gr / 'grizumi.c').read_text(), 'grIzumi_OnLoad')]
    pieces += [function((gr / 'ground.c').read_text(), 'Ground_801C1E94')]
    pieces += [function((gr / 'ground_stage_slot_lighting.inc').read_text(), name)
               for name in ['Ground_StageSlotFighterLightingClear',
                            'Ground_StageSlotFighterLightingRebuild']]
    install = (gr / 'ground_stage_slot_retail.inc').read_text()
    assert install.index('Ground_801C0800(pair)') < install.index(
        'Ground_StageSlotFighterLightingRebuild()') < install.index('Ground_OnLoad(pair)')
    (OUT / 'stage_lighting_extracted.inc').write_text('\n'.join(pieces))
    exe = OUT / 'stage_lighting_test.exe'
    compile_test(ROOT / 'melee/pc/tests/stage_lighting_test.c', exe, ['/I' + str(OUT)])
    subprocess.run([str(exe)], check=True)
