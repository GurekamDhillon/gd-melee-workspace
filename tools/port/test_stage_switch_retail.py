"""Test actual owned source helpers without linking or launching the game."""
from pathlib import Path
import subprocess
from test_stage_switch import ROOT, OUT, compile_test

def function(text, name):
    start = text.index(name + '(')
    # Locate the definition, skipping forward declarations if present.
    while text.find(';', start) < text.find('{', start):
        start = text.index(name + '(', start + len(name))
    start = text.rfind('\n', 0, start) + 1
    brace = text.index('{', start)
    depth = 1
    at = brace + 1
    while depth:
        if text[at] == '{': depth += 1
        elif text[at] == '}': depth -= 1
        at += 1
    return text[start:at] + '\n'

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    retail = (ROOT / 'melee/pc/gameworld/script_stage_slot_retail.inc').read_text()
    native = (ROOT / 'melee/pc/gameworld/script_stage_slot_native.inc').read_text()
    ground = (ROOT / 'melee/src/melee/gr/ground_stage_slot_retail.inc').read_text()
    parts = [function(retail, name) for name in [
        'ScriptGame_StageSlotRetailCaptureBegin', 'ScriptGame_StageSlotRetailCaptureResume',
        'ScriptGame_StageSlotRetailCaptureEnd', 'script_retail_forget_devices',
        'script_retail_clear_banks', 'script_retail_free_map',
        'ScriptGame_StageSlotRetailCollision', 'script_retail_destroy']]
    parts += [function(native, name) for name in [
        'ScriptGame_StageSlotCreated', 'ScriptGame_StageSlotDestroyed']]
    parts += [function(ground, 'Ground_StageSlotRetailInstall')]
    (OUT / 'stage_retail_fixture.inc').write_text('\n'.join(parts))
    exe = OUT / 'stage_retail_teardown_test.exe'
    compile_test(ROOT / 'melee/pc/tests/stage_retail_teardown_test.c', exe, ['/I' + str(OUT)])
    subprocess.run([str(exe)], check=True)
