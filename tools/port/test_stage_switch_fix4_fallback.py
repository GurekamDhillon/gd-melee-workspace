"""Run the existing controller suite with explicit legacy fallback context.

The production default now tracks full retail ownership. The old extracted-body
fixture intentionally exercises the opt-in fallback, so provide that context in
its generated include without changing either production bodies or old tests.
"""
from pathlib import Path
import runpy

original_write_text = Path.write_text


def write_with_fallback(self, data, *args, **kwargs):
    if self.name == 'stage_joint_retail.inc':
        # This fixture has no island graph; the parallel map lane added this
        # notification to the extracted retail joint-update function.
        data = ('static void mpScriptIslandRefresh(int j,int s,int c,int e) '
                '{ (void)j; (void)s; (void)c; (void)e; }\n') + data
    if self.name == 'stage_native_lifecycle_retail.inc':
        data = '''#define STAGE_SLOT_PARTIAL_FALLBACK 1
static StOwned script_retail_owned;
static int script_retail_live, script_retail_capture, script_retail_proc;
static void script_retail_forget_devices(HSD_GObj* g) { (void)g; }
''' + data
    return original_write_text(self, data, *args, **kwargs)


if __name__ == '__main__':
    Path.write_text = write_with_fallback
    try:
        runpy.run_path(str(Path(__file__).with_name('test_stage_switch_fix4.py')),
                       run_name='__main__')
    finally:
        Path.write_text = original_write_text
