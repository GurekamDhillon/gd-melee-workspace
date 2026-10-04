"""Run prior lifecycle fixture with separately tested lighting dependencies."""
from pathlib import Path
import runpy

original_write_text = Path.write_text


def write_with_lighting_context(self, data, *args, **kwargs):
    if self.name == 'stage_retail_fixture.inc':
        # The prior lifecycle fixture has no HSD light backend. Real lighting
        # helper/constructor/binder bodies are covered by test_stage_switch_lighting.
        data = ('static void Ground_StageSlotFighterLightingClear(void) {}\n'
                'static void Ground_StageSlotFighterLightingRebuild(void) {}\n') + data
    return original_write_text(self, data, *args, **kwargs)


if __name__ == '__main__':
    Path.write_text = write_with_lighting_context
    try:
        runpy.run_path(str(Path(__file__).with_name('test_stage_switch_retail.py')),
                       run_name='__main__')
    finally:
        Path.write_text = original_write_text
