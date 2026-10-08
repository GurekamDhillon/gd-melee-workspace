"""selftest.py - Blender-side checks: panel registers, preflight reports the mistakes it should, the control-rig bake reproduces a pose.

    blender -b starter.blend --python tools/geno/artist/blender/selftest.py

Prints SELFTEST PASS/FAIL lines and exits 1 on a failure. Used by tools/geno/artist/test_artist.py.
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import export_fighter as EF  # noqa: E402
import control_rig  # noqa: E402
import geno_panel  # noqa: E402

fails = []


def check(name, ok, detail=""):
    print("SELFTEST %s %s %s" % ("PASS" if ok else "FAIL", name, detail))
    if not ok:
        fails.append(name)


def codes():
    return {o[1] for o in EF.OUT if o[0] == "BLOCKER"}


arm = EF.find_armature()
mesh = [o for o in bpy.data.objects if o.type == "MESH"][0]

PART = "bake" if "bake" in sys.argv else "checks"
if PART == "checks":
  # 1. a clean starter has no blockers
  EF.preflight()
  check("starter preflight clean", not codes(), str(codes()))

  # 2. the panel registers and its operators run
  geno_panel.register()
  check("panel registers", hasattr(bpy.types, "GENO_PT_main"))
  bpy.context.view_layer.objects.active = arm
  r = bpy.ops.geno.validate()
  check("validate operator runs", r == {"FINISHED"} and bpy.data.texts.get("Geno Report") is not None)

  # 3. mistakes are reported with the object / vertex and a fix
  mesh.scale = (1.5, 1.5, 1.5)
  EF.preflight()
  check("unapplied scale named", "OBJECT_TRANSFORM" in codes() and any(o[2] == "object '%s'" % mesh.name for o in EF.OUT if o[1] == "OBJECT_TRANSFORM"))
  mesh.scale = (1, 1, 1)
  vg = mesh.vertex_groups
  names = [g.name for g in vg]
  for n in names[:3]:                      # three groups on vertex 5 -> too many influences
      vg[n].add([5], 0.3, "REPLACE")
  EF.preflight()
  inf = [o for o in EF.OUT if o[1] == "INFLUENCES"]
  check("influences named by vertex", bool(inf) and "5" in inf[0][2] and "Limit Total" in inf[0][4], str(inf[:1]))
  for n in names[:3]:
      vg[n].remove([5])
  EF.preflight()
  unw = [o for o in EF.OUT if o[1] == "UNWEIGHTED"]
  check("unweighted vertex named", bool(unw) and "5" in unw[0][2], str(unw[:1]))

# 4. control-rig bake: a copy of the armature animates; the export armature follows it
if PART == "bake":
  arm = EF.find_armature()
  ctrl_data = arm.data.copy()
  ctrl_data.name = "Ctrl_Data"
  ctrl = bpy.data.objects.new("Ctrl", ctrl_data)
  bpy.context.scene.collection.objects.link(ctrl)
  ctrl.location = (0, 0, 0)
  act = bpy.data.actions["Attack11"]
  export_before = {a.name for a in bpy.data.actions}
  ctrl.animation_data_create()
  ctrl.animation_data.action = act
  try:
      ctrl.animation_data.action_slot = act.slots[0]
  except Exception:
      pass
  # the export armature must not already own the motion: clear its action, keep the action datablock for the control rig
  arm.animation_data.action = None
  # retarget the curves from the armature's name to the control rig's slot (same bone names), so ctrl plays Attack11
  done = control_rig.bake(ctrl, arm, actions=["Attack11"])
  check("bake produced an action", bool(done), str(done))
  baked = bpy.data.actions.get("Attack11_baked")
  if baked:
      arm.animation_data.action = baked
      try:
          arm.animation_data.action_slot = baked.slots[0]
      except Exception:
          pass
      bpy.context.scene.frame_set(4)
      hand = arm.pose.bones["hand.L"].head.copy() if "hand.L" in arm.pose.bones else None
      ctrl.animation_data.action = act
      bpy.context.scene.frame_set(4)
      chand = ctrl.pose.bones["hand.L"].head.copy()
      check("baked pose matches the control rig", hand is not None and (hand - chand).length < 0.02, "%s vs %s" % (hand, chand))
sys.exit(1 if fails else 0)
