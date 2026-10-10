"""Measure Rebuild + reload end to end on the real engine.

    blender --background --factory-startup --python fastbuild_bench.py -- <bootstrap args> [--full-first] [--anim-input PATH]

Runs bootstrap's connect/load (same arguments as bootstrap.py, --row required), then:
  1. (--full-first) a Rebuild + reload on a project with no Stage A stamp: expect a FULL build (and it creates the stamp);
  2. a hitbox size edit through the add-on API, Rebuild + reload, refetch: expect a GAMEPLAY-ONLY build; prints the old/new size
     seen in the session's frame data and in the payload frame.json on disk;
  3. (--anim-input PATH) touches that animation/art input and does another edit + Rebuild + reload: expect a FULL build.
Prints BENCH lines; the numbers are wall clock.
"""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))


def arg(name, default=None):
    if name == "--anim-input" and os.environ.get("GW_BENCH_ANIM"):
        return os.environ["GW_BENCH_ANIM"]
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return argv[argv.index(name) + 1] if name in argv else default


def flag(name):
    if name == "--full-first" and os.environ.get("GW_BENCH_FULL_FIRST"):
        return True
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return name in argv


def strip_own(argv):
    out, skip = [], False
    for a in argv:
        if skip:
            skip = False
        elif a == "--anim-input":
            skip = True
        elif a not in ("--full-first", "--report"):
            out.append(a)
    return out


def hit_sizes(session):
    return [round(float(h.get("size", h.get("radius", -1))), 4) for h in (session.info or {}).get("hitboxes", [])]


def frame_json_sizes(payloads):
    p = Path(payloads) / "frame.json"
    if not p.is_file():
        return None, str(p)
    d = json.loads(p.read_text(encoding="utf-8"))
    return [round(float(h.get("size", h.get("radius", -1))), 4) for h in d.get("hitboxes", [])], str(p)


def main():
    import bootstrap
    from geno_workbench import api
    argv = strip_own(sys.argv[sys.argv.index("--") + 1:])
    bootstrap.main(argv)
    session = api.session()
    payloads = os.environ.get("GW_WB_PAYLOADS", "")
    row = arg("--row", "jab1")
    print("BENCH start row=%s connected=%s" % (row, session.connected))

    def step(label):
        t = time.monotonic()
        import bpy
        ok = "FINISHED" in bpy.ops.geno_wb.rebuild_reload()   # the real operator, as the panel button calls it
        dt = time.monotonic() - t
        # refetch the current frame explicitly: what the artist sees next
        t2 = time.monotonic()
        session.set_frame(session.frame if hasattr(session, "frame") else 1)
        refetch = time.monotonic() - t2
        print("BENCH %s ok=%s err=%r rebuild_reload=%.1fs refetch=%.2fs total=%.1fs status=%r last=%r" % (
            label, ok, session.last_error, dt, refetch, dt + refetch, session.status, session.last_rebuild))
        return ok

    if flag("--full-first"):
        step("full_first")
    # a frame where the hitbox is live: find the first frame of the row that has a hitbox
    session.refresh_hitboxes()
    boxes = session.hitboxes
    print("BENCH source_hitboxes=%d first=%s" % (len(boxes), boxes[0] if boxes else None))
    for f in range(1, 40):
        session.set_frame(f)
        if hit_sizes(session):
            break
    print("BENCH live_frame=%s sizes_before=%s" % (session.info.get("frame"), hit_sizes(session)))
    before = hit_sizes(session)
    current = float(boxes[0].get("size", 3.0))
    new = round(current * 1.5 + 0.25, 3)

    def edit_and_build(label, size):
        t = time.monotonic()
        import bpy
        assert "FINISHED" in bpy.ops.geno_wb.edit_hitbox(ordinal=0, size=size), session.last_error   # real operator; row defaults to the session's
        print("BENCH %s edit size %.3f ok in %.2fs" % (label, size, time.monotonic() - t))
        t = time.monotonic()
        ok = step(label)
        print("BENCH %s end_to_end_edit_to_frame=%.1fs" % (label, time.monotonic() - t))
        return ok

    live = session.info.get("frame")
    edit_and_build("hitbox_edit", new)
    session.set_frame(live)
    after = hit_sizes(session)
    print("BENCH sizes_after=%s (before %s, edited ordinal 0 to source size %.3f)" % (after, before, new))
    if payloads:
        print("BENCH frame.json sizes=%s" % (frame_json_sizes(payloads),))
    anim = arg("--anim-input")
    if anim:
        os.utime(anim, None)
        edit_and_build("anim_input_touched", current)  # restores the original size too
    print("BENCH done")


main()
