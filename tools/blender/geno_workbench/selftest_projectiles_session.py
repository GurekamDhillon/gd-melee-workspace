"""Background-Blender check of the Projectiles panel's operators against the fake workbench server.

    blender -b --factory-startup --python tools/blender/geno_workbench/selftest_projectiles_session.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy  # noqa: E402
import geno_workbench  # noqa: E402
from geno_workbench import api, client, fake_engine, projectiles_bpy as PB  # noqa: E402


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        raise SystemExit(1)


fake = fake_engine.FakeWorkbench()
port = fake.start()
try:
    api._session = api.WbSession(lambda: client.McpClient(port=port, timeout=3.0))
    geno_workbench.register()
    sess = api.session()
    check(sess.connect() and sess.refresh_rows() and sess.load_row("jab"), "connected, jab loaded")
    check(bpy.ops.geno_wb.proj_import() == {"FINISHED"}, "Load projectiles")
    check(len(PB.roots()) == 2 and len(bpy.context.scene.timeline_markers) == 2, "2 projectiles, 2 spawn markers")
    check(not PB.pending_ops(sess.articles)["edits"], "no pending edits after a load")
    ball = bpy.data.objects["Proj.Ball"]
    ball["gp_velocity_0"] = 4.5
    ball["gp_lifetime"] = 30
    bpy.context.scene.timeline_markers[0].frame = 9
    check(bpy.ops.geno_wb.proj_apply() == {"FINISHED"}, "Apply to source")
    check(fake.articles[0]["velocity"][0] == 4.5 and fake.articles[0]["lifetime"] == 30, "server article carries the edit")
    check([c["frame"] for c in fake.spawn_calls] == [9, 14], "server spawn moved to frame 9: %r" % [c["frame"] for c in fake.spawn_calls])
    check(fake.stale and sess.stale, "marked stale until Rebuild + reload")
    check(not PB.pending_ops(sess.articles)["edits"] and not PB.marker_edits(), "after Apply nothing is pending")
    sess.set_frame(12)
    ghosts = [o for o in bpy.data.objects if o.name.startswith("Ghost.path")]
    check(len(ghosts) == 2, "scrubbing to frame 12 draws a ghost path per spawn")
    bpy.context.view_layer.objects.active = ball
    sess.set_frame(10)
    check(bpy.ops.geno_wb.proj_add_spawn() == {"FINISHED"} and len(fake.spawn_calls) == 3, "Spawn at this frame adds a call")
    check(sess.rebuild_reload() and not sess.stale, "Rebuild + reload clears stale")
    print("PROJECTILES SESSION OK")
finally:
    try:
        geno_workbench.unregister()
    except Exception as exc:
        print("unregister:", exc)
    fake.stop()
