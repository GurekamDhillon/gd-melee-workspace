"""Add a hitbox on the real engine, rebuild + reload, see it in the frame data, delete it, check the source bytes.

    GW_WB_SCRIPT=add_hitbox_bench.py python launch_goku.py --check --row jab1 --work <own dir>   (see launch_goku.py)

Uses the registered operators (what the panel buttons call). BENCH lines are the evidence.
"""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))


def argv_value(name, default=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return argv[argv.index(name) + 1] if name in argv else default


def main():
    import bpy
    import bootstrap
    from geno_workbench import api
    argv = sys.argv[sys.argv.index("--") + 1:]
    bootstrap.main([a for a in argv if a != "--report"])
    s = api.session()
    project = Path(argv_value("--project"))
    row = argv_value("--row", "jab1")
    frame = int(os.environ.get("GW_BENCH_FRAME", "3"))
    script = project / "moves" / (row + ".genoasm")
    payloads = Path(os.environ.get("GW_WB_PAYLOADS", ""))
    before = script.read_bytes()
    print("BENCH start row=%s connected=%s roles=%s" % (row, s.connected, [r["name"] for r in s.roles]))

    def live(label):
        s.set_frame(frame)
        boxes = (s.info or {}).get("hitboxes", [])
        slots = sorted(h.get("slot", -1) for h in boxes)
        fj = None
        if payloads and (payloads / "frame.json").is_file():
            d = json.loads((payloads / "frame.json").read_text(encoding="utf-8"))
            fj = sorted(h.get("slot", -1) for h in d.get("hitboxes", []))
        print("BENCH %s frame=%s engine_hitbox_slots=%s frame.json_slots=%s" % (label, s.info.get("frame"), slots, fj))
        return slots

    s.refresh_hitboxes()
    n0 = len(s.hitboxes)
    slots0 = live("before")
    t = time.monotonic()
    r = bpy.ops.geno_wb.add_hitbox(frame=frame, bone="HAND_R")
    print("BENCH add result=%s err=%r status=%r source_hitboxes=%d->%d last_added=%s" % (r, s.last_error, s.status, n0, len(s.hitboxes), s.last_added))
    added_bytes = script.read_bytes()
    new_line = [l for l in added_bytes.decode("utf-8").splitlines() if l not in before.decode("utf-8").splitlines()]
    print("BENCH source_diff_lines=%s" % (new_line,))
    ordinal = s.last_added
    ok = "FINISHED" in bpy.ops.geno_wb.rebuild_reload()
    print("BENCH rebuild_reload ok=%s err=%r last=%r total=%.1fs" % (ok, s.last_error, s.last_rebuild, time.monotonic() - t))
    slots1 = live("after_add")
    r = bpy.ops.geno_wb.delete_hitbox(ordinal=ordinal)
    after = script.read_bytes()
    print("BENCH delete result=%s err=%r bytes_identical=%s" % (r, s.last_error, after == before))
    ok = "FINISHED" in bpy.ops.geno_wb.rebuild_reload()
    slots2 = live("after_delete")
    print("BENCH summary added_visible=%s removed_visible=%s source_restored=%s" % (
        len(slots1) == len(slots0) + 1, slots2 == slots0, after == before))
    print("BENCH done")


main()
