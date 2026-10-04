"""Existing real-Lua snapshot fixture in an explicitly offline versus context."""
from pathlib import Path
import runpy

original_write_text = Path.write_text


def write_with_context(self, data, *args, **kwargs):
    if self.name == 'stage_slot_lua_retail.inc':
        # The parallel 1P lane added another save-state refusal gate. This
        # fixture tests the stage-slot gate and has no active 1P mode state.
        data = 'static int gs_1p_state_active(void) { return 0; }\n' + data
    return original_write_text(self, data, *args, **kwargs)


if __name__ == '__main__':
    Path.write_text = write_with_context
    try:
        runpy.run_path(str(Path(__file__).with_name('test_stage_switch_fix3.py')),
                       run_name='__main__')
    finally:
        Path.write_text = original_write_text
