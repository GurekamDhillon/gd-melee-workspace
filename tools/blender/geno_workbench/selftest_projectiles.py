"""Background-Blender check for the Projectiles collection.

    blender -b --factory-startup --python tools/blender/geno_workbench/selftest_projectiles.py

Imports Goku's real articles (ports/goku-xv2/gameplay.json), checks the zero-diff round trip, an edit -> ops, the
spawn markers and the ghost path.  Prints PASS/FAIL lines and exits 1 on a failure.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bpy  # noqa: E402
import projectiles as P  # noqa: E402
import projectiles_bpy as PB  # noqa: E402

ROOT = HERE.parents[2]


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        raise SystemExit(1)


doc = json.loads((ROOT / "ports/goku-xv2/gameplay.json").read_text(encoding="utf-8"))
server = [dict(a, index=i) for i, a in enumerate(doc["articles"])]
scene = bpy.context.scene
made = PB.import_articles(server, scene)
check(len(made) == len(server), "one root per article (%d)" % len(made))
check(sum(len(PB.hitbox_children(r)) for r in made) == sum(len(a.get("hitboxes", [])) for a in server), "one sphere per hitbox")
res = PB.pending_ops(server, scene)
check(not res["edits"] and not res["new"], "unchanged import exports an empty diff")

full = next(r for r in made if r.name == "Proj.KameFull")
check(abs(full.location.x - 12) < 1e-6 and abs(full.location.z - 10) < 1e-6, "root sits at the spawn offset (X fwd, Z up)")
full["gp_velocity_0"] = 6.5
hb = PB.hitbox_children(full)[1]
hb.scale = (4.0, 4.0, 4.0)
hb.location.y = 2.0   # Blender -Y is Melee +Z: offset z = -2
hb["gh_damage"] = 25
res = PB.pending_ops(server, scene)
ops = res["edits"][server.index(next(a for a in server if a["name"] == "KameFull"))]
paths = {o["path"]: o["value"] for o in ops}
check(paths.get("velocity/#0") == 6.5, "velocity edit -> set velocity/#0 = 6.5")
check(paths.get("hitboxes/#1/size") == 4.0 and paths.get("hitboxes/#1/damage") == 25, "hitbox size and damage ops")
check(abs(paths.get("hitboxes/#1/offset/#2", 99) + 2.0) < 1e-3, "Blender Y -> Melee Z offset")
check(len(ops) == 4, "only the four edited leaves changed: %r" % [o["path"] for o in ops])

new = PB.add_projectile("Zap", scene)
res = PB.pending_ops(server, scene)
check(len(res["new"]) == 1 and res["new"][0]["name"] == "Zap", "a new projectile exports as add_article")
bpy.data.objects.remove(new, do_unlink=True)

spawns = [{"row": "volley", "ordinal": 0, "frame": 6, "article": 0, "variant": 0, "angle": 0},
          {"row": "volley", "ordinal": 1, "frame": 14, "article": 1, "variant": 0, "angle": 0}]
rec = PB.sync_markers(spawns, server, "volley", scene)
check(len(scene.timeline_markers) == 2 and not PB.marker_edits(scene), "two spawn markers, none moved")
scene.timeline_markers[0].frame = 9
check(PB.marker_edits(scene) == [{"row": "volley", "ordinal": 0, "frame": 9}], "a dragged marker is an edit_spawn")

info = PB.update_ghost(server, spawns, "volley", 10, scene, base=(0, 0))
check(len(info) == 2 and info[0]["life"] == 4 and info[0]["hitboxes"] == 4, "ghost at frame 10: life 4, KameTap's 4 hitboxes live")
check(info[1]["life"] is None or info[1]["life"] < 0 or info[1]["life"] is None, "second spawn not yet live")
check(bpy.data.objects.get("Ghost.path.0.0") is not None and len(bpy.data.objects["Ghost.path.0.0"].data.vertices) == server[0]["lifetime"] + 1,
      "ghost path has lifetime+1 points")
print("PROJECTILES SELFTEST OK")
