"""Background-Blender check for the Geno workspace.

    blender -b --factory-startup --python tools/blender/geno_workbench/selftest_workspace.py

Registers twice, asserts exactly one "Geno" workspace with a 3D view and a dope sheet/timeline, that the
other workspaces are untouched, then unregisters cleanly (the workspace stays by design).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import geno_workbench
from geno_workbench import geno_workspace as gw


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        raise SystemExit(1)


before = sorted(w.name for w in bpy.data.workspaces)
geno_workbench.register()
geno_workbench.unregister()
geno_workbench.register()
geno_workbench.register()   # a repeated register is a no-op
names = [w.name for w in bpy.data.workspaces]
check(names.count("Geno") == 1, "one Geno workspace after repeated register: %s" % names)
check(sorted(n for n in names if n != "Geno") == before, "the user's workspaces are untouched")
screen = bpy.data.workspaces["Geno"].screens[0]
layout_types = gw.area_types(bpy.data.workspaces["Layout"].screens[0])
check(layout_types == ["PROPERTIES", "OUTLINER", "DOPESHEET_EDITOR", "VIEW_3D"], "Layout screen untouched: %s" % layout_types)
types = gw.area_types(screen)
print("areas", types)
for want in gw.WANT_AREAS:
    check(want in types, "has a %s area" % want)
check(types == layout_types, "Geno keeps the Layout arrangement: %s" % types)
check(types.count("VIEW_3D") == 1, "one big 3D viewport")
v3d = next(a for a in screen.areas if a.type == "VIEW_3D")
check(v3d.spaces.active.show_region_ui, "3D view sidebar open")
check(v3d.spaces.active.overlay.show_overlays, "overlays on")
check(v3d.spaces.active.region_3d.view_perspective == "ORTHO", "orthographic front view")
geno_workbench.unregister()
check(len([w for w in bpy.data.workspaces if w.name == "Geno"]) == 1, "unregister leaves the Geno workspace in place")
check(sorted(w.name for w in bpy.data.workspaces if w.name != "Geno") == before, "unregister removed nothing else")
print("GENO_WORKSPACE_OK")
