"""Run real retail ledge fixture with every fixture joint explicitly active."""
from pathlib import Path
import runpy

original_write_text = Path.write_text


def write_with_context(self, data, *args, **kwargs):
    if self.name == 'stage_ledge_retail.inc':
        # This fixture represents native stage joints, not hidden script areas.
        data = ('static int ScriptGame_StageJointActive(int joint) '
                '{ (void)joint; return 1; }\n') + data
    return original_write_text(self, data, *args, **kwargs)


if __name__ == '__main__':
    Path.write_text = write_with_context
    try:
        runpy.run_path(str(Path(__file__).with_name('test_stage_switch_ledges.py')),
                       run_name='__main__')
    finally:
        Path.write_text = original_write_text
